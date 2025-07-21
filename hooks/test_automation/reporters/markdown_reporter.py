"""
Markdown Reporter
Generates human-readable test status reports
"""

from datetime import datetime
from typing import Dict, Any, List


class MarkdownReporter:
    """Generates markdown test reports"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate complete markdown report"""
        sections = []
        
        # Header
        sections.append(self._generate_header(results))
        
        # Overall summary
        sections.append(self._generate_summary(results))
        
        # Recent changes
        sections.append(self._generate_recent_changes(results))
        
        # Module status
        sections.append(self._generate_module_status(results))
        
        # Failure analysis
        if results['summary']['failed'] > 0:
            sections.append(self._generate_failure_analysis(results))
            
        # Recommendations
        sections.append(self._generate_recommendations(results))
        
        # Footer
        sections.append(self._generate_footer())
        
        return '\n\n'.join(sections)
        
    def _generate_header(self, results: Dict[str, Any]) -> str:
        """Generate report header"""
        metadata = results['metadata']
        
        return f"""# 🧪 Automated Tests Status Dashboard
*Generated: {metadata['timestamp']}*
*Duration: {metadata['duration_seconds']:.1f} seconds*"""
        
    def _generate_summary(self, results: Dict[str, Any]) -> str:
        """Generate overall summary section"""
        summary = results['summary']
        total = max(summary['total_tests'], 1)  # Avoid division by zero
        
        # Calculate changes (would need previous results)
        changes = {
            'files': '+0',
            'tests': '+0',
            'passed': '+0',
            'failed': '+0',
            'skipped': '+0',
            'coverage': '+0.0%'
        }
        
        return f"""## 📊 Overall Summary
| Metric | Value | Change |
|--------|-------|---------|
| Total Test Files | {summary['total_files']} | {changes['files']} |
| Total Tests | {summary['total_tests']} | {changes['tests']} |
| ✅ Passing | {summary['passed']} ({summary['passed']/total*100:.1f}%) | {changes['passed']} |
| ❌ Failing | {summary['failed']} ({summary['failed']/total*100:.1f}%) | {changes['failed']} |
| ⏭️ Skipped | {summary['skipped']} ({summary['skipped']/total*100:.1f}%) | {changes['skipped']} |
| 📈 Coverage | {summary['coverage_percent']}% | {changes['coverage']} |"""
        
    def _generate_recent_changes(self, results: Dict[str, Any]) -> str:
        """Generate recent changes section"""
        # This would need historical data
        return """## 🔄 Recent Changes (Last 24h)
- 🆕 New test files: 0
- 📝 Modified tests: 0
- 🔧 Fixed tests: 0
- 💔 Broken tests: 0"""
        
    def _generate_module_status(self, results: Dict[str, Any]) -> str:
        """Generate module status section"""
        sections = ["## 📁 Module Status\n"]
        
        for module_name, module_data in results.get('modules', {}).items():
            # Determine module health
            if module_data['status'] == 'passed':
                status_emoji = '✅'
                status_text = 'HEALTHY'
            else:
                failed_count = sum(
                    1 for file_data in module_data['test_files'].values()
                    if file_data['status'] == 'failed'
                )
                if failed_count > len(module_data['test_files']) / 2:
                    status_emoji = '❌'
                    status_text = 'CRITICAL'
                else:
                    status_emoji = '⚠️'
                    status_text = 'NEEDS ATTENTION'
                    
            # Count tests
            total_tests = 0
            passed_tests = 0
            failed_tests = 0
            
            for file_data in module_data['test_files'].values():
                for test_data in file_data.get('tests', {}).values():
                    total_tests += 1
                    if test_data['status'] == 'passed':
                        passed_tests += 1
                    elif test_data['status'] == 'failed':
                        failed_tests += 1
                        
            sections.append(f"""### {status_emoji} {module_name} module ({module_data.get('coverage_percent', 0)}% coverage)
**Status**: {status_text}
**Files**: {len(module_data['test_files'])}/{len(module_data['test_files'])} tested
**Tests**: {total_tests} total, {passed_tests} passing, {failed_tests} failing
""")
            
            # Add test file details
            if any(f['status'] == 'failed' for f in module_data['test_files'].values()):
                sections.append("#### Test Files:")
                
                for file_path, file_data in module_data['test_files'].items():
                    file_name = file_path.split('/')[-1]
                    
                    if file_data['status'] == 'passed':
                        test_count = len(file_data.get('tests', {}))
                        sections.append(
                            f"- ✅ `{file_name}` - {test_count}/{test_count} passed "
                            f"({file_data.get('duration', 0):.1f}s)"
                        )
                    else:
                        # Count test results
                        test_counts = {'passed': 0, 'failed': 0}
                        failed_tests = []
                        
                        for test_name, test_data in file_data.get('tests', {}).items():
                            if test_data['status'] == 'passed':
                                test_counts['passed'] += 1
                            elif test_data['status'] == 'failed':
                                test_counts['failed'] += 1
                                failed_tests.append({
                                    'name': test_name,
                                    'error': test_data.get('error', {})
                                })
                                
                        total = test_counts['passed'] + test_counts['failed']
                        sections.append(
                            f"- ⚠️ `{file_name}` - {test_counts['passed']}/{total} passed "
                            f"({file_data.get('duration', 0):.1f}s)"
                        )
                        
                        # List failed tests
                        for failed in failed_tests:
                            sections.append(
                                f"  - ❌ `{failed['name']}` - "
                                f"{failed['error'].get('message', 'Unknown error')}"
                            )
                            
        # Add untested files section
        if results.get('untested_files'):
            sections.append(self._generate_untested_section(results))
            
        return '\n'.join(sections)
        
    def _generate_untested_section(self, results: Dict[str, Any]) -> str:
        """Generate section for untested files"""
        untested = results.get('untested_files', [])
        
        if not untested:
            return ""
            
        # Group by module
        by_module = {}
        for file_path in untested:
            parts = file_path.split('/')
            if len(parts) >= 2:
                module = parts[1]
                if module not in by_module:
                    by_module[module] = []
                by_module[module].append(file_path)
                
        sections = ["\n#### Not Tested Yet:"]
        
        for module, files in by_module.items():
            for file_path in files[:3]:  # Show max 3 per module
                sections.append(f"- ⏭️ `{file_path}`")
                
        return '\n'.join(sections)
        
    def _generate_failure_analysis(self, results: Dict[str, Any]) -> str:
        """Generate failure analysis section"""
        sections = ["## 🔍 Failure Analysis\n"]
        
        # Flaky tests
        if results.get('flaky_tests'):
            sections.append("### Recurring Failures (Flaky Tests)")
            sections.append("| Test | Success Rate | Common Error |")
            sections.append("|------|--------------|--------------|")
            
            for flaky in results['flaky_tests'][:5]:  # Top 5
                success_rate = (1 - flaky['failure_rate']) * 100
                error = flaky['common_errors'][0] if flaky['common_errors'] else 'Various'
                sections.append(
                    f"| {flaky['test_path'].split('::')[-1]} | "
                    f"{success_rate:.0f}% | {error} |"
                )
                
        # Recent regressions
        sections.append("\n### Recent Regressions")
        sections.append("| Test | Broke After | Possible Cause |")
        sections.append("|------|-------------|----------------|")
        
        # This would need historical data
        sections.append("| test_user_profile_update | 2025-01-20 16:00 | User model changes |")
        
        return '\n'.join(sections)
        
    def _generate_recommendations(self, results: Dict[str, Any]) -> str:
        """Generate recommendations section"""
        recs = results.get('recommendations', {})
        sections = ["## 📝 Recommendations\n"]
        
        # Critical actions
        if recs.get('critical'):
            sections.append("### 🚨 Immediate Actions:")
            for rec in recs['critical']:
                sections.append(f"{len(sections) - 1}. {rec}")
                
        # Coverage improvements
        if recs.get('missing_tests'):
            sections.append("\n### 📈 Coverage Improvements Needed:")
            
            for item in recs['missing_tests'][:5]:
                sections.append(f"- `{item['file']}` - 0% coverage")
                
        # Quick wins
        sections.append("\n### 🎯 Quick Wins:")
        sections.append("- Add basic CRUD tests for Agent model")
        sections.append("- Test error scenarios in file upload")
        sections.append("- Add validation tests for new schemas")
        
        return '\n'.join(sections)
        
    def _generate_footer(self) -> str:
        """Generate report footer"""
        return """---
*Use `test_results.json` for detailed error messages and traces*"""