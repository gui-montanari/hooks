"""
JSON Reporter
Generates detailed JSON reports for Claude analysis
"""

import json
from pathlib import Path
from typing import Dict, Any

from ..utils.logger import logger


class JsonReporter:
    """Generates JSON test reports"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    def generate_report(self, results: Dict[str, Any], output_path: Path) -> None:
        """Generate and save JSON report"""
        try:
            # Add commands for Claude
            results['commands_for_claude'] = self._generate_claude_commands(results)
            
            # Save report
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
                
            logger.info(f"Generated JSON report: {output_path}")
            
        except Exception as e:
            logger.error(f"Error generating JSON report: {e}")
            
    def _generate_claude_commands(self, results: Dict[str, Any]) -> Dict[str, str]:
        """Generate helpful commands for Claude"""
        commands = {
            'fix_failures': "To fix failing tests, analyze the errors in test_results.json",
            'improve_coverage': "Focus on untested_files list, especially aiagente module",
            'fix_flaky': "Check flaky_tests for patterns and add retry logic or fix root cause"
        }
        
        # Add specific recommendations based on results
        if results['summary']['failed'] > 0:
            commands['urgent'] = f"Fix {results['summary']['failed']} failing tests first"
            
        if results['summary']['coverage_percent'] < 80:
            commands['coverage'] = "Increase coverage to meet 80% minimum requirement"
            
        return commands