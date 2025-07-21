"""
Result Tracker
Tracks test execution results
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from ..utils.logger import logger


class ResultTracker:
    """Tracks test results across executions"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tracking_dir = Path('.claude/test_tracking')
        self.tracking_dir.mkdir(parents=True, exist_ok=True)
        self.results_file = self.tracking_dir / 'test_results.json'
        
    def track_results(self, results: Dict[str, Any]) -> None:
        """Save test results"""
        try:
            # Save current results
            with open(self.results_file, 'w') as f:
                json.dump(results, f, indent=2)
                
            logger.info(f"Saved test results to {self.results_file}")
            
        except Exception as e:
            logger.error(f"Error saving test results: {e}")
            
    def get_latest_results(self) -> Optional[Dict[str, Any]]:
        """Get latest test results"""
        if self.results_file.exists():
            try:
                with open(self.results_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading test results: {e}")
                
        return None
        
    def get_module_results(self, module: str) -> Optional[Dict[str, Any]]:
        """Get results for specific module"""
        results = self.get_latest_results()
        if results and 'modules' in results:
            return results['modules'].get(module)
        return None
        
    def get_failed_tests(self) -> Dict[str, List[str]]:
        """Get all failed tests from latest results"""
        failed = {}
        results = self.get_latest_results()
        
        if not results:
            return failed
            
        for module_name, module_data in results.get('modules', {}).items():
            for file_path, file_data in module_data.get('test_files', {}).items():
                for test_name, test_data in file_data.get('tests', {}).items():
                    if test_data.get('status') == 'failed':
                        if file_path not in failed:
                            failed[file_path] = []
                        failed[file_path].append(test_name)
                        
        return failed