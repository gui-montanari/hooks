"""
Safety Analyzer
Analyzes changes and migrations for safety risks and data loss potential
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Set

from ..utils.logger import logger


class SafetyAnalyzer:
    """Analyzes safety risks in database changes"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.dangerous_operations = set(config.get('dangerous_operations', [
            'DROP TABLE',
            'DROP COLUMN', 
            'DROP CONSTRAINT',
            'ALTER COLUMN.*NOT NULL',
            'DELETE FROM',
            'TRUNCATE'
        ]))
        
        self.safety_thresholds = config.get('safety_thresholds', {
            'max_affected_rows_auto': 1000,
            'require_backup_above_rows': 10000,
            'require_staged_migration_above': 100000
        })
        
    def analyze_changes(self, changes: Dict[str, Any], 
                       dependencies: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze changes for safety risks"""
        report = {
            'risk_level': 'LOW',
            'risks': [],
            'warnings': [],
            'recommendations': [],
            'data_impact': {},
            'requires_backup': False,
            'requires_staging': False,
            'estimated_downtime': 0
        }
        
        if not changes or not changes.get('changes'):
            return report
            
        # Analyze each change
        for change in changes['changes']:
            risk_analysis = self._analyze_change_risk(change)
            
            # Update overall risk level
            report['risk_level'] = self._max_risk_level(
                report['risk_level'], risk_analysis['risk_level']
            )
            
            # Collect risks and warnings
            if risk_analysis['risk_level'] != 'LOW':
                report['risks'].append(risk_analysis)
                
            report['warnings'].extend(risk_analysis.get('warnings', []))
            report['recommendations'].extend(risk_analysis.get('recommendations', []))
            
            # Track data impact
            if 'table' in change:
                table = change['table']
                report['data_impact'][table] = self._estimate_data_impact(change)
                
        # Check cross-module risks
        if dependencies.get('cross_module'):
            report['warnings'].append(
                'Cross-module dependencies detected. Ensure proper migration order.'
            )
            report['recommendations'].append(
                f"Apply migrations in order: {' → '.join(dependencies['migration_order'])}"
            )
            
        # Calculate backup and staging requirements
        total_affected_rows = sum(
            impact.get('row_count', 0) 
            for impact in report['data_impact'].values()
        )
        
        if total_affected_rows > self.safety_thresholds['require_backup_above_rows']:
            report['requires_backup'] = True
            report['recommendations'].append(
                f"Backup recommended: {total_affected_rows:,} rows affected"
            )
            
        if total_affected_rows > self.safety_thresholds['require_staged_migration_above']:
            report['requires_staging'] = True
            report['recommendations'].append(
                "Consider staged migration due to large data volume"
            )
            
        # Estimate downtime
        report['estimated_downtime'] = self._estimate_downtime(changes, report)
        
        return report
        
    def _analyze_change_risk(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze risk for a single change"""
        risk = {
            'change': change,
            'risk_level': 'LOW',
            'warnings': [],
            'recommendations': []
        }
        
        change_type = change['type']
        
        # Analyze based on change type
        if change_type == 'DROP_TABLE':
            risk['risk_level'] = 'HIGH'
            risk['warnings'].append(f"Table '{change['table']}' will be permanently deleted")
            risk['recommendations'].append(
                f"CREATE TABLE {change['table']}_backup AS SELECT * FROM {change['table']};"
            )
            
        elif change_type == 'DROP_COLUMN':
            risk['risk_level'] = 'HIGH'
            risk['warnings'].append(
                f"Column '{change['column']}' data will be permanently lost"
            )
            risk['recommendations'].append(
                f"Consider renaming to '{change['column']}_deprecated' instead"
            )
            
        elif change_type == 'ADD_COLUMN':
            if not change.get('nullable', True) and not change.get('default'):
                risk['risk_level'] = 'MEDIUM'
                risk['warnings'].append(
                    'Adding NOT NULL column without default value will fail if table has data'
                )
                risk['recommendations'].append(
                    'Add column as nullable first, update data, then add NOT NULL constraint'
                )
                
        elif change_type == 'ALTER_COLUMN_TYPE':
            risk['risk_level'] = 'MEDIUM'
            risk['warnings'].append(
                f"Type change from {change['old_type']} to {change['new_type']} may fail"
            )
            risk['recommendations'].append(
                'Test type conversion on a data sample first'
            )
            
            # Check for lossy conversions
            if self._is_lossy_conversion(change['old_type'], change['new_type']):
                risk['risk_level'] = 'HIGH'
                risk['warnings'].append('Type conversion may result in data loss')
                
        elif change_type == 'ALTER_COLUMN_NULLABLE':
            if not change.get('nullable', True):
                risk['risk_level'] = 'MEDIUM'
                risk['warnings'].append(
                    'Setting column to NOT NULL will fail if NULL values exist'
                )
                risk['recommendations'].append(
                    f"UPDATE {change['table']} SET {change['column']} = <default> "
                    f"WHERE {change['column']} IS NULL;"
                )
                
        return risk
        
    def _is_lossy_conversion(self, old_type: str, new_type: str) -> bool:
        """Check if type conversion could lose data"""
        lossy_conversions = {
            ('VARCHAR', 'INTEGER'): True,
            ('TEXT', 'VARCHAR'): True,
            ('BIGINT', 'INTEGER'): True,
            ('NUMERIC', 'INTEGER'): True,
            ('TIMESTAMP', 'DATE'): True,
            ('DOUBLE', 'FLOAT'): True
        }
        
        old_base = old_type.upper().split('(')[0]
        new_base = new_type.upper().split('(')[0]
        
        return lossy_conversions.get((old_base, new_base), False)
        
    def _estimate_data_impact(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate the data impact of a change"""
        impact = {
            'row_count': 0,
            'data_size': 0,
            'has_data': False
        }
        
        # In a real implementation, this would query the database
        # For now, use mock data
        table_stats = {
            'users': {'rows': 10000, 'size_mb': 50},
            'files': {'rows': 50000, 'size_mb': 500},
            'conversations': {'rows': 25000, 'size_mb': 200},
            'agents': {'rows': 100, 'size_mb': 1},
            'sessions': {'rows': 100000, 'size_mb': 300}
        }
        
        table = change.get('table', '')
        if table in table_stats:
            stats = table_stats[table]
            impact['row_count'] = stats['rows']
            impact['data_size'] = stats['size_mb']
            impact['has_data'] = stats['rows'] > 0
            
        return impact
        
    def _estimate_downtime(self, changes: Dict[str, Any], 
                          safety_report: Dict[str, Any]) -> int:
        """Estimate migration downtime in seconds"""
        downtime = 0
        
        for change in changes.get('changes', []):
            change_type = change['type']
            
            # Base estimates
            if change_type == 'CREATE_TABLE':
                downtime += 1
            elif change_type == 'DROP_TABLE':
                downtime += 2
            elif change_type == 'ADD_COLUMN':
                # Depends on table size
                table = change.get('table', '')
                row_count = safety_report['data_impact'].get(table, {}).get('row_count', 0)
                downtime += max(1, row_count / 10000)  # 1 second per 10k rows
            elif change_type == 'DROP_COLUMN':
                downtime += 5
            elif change_type == 'ALTER_COLUMN_TYPE':
                # Type changes can be slow
                table = change.get('table', '')
                row_count = safety_report['data_impact'].get(table, {}).get('row_count', 0)
                downtime += max(5, row_count / 5000)  # 1 second per 5k rows
            elif change_type == 'CREATE_INDEX':
                # Index creation can be very slow
                table = change.get('table', '')
                row_count = safety_report['data_impact'].get(table, {}).get('row_count', 0)
                downtime += max(10, row_count / 1000)  # 1 second per 1k rows
                
        return int(downtime)
        
    def _max_risk_level(self, level1: str, level2: str) -> str:
        """Return the maximum risk level"""
        levels = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}
        
        if levels.get(level2, 0) > levels.get(level1, 0):
            return level2
        return level1
        
    def generate_safety_checks(self, changes: Dict[str, Any]) -> List[str]:
        """Generate SQL safety checks for changes"""
        checks = []
        
        for change in changes.get('changes', []):
            if change['type'] == 'DROP_COLUMN':
                # Check for non-null values
                checks.append(
                    f"-- Check data in column to be dropped\n"
                    f"SELECT COUNT(*), COUNT({change['column']}) "
                    f"FROM {change['table']};"
                )
                
            elif change['type'] == 'ALTER_COLUMN_NULLABLE' and not change.get('nullable'):
                # Check for null values
                checks.append(
                    f"-- Check for NULL values before adding NOT NULL\n"
                    f"SELECT COUNT(*) FROM {change['table']} "
                    f"WHERE {change['column']} IS NULL;"
                )
                
            elif change['type'] == 'ADD_COLUMN' and change.get('unique'):
                # Check uniqueness
                checks.append(
                    f"-- Verify uniqueness before adding constraint\n"
                    f"SELECT {change['column']}, COUNT(*) "
                    f"FROM {change['table']} "
                    f"GROUP BY {change['column']} "
                    f"HAVING COUNT(*) > 1;"
                )
                
        return checks
        
    def generate_rollback_script(self, changes: Dict[str, Any]) -> str:
        """Generate rollback SQL for changes"""
        rollback_statements = []
        
        for change in reversed(changes.get('changes', [])):
            if change['type'] == 'CREATE_TABLE':
                rollback_statements.append(
                    f"DROP TABLE IF EXISTS {change['table']};"
                )
                
            elif change['type'] == 'DROP_TABLE':
                rollback_statements.append(
                    f"-- Cannot rollback DROP TABLE without backup"
                )
                
            elif change['type'] == 'ADD_COLUMN':
                rollback_statements.append(
                    f"ALTER TABLE {change['table']} "
                    f"DROP COLUMN IF EXISTS {change['column']};"
                )
                
            elif change['type'] == 'DROP_COLUMN':
                rollback_statements.append(
                    f"-- Cannot rollback DROP COLUMN without backup"
                )
                
        return '\n'.join(rollback_statements)