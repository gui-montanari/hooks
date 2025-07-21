#!/usr/bin/env python3
"""
Migration Guardian Main Hook
Monitors SQLAlchemy model changes and automates safe migration generation
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any

from .detectors.model_detector import ModelChangeDetector
from .detectors.dependency_detector import DependencyDetector
from .analyzers.migration_analyzer import MigrationAnalyzer
from .analyzers.safety_analyzer import SafetyAnalyzer
from .generators.migration_generator import MigrationGenerator
from .utils.config import load_config
from .utils.logger import logger
from .utils.formatter import format_report, format_alert


class MigrationGuardian:
    """Main Migration Guardian hook class"""
    
    def __init__(self):
        self.config = load_config()
        self.model_detector = ModelChangeDetector(self.config)
        self.dependency_detector = DependencyDetector(self.config)
        self.migration_analyzer = MigrationAnalyzer(self.config)
        self.safety_analyzer = SafetyAnalyzer(self.config)
        self.migration_generator = MigrationGenerator(self.config)
        
    def run(self, hook_data: Dict[str, Any]) -> None:
        """Main entry point for the hook"""
        try:
            # Parse hook data
            tool_name = hook_data.get('tool', '')
            if tool_name not in ['Write', 'Edit', 'MultiEdit']:
                return
                
            file_path = self._extract_file_path(hook_data)
            if not file_path or not self._is_model_file(file_path):
                return
                
            # Extract module name from path
            module_name = self._extract_module_name(file_path)
            if not module_name:
                return
                
            logger.info(f"🔍 Migration Guardian: Detected changes in {module_name} module")
            
            # Detect model changes
            changes = self.model_detector.detect_changes(file_path, module_name)
            if not changes:
                return
                
            # Check for cross-module dependencies
            dependencies = self.dependency_detector.analyze_dependencies(changes)
            
            # Analyze safety
            safety_report = self.safety_analyzer.analyze_changes(changes, dependencies)
            
            # Generate migration if safe or user confirms
            if self._should_generate_migration(safety_report):
                migrations = self.migration_generator.generate(
                    changes, dependencies, safety_report
                )
                
                # Display report
                self._display_report(migrations, changes, dependencies, safety_report)
                
                # Save report
                self._save_report(migrations, changes, dependencies, safety_report)
                
        except Exception as e:
            logger.error(f"Migration Guardian Error: {e}")
            print(f"❌ Migration Guardian encountered an error: {e}")
            
    def _extract_file_path(self, hook_data: Dict[str, Any]) -> Optional[str]:
        """Extract file path from hook data"""
        params = hook_data.get('params', {})
        return params.get('file_path') or params.get('path')
        
    def _is_model_file(self, file_path: str) -> bool:
        """Check if file matches monitored patterns"""
        path = Path(file_path)
        patterns = self.config.get('monitored_paths', [])
        
        for pattern in patterns:
            # Convert glob pattern to regex
            regex_pattern = pattern.replace('**/', '.*').replace('*', '[^/]*')
            if re.match(regex_pattern, str(path)):
                return True
        return False
        
    def _extract_module_name(self, file_path: str) -> Optional[str]:
        """Extract module name from file path"""
        # Expected pattern: app/{module}/models/*.py
        path_parts = Path(file_path).parts
        
        if len(path_parts) >= 3 and path_parts[0] == 'app' and path_parts[2] == 'models':
            return path_parts[1]
        return None
        
    def _should_generate_migration(self, safety_report: Dict) -> bool:
        """Determine if migration should be generated"""
        if safety_report['risk_level'] == 'LOW':
            return True
            
        if self.config.get('block_dangerous', False) and safety_report['risk_level'] == 'HIGH':
            print("\n🚨 DANGEROUS OPERATION BLOCKED!")
            print("Set 'block_dangerous': false in config to allow")
            return False
            
        # Show warning and ask for confirmation
        print(format_alert(safety_report))
        
        if self.config.get('require_review', True):
            response = input("\n⚠️  Proceed with migration generation? [y/N]: ")
            return response.lower() == 'y'
            
        return True
        
    def _display_report(self, migrations: List[Dict], changes: Dict, 
                       dependencies: Dict, safety_report: Dict) -> None:
        """Display formatted report to user"""
        print("\n" + "="*60)
        print("🔄 MIGRATION GUARDIAN REPORT")
        print("="*60)
        
        # Module summary
        print(f"\n📦 Module: {changes['module']}")
        print(f"📝 Changes detected: {len(changes['changes'])}")
        
        # Dependencies
        if dependencies['cross_module']:
            print("\n🔗 Cross-Module Dependencies:")
            for dep in dependencies['dependencies']:
                print(f"   {dep['from_module']} → {dep['to_module']} ({dep['type']})")
                
        # Safety summary
        risk_emoji = {'LOW': '✅', 'MEDIUM': '⚠️', 'HIGH': '🔴'}
        print(f"\n🛡️ Risk Level: {risk_emoji[safety_report['risk_level']]} {safety_report['risk_level']}")
        
        # Migrations generated
        print(f"\n📝 Migrations Generated: {len(migrations)}")
        for i, migration in enumerate(migrations, 1):
            print(f"   {i}. {migration['filename']}")
            if migration.get('warnings'):
                for warning in migration['warnings']:
                    print(f"      ⚠️  {warning}")
                    
        # Recommendations
        if safety_report.get('recommendations'):
            print("\n💡 Recommendations:")
            for rec in safety_report['recommendations']:
                print(f"   • {rec}")
                
        print("\n" + "="*60)
        
    def _save_report(self, migrations: List[Dict], changes: Dict,
                    dependencies: Dict, safety_report: Dict) -> None:
        """Save detailed report to file"""
        report_dir = Path("migration_guardian_reports")
        report_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        report_file = report_dir / f"{timestamp}_analysis.json"
        
        report_data = {
            'timestamp': timestamp,
            'module': changes['module'],
            'changes': changes,
            'dependencies': dependencies,
            'safety_report': safety_report,
            'migrations': migrations
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
            
        # Also save markdown report
        md_file = report_dir / f"{timestamp}_analysis.md"
        with open(md_file, 'w') as f:
            f.write(format_report(report_data))
            
        print(f"\n📄 Detailed report saved to: {report_file}")


def main():
    """Hook entry point"""
    # Read hook data from stdin
    hook_data = json.loads(sys.stdin.read())
    
    # Run Migration Guardian
    guardian = MigrationGuardian()
    guardian.run(hook_data)


if __name__ == "__main__":
    main()