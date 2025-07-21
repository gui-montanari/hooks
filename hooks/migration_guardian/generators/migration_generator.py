"""
Migration Generator
Generates Alembic migrations with safety comments and analysis
"""

import subprocess
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..utils.logger import logger


class MigrationGenerator:
    """Generates safe Alembic migrations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.naming_convention = config.get('naming_convention', {
            'format': '{timestamp}_{module}_{description}',
            'timestamp': '%Y_%m_%d_%H%M',
            'dangerous_suffix': '_DANGEROUS',
            'staged_suffix': '_staged',
            'module_separator': '_'
        })
        
    def generate(self, changes: Dict[str, Any], dependencies: Dict[str, Any],
                safety_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate migrations for the changes"""
        migrations = []
        
        try:
            module_name = changes['module']
            
            # Determine if we need staged migrations
            if safety_report.get('requires_staging'):
                migrations = self._generate_staged_migrations(
                    changes, dependencies, safety_report
                )
            else:
                # Generate single migration
                migration = self._generate_single_migration(
                    changes, dependencies, safety_report
                )
                if migration:
                    migrations.append(migration)
                    
        except Exception as e:
            logger.error(f"Error generating migrations: {e}")
            
        return migrations
        
    def _generate_single_migration(self, changes: Dict[str, Any],
                                 dependencies: Dict[str, Any],
                                 safety_report: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate a single migration file"""
        module_name = changes['module']
        
        # Generate description
        description = self._generate_description(changes)
        
        # Generate migration name
        migration_name = self._generate_migration_name(
            module_name, description, safety_report
        )
        
        # Run alembic revision command
        result = self._run_alembic_revision(migration_name)
        
        if not result['success']:
            logger.error(f"Failed to generate migration: {result['error']}")
            return None
            
        # Get the generated file path
        migration_file = result['file_path']
        
        # Add safety comments and analysis
        self._enhance_migration_file(
            migration_file, changes, dependencies, safety_report
        )
        
        return {
            'filename': migration_file.name,
            'filepath': str(migration_file),
            'module': module_name,
            'risk_level': safety_report['risk_level'],
            'warnings': safety_report.get('warnings', []),
            'description': description
        }
        
    def _generate_staged_migrations(self, changes: Dict[str, Any],
                                  dependencies: Dict[str, Any],
                                  safety_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate multiple staged migrations for complex changes"""
        migrations = []
        module_name = changes['module']
        
        # Group changes by risk and type
        staged_groups = self._group_changes_for_staging(changes['changes'])
        
        for i, (stage_name, stage_changes) in enumerate(staged_groups):
            # Create a changes dict for this stage
            stage_change_dict = {
                'module': module_name,
                'changes': stage_changes
            }
            
            # Generate description for this stage
            description = f"{stage_name}_step{i+1}"
            
            # Generate migration name
            migration_name = self._generate_migration_name(
                module_name, description, safety_report, staged=True
            )
            
            # Run alembic revision
            result = self._run_alembic_revision(migration_name)
            
            if result['success']:
                migration_file = result['file_path']
                
                # Add stage-specific comments
                self._enhance_staged_migration_file(
                    migration_file, stage_change_dict, i+1, len(staged_groups),
                    dependencies, safety_report
                )
                
                migrations.append({
                    'filename': migration_file.name,
                    'filepath': str(migration_file),
                    'module': module_name,
                    'stage': i+1,
                    'stage_name': stage_name,
                    'risk_level': safety_report['risk_level']
                })
                
        return migrations
        
    def _generate_description(self, changes: Dict[str, Any]) -> str:
        """Generate a descriptive name for the migration"""
        change_types = {}
        
        for change in changes['changes']:
            change_type = change['type']
            if change_type not in change_types:
                change_types[change_type] = 0
            change_types[change_type] += 1
            
        # Build description
        parts = []
        
        if 'CREATE_TABLE' in change_types:
            parts.append(f"create_{change_types['CREATE_TABLE']}_tables")
            
        if 'ADD_COLUMN' in change_types:
            parts.append(f"add_{change_types['ADD_COLUMN']}_columns")
            
        if 'DROP_TABLE' in change_types:
            parts.append(f"drop_{change_types['DROP_TABLE']}_tables")
            
        if 'DROP_COLUMN' in change_types:
            parts.append(f"drop_{change_types['DROP_COLUMN']}_columns")
            
        if 'ALTER_COLUMN_TYPE' in change_types:
            parts.append("alter_column_types")
            
        return '_'.join(parts) if parts else 'schema_changes'
        
    def _generate_migration_name(self, module: str, description: str,
                               safety_report: Dict[str, Any],
                               staged: bool = False) -> str:
        """Generate migration name following naming convention"""
        timestamp = datetime.now().strftime(self.naming_convention['timestamp'])
        
        name_parts = {
            'timestamp': timestamp,
            'module': module,
            'description': description
        }
        
        # Format name
        name = self.naming_convention['format'].format(**name_parts)
        
        # Add suffixes
        if staged:
            name += self.naming_convention['staged_suffix']
            
        if safety_report['risk_level'] == 'HIGH':
            name += self.naming_convention['dangerous_suffix']
            
        return name
        
    def _run_alembic_revision(self, message: str) -> Dict[str, Any]:
        """Run alembic revision command"""
        try:
            # Run alembic command
            cmd = ['alembic', 'revision', '--autogenerate', '-m', message]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Extract file path from output
            output = result.stdout
            file_match = re.search(r'Generating (.*\.py)', output)
            
            if file_match:
                file_path = Path(file_match.group(1))
                return {
                    'success': True,
                    'file_path': file_path,
                    'output': output
                }
            else:
                return {
                    'success': False,
                    'error': 'Could not find generated file in output'
                }
                
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f"Alembic command failed: {e.stderr}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
            
    def _enhance_migration_file(self, file_path: Path, changes: Dict[str, Any],
                              dependencies: Dict[str, Any],
                              safety_report: Dict[str, Any]) -> None:
        """Add safety comments and analysis to migration file"""
        try:
            content = file_path.read_text()
            
            # Generate header comment
            header = self._generate_migration_header(
                changes, dependencies, safety_report
            )
            
            # Insert header after imports
            import_end = content.find('revision =')
            if import_end > 0:
                content = content[:import_end] + header + '\n' + content[import_end:]
                
            # Add safety checks in upgrade function
            safety_checks = self._generate_safety_check_comments(safety_report)
            content = content.replace(
                'def upgrade():',
                f'def upgrade():{safety_checks}'
            )
            
            # Add rollback warnings in downgrade
            if safety_report['risk_level'] == 'HIGH':
                rollback_warning = '''
    # ⚠️  WARNING: High-risk rollback
    # Some operations cannot be fully rolled back without data loss
    # Ensure you have backups before proceeding
'''
                content = content.replace(
                    'def downgrade():',
                    f'def downgrade():{rollback_warning}'
                )
                
            # Write enhanced content
            file_path.write_text(content)
            
        except Exception as e:
            logger.error(f"Error enhancing migration file: {e}")
            
    def _generate_migration_header(self, changes: Dict[str, Any],
                                 dependencies: Dict[str, Any],
                                 safety_report: Dict[str, Any]) -> str:
        """Generate comprehensive header comment for migration"""
        risk_emoji = {'LOW': '✅', 'MEDIUM': '⚠️', 'HIGH': '🚨'}
        
        header = f'''
"""
Migration Guardian Analysis
==========================

Module: {changes['module']}
Risk Level: {risk_emoji[safety_report['risk_level']]} {safety_report['risk_level']}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Changes Summary:
---------------
'''
        
        # Add change summary
        for change in changes['changes']:
            header += f"- {change['type']}: "
            if 'table' in change:
                header += f"{change['table']}"
            if 'column' in change:
                header += f".{change['column']}"
            header += '\n'
            
        # Add affected rows
        if safety_report.get('data_impact'):
            header += '\nAffected Data:\n'
            header += '--------------\n'
            for table, impact in safety_report['data_impact'].items():
                header += f"- {table}: {impact['row_count']:,} rows\n"
                
        # Add estimated time
        header += f"\nEstimated Migration Time: ~{safety_report['estimated_downtime']} seconds\n"
        
        # Add dependencies
        if dependencies.get('cross_module'):
            header += '\nCross-Module Dependencies:\n'
            header += '-------------------------\n'
            for dep in dependencies['dependencies']:
                header += f"- {dep['from_module']} → {dep['to_module']} ({dep['reference']})\n"
                
        # Add warnings
        if safety_report.get('warnings'):
            header += '\n⚠️  WARNINGS:\n'
            header += '----------\n'
            for warning in safety_report['warnings']:
                header += f"- {warning}\n"
                
        # Add recommendations
        if safety_report.get('recommendations'):
            header += '\n💡 RECOMMENDATIONS:\n'
            header += '----------------\n'
            for rec in safety_report['recommendations']:
                header += f"- {rec}\n"
                
        # Add safety checklist
        if safety_report['risk_level'] != 'LOW':
            header += '\nSAFETY CHECKLIST:\n'
            header += '----------------\n'
            header += '[ ] Backup completed\n'
            header += '[ ] Tested on staging\n'
            
            if safety_report['risk_level'] == 'HIGH':
                header += '[ ] Downtime window scheduled\n'
                header += '[ ] Rollback plan prepared\n'
                header += '[ ] Team notified\n'
                
        header += '"""'
        
        return header
        
    def _generate_safety_check_comments(self, safety_report: Dict[str, Any]) -> str:
        """Generate safety check comments for upgrade function"""
        if safety_report['risk_level'] == 'LOW':
            return ''
            
        comments = '\n    # Migration Guardian Safety Checks\n'
        
        if safety_report['requires_backup']:
            comments += '    # ⚠️  BACKUP REQUIRED - Large number of rows affected\n'
            
        if safety_report.get('risks'):
            comments += '    # 🚨 HIGH RISK OPERATIONS:\n'
            for risk in safety_report['risks']:
                change = risk['change']
                comments += f"    #   - {change['type']}"
                if 'table' in change:
                    comments += f" on {change['table']}"
                comments += '\n'
                
        comments += '    \n'
        
        return comments
        
    def _enhance_staged_migration_file(self, file_path: Path,
                                     stage_changes: Dict[str, Any],
                                     stage_num: int, total_stages: int,
                                     dependencies: Dict[str, Any],
                                     safety_report: Dict[str, Any]) -> None:
        """Enhance staged migration file with stage-specific information"""
        try:
            content = file_path.read_text()
            
            # Generate staged header
            header = f'''
"""
Migration Guardian - Staged Migration (Step {stage_num}/{total_stages})
================================================================

This is part of a staged migration to safely apply complex changes.

Stage {stage_num} Operations:
'''
            
            for change in stage_changes['changes']:
                header += f"- {change['type']}: {change.get('table', 'unknown')}\n"
                
            header += f'''
            
⚠️  IMPORTANT: Apply all {total_stages} stages in order!
   
Previous stages must be completed before running this migration.
"""
'''
            
            # Insert header
            import_end = content.find('revision =')
            if import_end > 0:
                content = content[:import_end] + header + '\n' + content[import_end:]
                
            file_path.write_text(content)
            
        except Exception as e:
            logger.error(f"Error enhancing staged migration: {e}")
            
    def _group_changes_for_staging(self, changes: List[Dict[str, Any]]) -> List[tuple]:
        """Group changes into stages for safer application"""
        stages = []
        
        # Stage 1: Safe operations (create tables, add nullable columns)
        safe_changes = [
            c for c in changes 
            if c['type'] in ['CREATE_TABLE', 'ADD_COLUMN'] 
            and c.get('nullable', True)
        ]
        if safe_changes:
            stages.append(('safe_additions', safe_changes))
            
        # Stage 2: Data migrations
        data_changes = [
            c for c in changes
            if c['type'] in ['ALTER_COLUMN_TYPE']
        ]
        if data_changes:
            stages.append(('data_migrations', data_changes))
            
        # Stage 3: Constraint additions
        constraint_changes = [
            c for c in changes
            if (c['type'] == 'ADD_COLUMN' and not c.get('nullable', True)) or
            (c['type'] == 'ALTER_COLUMN_NULLABLE' and not c.get('nullable', True))
        ]
        if constraint_changes:
            stages.append(('add_constraints', constraint_changes))
            
        # Stage 4: Dangerous operations
        dangerous_changes = [
            c for c in changes
            if c['type'] in ['DROP_TABLE', 'DROP_COLUMN', 'DROP_CONSTRAINT']
        ]
        if dangerous_changes:
            stages.append(('dangerous_cleanup', dangerous_changes))
            
        return stages