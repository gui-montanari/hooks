"""
Test Runner
Executes pytest and tracks results
"""

import json
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from .trackers.result_tracker import ResultTracker
from .trackers.history_tracker import HistoryTracker
from .reporters.markdown_reporter import MarkdownReporter
from .reporters.json_reporter import JsonReporter
from .utils.config import load_config
from .utils.logger import logger


class TestRunner:
    """Main test runner with tracking capabilities"""
    
    def __init__(self):
        self.config = load_config()
        self.test_dir = Path(self.config['test_generator']['test_directory'])
        self.result_tracker = ResultTracker(self.config)
        self.history_tracker = HistoryTracker(self.config)
        self.md_reporter = MarkdownReporter(self.config)
        self.json_reporter = JsonReporter(self.config)
        
    def run_tests(self, module: Optional[str] = None, 
                 failed_only: bool = False,
                 not_tested_only: bool = False,
                 file_path: Optional[str] = None,
                 since: Optional[str] = None,
                 pattern: Optional[str] = None) -> None:
        """Run tests with specified filters"""
        print("🧪 TEST RUNNER & TRACKER")
        print("=" * 60)
        
        # Build pytest command
        cmd = self._build_pytest_command(
            module, failed_only, not_tested_only, 
            file_path, since, pattern
        )
        
        # Get list of test files that will run
        test_files = self._get_test_files(
            module, failed_only, not_tested_only,
            file_path, since, pattern
        )
        
        if not test_files:
            print("❌ No test files found matching criteria")
            return
            
        print(f"📋 Running {len(test_files)} test file(s)...")
        print(f"🔧 Command: {' '.join(cmd)}")
        print("-" * 60)
        
        # Run tests
        start_time = time.time()
        result = self._execute_tests(cmd)
        duration = time.time() - start_time
        
        # Process results
        test_results = self._process_results(result, test_files, duration)
        
        # Track results
        self.result_tracker.track_results(test_results)
        self.history_tracker.add_to_history(test_results)
        
        # Generate reports
        self._generate_reports(test_results)
        
        # Display summary
        self._display_summary(test_results)
        
    def show_status(self) -> None:
        """Show current test status"""
        # Load latest results
        results = self.result_tracker.get_latest_results()
        
        if not results:
            print("❌ No test results found. Run tests first.")
            return
            
        # Generate and display markdown report
        report = self.md_reporter.generate_report(results)
        print(report)
        
    def analyze_failures(self) -> None:
        """Analyze test failures"""
        results = self.result_tracker.get_latest_results()
        
        if not results:
            print("❌ No test results found.")
            return
            
        # Find failures
        failures = []
        for module_name, module_data in results.get('modules', {}).items():
            for test_file, file_data in module_data.get('test_files', {}).items():
                if file_data['status'] == 'failed':
                    for test_name, test_data in file_data.get('tests', {}).items():
                        if test_data['status'] == 'failed':
                            failures.append({
                                'module': module_name,
                                'file': test_file,
                                'test': test_name,
                                'error': test_data.get('error', {})
                            })
                            
        if not failures:
            print("✅ No failures found!")
            return
            
        print(f"\n❌ Found {len(failures)} failing test(s):\n")
        
        for i, failure in enumerate(failures, 1):
            print(f"{i}. {failure['module']} :: {failure['file']} :: {failure['test']}")
            print(f"   Error: {failure['error'].get('message', 'Unknown error')}")
            print(f"   Type: {failure['error'].get('type', 'Unknown')}")
            print()
            
    def _build_pytest_command(self, module: Optional[str] = None,
                            failed_only: bool = False,
                            not_tested_only: bool = False,
                            file_path: Optional[str] = None,
                            since: Optional[str] = None,
                            pattern: Optional[str] = None) -> List[str]:
        """Build pytest command with arguments"""
        cmd = ['pytest']
        
        # Add base arguments
        cmd.extend(self.config['test_runner']['pytest_args'])
        
        # Add coverage arguments
        if self.config['test_runner'].get('coverage_args'):
            cmd.extend(self.config['test_runner']['coverage_args'])
            
        # Add JSON output for parsing
        cmd.extend(['--json-report', '--json-report-file=.pytest_report.json'])
        
        # Add target path
        if file_path:
            cmd.append(file_path)
        elif module:
            cmd.append(str(self.test_dir / module))
        else:
            cmd.append(str(self.test_dir))
            
        # Add filters
        if failed_only:
            # Get failed tests from history
            failed_tests = self.history_tracker.get_failed_tests()
            if failed_tests:
                cmd.extend(['-k', ' or '.join(failed_tests)])
                
        if pattern:
            cmd.extend(['-k', pattern])
            
        # Add parallel execution
        if self.config['test_runner']['parallel_execution']:
            cmd.extend(['-n', str(self.config['test_runner']['max_workers'])])
            
        return cmd
        
    def _get_test_files(self, module: Optional[str] = None,
                       failed_only: bool = False,
                       not_tested_only: bool = False,
                       file_path: Optional[str] = None,
                       since: Optional[str] = None,
                       pattern: Optional[str] = None) -> List[Path]:
        """Get list of test files that match criteria"""
        if file_path:
            return [Path(file_path)]
            
        # Get base directory
        if module:
            base_dir = self.test_dir / module
        else:
            base_dir = self.test_dir
            
        if not base_dir.exists():
            return []
            
        # Get all test files
        test_files = list(base_dir.rglob('test_*.py'))
        
        # Filter by modification time
        if since:
            cutoff_date = self._parse_since_date(since)
            test_files = [f for f in test_files if f.stat().st_mtime > cutoff_date.timestamp()]
            
        # Filter by test history
        if failed_only:
            failed_files = self.history_tracker.get_failed_test_files()
            test_files = [f for f in test_files if str(f) in failed_files]
            
        if not_tested_only:
            tested_files = self.history_tracker.get_tested_files()
            test_files = [f for f in test_files if str(f) not in tested_files]
            
        return test_files
        
    def _execute_tests(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """Execute pytest command"""
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
    def _process_results(self, result: subprocess.CompletedProcess, 
                        test_files: List[Path], duration: float) -> Dict[str, Any]:
        """Process test execution results"""
        # Parse pytest JSON output
        json_report_path = Path('.pytest_report.json')
        
        if json_report_path.exists():
            with open(json_report_path) as f:
                pytest_data = json.load(f)
        else:
            pytest_data = {}
            
        # Parse coverage data
        coverage_data = self._parse_coverage_data()
        
        # Build results structure
        results = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': duration,
                'command': ' '.join(result.args) if hasattr(result, 'args') else '',
                'pytest_version': pytest_data.get('pytest_version', 'unknown'),
                'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            },
            'summary': {
                'total_files': len(test_files),
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0,
                'coverage_percent': coverage_data.get('percent', 0),
                'execution_status': 'completed' if result.returncode == 0 else 'failed'
            },
            'modules': {},
            'untested_files': [],
            'flaky_tests': [],
            'recommendations': {}
        }
        
        # Process test results
        if 'tests' in pytest_data:
            results = self._process_pytest_tests(pytest_data['tests'], results)
            
        # Add untested files
        results['untested_files'] = self._find_untested_files()
        
        # Identify flaky tests
        results['flaky_tests'] = self.history_tracker.identify_flaky_tests()
        
        # Generate recommendations
        results['recommendations'] = self._generate_recommendations(results)
        
        return results
        
    def _process_pytest_tests(self, tests: List[Dict], results: Dict) -> Dict:
        """Process individual test results from pytest"""
        for test in tests:
            # Extract module and file info
            nodeid = test['nodeid']
            parts = nodeid.split('/')
            
            if len(parts) >= 3:  # tests/automated_tests/module/file.py::test
                module = parts[2]
                file_path = '/'.join(parts[:4])
                test_name = nodeid.split('::')[-1]
                
                # Initialize module if needed
                if module not in results['modules']:
                    results['modules'][module] = {
                        'coverage_percent': 0,
                        'status': 'passed',
                        'test_files': {}
                    }
                    
                # Initialize file if needed
                if file_path not in results['modules'][module]['test_files']:
                    results['modules'][module]['test_files'][file_path] = {
                        'status': 'passed',
                        'duration': 0,
                        'tests': {}
                    }
                    
                # Add test result
                test_result = {
                    'status': test['outcome'],
                    'duration': test['duration']
                }
                
                # Add error info if failed
                if test['outcome'] == 'failed':
                    test_result['error'] = self._extract_error_info(test)
                    results['modules'][module]['status'] = 'failed'
                    results['modules'][module]['test_files'][file_path]['status'] = 'failed'
                    
                results['modules'][module]['test_files'][file_path]['tests'][test_name] = test_result
                
                # Update counts
                results['summary']['total_tests'] += 1
                if test['outcome'] == 'passed':
                    results['summary']['passed'] += 1
                elif test['outcome'] == 'failed':
                    results['summary']['failed'] += 1
                elif test['outcome'] == 'skipped':
                    results['summary']['skipped'] += 1
                    
        return results
        
    def _extract_error_info(self, test: Dict) -> Dict[str, Any]:
        """Extract error information from failed test"""
        error_info = {
            'type': 'Unknown',
            'message': 'Unknown error',
            'traceback': ''
        }
        
        if 'call' in test and test['call'].get('longrepr'):
            longrepr = test['call']['longrepr']
            
            # Extract error type and message
            if isinstance(longrepr, str):
                lines = longrepr.split('\n')
                if lines:
                    # Try to find assertion or exception
                    for line in lines:
                        if 'AssertionError' in line:
                            error_info['type'] = 'AssertionError'
                            error_info['message'] = line.strip()
                            break
                        elif 'Error' in line or 'Exception' in line:
                            parts = line.split(':', 1)
                            if len(parts) == 2:
                                error_info['type'] = parts[0].strip()
                                error_info['message'] = parts[1].strip()
                                break
                                
                    # Get traceback
                    error_info['traceback'] = longrepr
                    
        return error_info
        
    def _parse_coverage_data(self) -> Dict[str, Any]:
        """Parse coverage data if available"""
        coverage_file = Path('.coverage')
        coverage_json = Path('coverage.json')
        
        if coverage_json.exists():
            with open(coverage_json) as f:
                return json.load(f)
                
        # TODO: Parse .coverage file if needed
        return {'percent': 0}
        
    def _find_untested_files(self) -> List[str]:
        """Find Python files without tests"""
        untested = []
        
        # Get all Python files in app directory
        app_dir = Path('app')
        if app_dir.exists():
            for py_file in app_dir.rglob('*.py'):
                # Skip __pycache__ and __init__
                if '__pycache__' in str(py_file) or py_file.name == '__init__.py':
                    continue
                    
                # Check if test exists
                test_name = f"test_auto_{py_file.stem}.py"
                test_path = self.test_dir / py_file.parts[1] / test_name
                
                if not test_path.exists():
                    untested.append(str(py_file))
                    
        return untested
        
    def _generate_recommendations(self, results: Dict) -> Dict[str, List[str]]:
        """Generate recommendations based on results"""
        recommendations = {
            'critical': [],
            'missing_tests': [],
            'performance': []
        }
        
        # Critical recommendations for failures
        if results['summary']['failed'] > 0:
            recommendations['critical'].append(
                f"Fix {results['summary']['failed']} failing tests"
            )
            
        # Check coverage
        if results['summary']['coverage_percent'] < self.config['integration']['min_coverage_percent']:
            recommendations['critical'].append(
                f"Increase coverage from {results['summary']['coverage_percent']}% "
                f"to {self.config['integration']['min_coverage_percent']}%"
            )
            
        # Missing tests
        for file_path in results['untested_files'][:5]:  # Top 5
            recommendations['missing_tests'].append({
                'file': file_path,
                'suggested_tests': self._suggest_tests_for_file(file_path)
            })
            
        # Performance issues
        # Find slow tests
        for module_name, module_data in results['modules'].items():
            for file_path, file_data in module_data['test_files'].items():
                for test_name, test_data in file_data['tests'].items():
                    if test_data.get('duration', 0) > 5:  # Tests taking > 5 seconds
                        recommendations['performance'].append({
                            'test': f"{file_path}::{test_name}",
                            'duration': test_data['duration'],
                            'suggestion': 'Consider optimizing or mocking external calls'
                        })
                        
        return recommendations
        
    def _suggest_tests_for_file(self, file_path: str) -> List[str]:
        """Suggest test names for untested file"""
        suggestions = []
        
        # Basic CRUD suggestions for models
        if 'models' in file_path:
            suggestions.extend([
                'test_create',
                'test_read',
                'test_update',
                'test_delete',
                'test_validation'
            ])
        # Service suggestions
        elif 'services' in file_path:
            suggestions.extend([
                'test_service_initialization',
                'test_main_functionality',
                'test_error_handling'
            ])
        # Endpoint suggestions
        elif 'api' in file_path or 'routes' in file_path:
            suggestions.extend([
                'test_success_response',
                'test_authentication',
                'test_validation_errors',
                'test_not_found'
            ])
            
        return suggestions
        
    def _generate_reports(self, results: Dict) -> None:
        """Generate all configured reports"""
        # Create tracking directory
        tracking_dir = Path('.claude/test_tracking')
        tracking_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate JSON report
        if self.config['test_runner']['reporting']['generate_json']:
            json_path = tracking_dir / 'test_results.json'
            self.json_reporter.generate_report(results, json_path)
            
        # Generate Markdown report
        if self.config['test_runner']['reporting']['generate_md']:
            md_path = tracking_dir / 'test_status.md'
            md_content = self.md_reporter.generate_report(results)
            md_path.write_text(md_content)
            
        print(f"\n📊 Reports saved to {tracking_dir}")
        
    def _display_summary(self, results: Dict) -> None:
        """Display test execution summary"""
        summary = results['summary']
        
        print("\n" + "=" * 60)
        print("📊 TEST EXECUTION SUMMARY")
        print("=" * 60)
        
        print(f"Total Files: {summary['total_files']}")
        print(f"Total Tests: {summary['total_tests']}")
        print(f"✅ Passed: {summary['passed']} ({summary['passed']/max(summary['total_tests'], 1)*100:.1f}%)")
        print(f"❌ Failed: {summary['failed']} ({summary['failed']/max(summary['total_tests'], 1)*100:.1f}%)")
        print(f"⏭️  Skipped: {summary['skipped']}")
        print(f"📈 Coverage: {summary['coverage_percent']}%")
        print(f"⏱️  Duration: {results['metadata']['duration_seconds']:.1f}s")
        
        if summary['failed'] > 0:
            print("\n❌ Tests failed! See test_results.json for details.")
        else:
            print("\n✅ All tests passed!")
            
    def _parse_since_date(self, since: str) -> datetime:
        """Parse since date string"""
        if since == 'yesterday':
            return datetime.now() - timedelta(days=1)
        elif since == 'last-week':
            return datetime.now() - timedelta(weeks=1)
        else:
            # Try to parse as date
            try:
                return datetime.fromisoformat(since)
            except:
                return datetime.now() - timedelta(days=1)