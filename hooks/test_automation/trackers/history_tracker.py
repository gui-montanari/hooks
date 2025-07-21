"""
History Tracker
Tracks test execution history for trend analysis
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

from ..utils.logger import logger


class HistoryTracker:
    """Tracks test history across multiple executions"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.history_dir = Path('.claude/test_tracking/history')
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.history_size = config['test_runner']['tracking']['history_size']
        
    def add_to_history(self, results: Dict[str, Any]) -> None:
        """Add results to history"""
        try:
            # Generate filename with timestamp
            timestamp = results['metadata']['timestamp']
            command_type = self._extract_command_type(results)
            filename = f"{timestamp.replace(':', '-')}_{command_type}.json"
            
            # Save to history
            history_file = self.history_dir / filename
            with open(history_file, 'w') as f:
                json.dump(results, f, indent=2)
                
            # Clean up old history
            self._cleanup_old_history()
            
            logger.info(f"Added to history: {filename}")
            
        except Exception as e:
            logger.error(f"Error adding to history: {e}")
            
    def get_test_history(self, test_path: str) -> List[Dict[str, Any]]:
        """Get history for specific test"""
        history = []
        
        for history_file in sorted(self.history_dir.glob('*.json'), reverse=True):
            try:
                with open(history_file) as f:
                    results = json.load(f)
                    
                # Search for test in results
                for module_data in results.get('modules', {}).values():
                    for file_path, file_data in module_data.get('test_files', {}).items():
                        if test_path in file_path:
                            for test_name, test_data in file_data.get('tests', {}).items():
                                if test_path.endswith(test_name):
                                    history.append({
                                        'timestamp': results['metadata']['timestamp'],
                                        'status': test_data['status'],
                                        'duration': test_data.get('duration', 0)
                                    })
                                    
            except Exception as e:
                logger.error(f"Error reading history file {history_file}: {e}")
                
        return history[:self.history_size]
        
    def identify_flaky_tests(self) -> List[Dict[str, Any]]:
        """Identify tests that fail intermittently"""
        test_runs = defaultdict(list)
        
        # Collect all test runs
        for history_file in sorted(self.history_dir.glob('*.json'), reverse=True)[:10]:  # Last 10 runs
            try:
                with open(history_file) as f:
                    results = json.load(f)
                    
                for module_name, module_data in results.get('modules', {}).items():
                    for file_path, file_data in module_data.get('test_files', {}).items():
                        for test_name, test_data in file_data.get('tests', {}).items():
                            test_key = f"{file_path}::{test_name}"
                            test_runs[test_key].append(test_data['status'])
                            
            except Exception as e:
                logger.error(f"Error reading history: {e}")
                
        # Identify flaky tests
        flaky_tests = []
        threshold = self.config['test_runner']['tracking']['identify_flaky_threshold']
        
        for test_path, statuses in test_runs.items():
            if len(statuses) >= 3:  # Need at least 3 runs
                failure_rate = statuses.count('failed') / len(statuses)
                
                # Flaky if it fails sometimes but not always
                if 0 < failure_rate < threshold:
                    flaky_tests.append({
                        'test_path': test_path,
                        'failure_rate': failure_rate,
                        'last_5_runs': statuses[:5],
                        'common_errors': self._get_common_errors(test_path)
                    })
                    
        return sorted(flaky_tests, key=lambda x: x['failure_rate'], reverse=True)
        
    def get_failed_tests(self) -> List[str]:
        """Get list of tests that failed in last run"""
        failed = []
        
        # Get most recent history file
        history_files = sorted(self.history_dir.glob('*.json'), reverse=True)
        if not history_files:
            return failed
            
        try:
            with open(history_files[0]) as f:
                results = json.load(f)
                
            for module_data in results.get('modules', {}).values():
                for file_path, file_data in module_data.get('test_files', {}).items():
                    for test_name, test_data in file_data.get('tests', {}).items():
                        if test_data.get('status') == 'failed':
                            failed.append(f"{file_path}::{test_name}")
                            
        except Exception as e:
            logger.error(f"Error getting failed tests: {e}")
            
        return failed
        
    def get_failed_test_files(self) -> List[str]:
        """Get list of test files with failures"""
        failed_files = set()
        
        # Get most recent history file
        history_files = sorted(self.history_dir.glob('*.json'), reverse=True)
        if not history_files:
            return []
            
        try:
            with open(history_files[0]) as f:
                results = json.load(f)
                
            for module_data in results.get('modules', {}).values():
                for file_path, file_data in module_data.get('test_files', {}).items():
                    if file_data.get('status') == 'failed':
                        failed_files.add(file_path)
                        
        except Exception as e:
            logger.error(f"Error getting failed test files: {e}")
            
        return list(failed_files)
        
    def get_tested_files(self) -> set:
        """Get set of all files that have been tested"""
        tested = set()
        
        for history_file in self.history_dir.glob('*.json'):
            try:
                with open(history_file) as f:
                    results = json.load(f)
                    
                for module_data in results.get('modules', {}).values():
                    tested.update(module_data.get('test_files', {}).keys())
                    
            except Exception as e:
                logger.error(f"Error reading history: {e}")
                
        return tested
        
    def _extract_command_type(self, results: Dict[str, Any]) -> str:
        """Extract command type from results"""
        command = results['metadata'].get('command', '')
        
        if '--module' in command:
            # Extract module name
            parts = command.split()
            for i, part in enumerate(parts):
                if part == '--module' and i + 1 < len(parts):
                    return parts[i + 1]
                    
        elif '--failed' in command:
            return 'failed_only'
        elif '--not-tested' in command:
            return 'not_tested'
        else:
            return 'full'
            
    def _cleanup_old_history(self) -> None:
        """Remove old history files beyond configured size"""
        history_files = sorted(self.history_dir.glob('*.json'))
        
        # Keep only recent files
        max_files = self.history_size * 5  # Keep more files than test history
        
        if len(history_files) > max_files:
            for old_file in history_files[:-max_files]:
                try:
                    old_file.unlink()
                    logger.info(f"Removed old history file: {old_file}")
                except Exception as e:
                    logger.error(f"Error removing history file: {e}")
                    
    def _get_common_errors(self, test_path: str) -> List[str]:
        """Get common error messages for a test"""
        errors = []
        
        for history_file in sorted(self.history_dir.glob('*.json'), reverse=True)[:5]:
            try:
                with open(history_file) as f:
                    results = json.load(f)
                    
                # Find test and extract error
                for module_data in results.get('modules', {}).values():
                    for file_path, file_data in module_data.get('test_files', {}).items():
                        for test_name, test_data in file_data.get('tests', {}).items():
                            if f"{file_path}::{test_name}" == test_path:
                                if test_data.get('status') == 'failed':
                                    error = test_data.get('error', {})
                                    if error.get('message'):
                                        errors.append(error['message'])
                                        
            except Exception as e:
                logger.error(f"Error getting errors: {e}")
                
        # Return unique errors
        return list(set(errors))