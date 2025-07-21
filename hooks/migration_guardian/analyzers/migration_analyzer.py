"""
Migration Analyzer
Analyzes generated migrations for potential issues and optimizations
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from ..utils.logger import logger


class MigrationAnalyzer:
    """Analyzes Alembic migrations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.alembic_dir = Path("alembic/versions")
        
    def analyze_migration(self, migration_path: Path) -> Dict[str, Any]:
        """Analyze a single migration file"""
        analysis = {
            'file': migration_path.name,
            'operations': [],
            'risks': [],
            'warnings': [],
            'recommendations': [],
            'estimated_time': 0,
            'affected_rows': {}
        }
        
        try:
            content = migration_path.read_text()
            
            # Extract operations
            operations = self._extract_operations(content)
            analysis['operations'] = operations
            
            # Analyze each operation
            for op in operations:
                op_analysis = self._analyze_operation(op)
                
                if op_analysis['risk'] != 'LOW':
                    analysis['risks'].append(op_analysis)
                    
                if op_analysis.get('warnings'):
                    analysis['warnings'].extend(op_analysis['warnings'])
                    
                if op_analysis.get('recommendations'):
                    analysis['recommendations'].extend(op_analysis['recommendations'])
                    
                # Estimate time
                analysis['estimated_time'] += op_analysis.get('estimated_time', 0)
                
                # Track affected rows
                if op_analysis.get('table'):
                    table = op_analysis['table']
                    if table not in analysis['affected_rows']:
                        analysis['affected_rows'][table] = self._estimate_row_count(table)
                        
        except Exception as e:
            logger.error(f"Error analyzing migration {migration_path}: {e}")
            analysis['warnings'].append(f"Analysis error: {e}")
            
        return analysis
        
    def _extract_operations(self, content: str) -> List[Dict[str, Any]]:
        """Extract operations from migration content"""
        operations = []
        
        # Pattern matching for common Alembic operations
        patterns = {
            'create_table': r'op\.create_table\s*\(\s*["\'](\w+)["\']',
            'drop_table': r'op\.drop_table\s*\(\s*["\'](\w+)["\']',
            'add_column': r'op\.add_column\s*\(\s*["\'](\w+)["\'],\s*sa\.Column\s*\(\s*["\'](\w+)["\']',
            'drop_column': r'op\.drop_column\s*\(\s*["\'](\w+)["\'],\s*["\'](\w+)["\']',
            'alter_column': r'op\.alter_column\s*\(\s*["\'](\w+)["\'],\s*["\'](\w+)["\']',
            'create_index': r'op\.create_index\s*\(\s*["\'](\w+)["\'],\s*["\'](\w+)["\']',
            'drop_index': r'op\.drop_index\s*\(\s*["\'](\w+)["\']',
            'create_foreign_key': r'op\.create_foreign_key\s*\([^,]+,\s*["\'](\w+)["\']',
            'drop_constraint': r'op\.drop_constraint\s*\([^,]+,\s*["\'](\w+)["\']',
            'execute': r'op\.execute\s*\(\s*["\']([^"\']+)["\']'
        }
        
        for op_type, pattern in patterns.items():
            matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
            
            for match in matches:
                operation = {
                    'type': op_type.upper(),
                    'line': content[:match.start()].count('\n') + 1
                }
                
                # Extract details based on operation type
                if op_type == 'create_table':
                    operation['table'] = match.group(1)
                elif op_type == 'drop_table':
                    operation['table'] = match.group(1)
                elif op_type in ['add_column', 'drop_column', 'alter_column']:
                    operation['table'] = match.group(1)
                    operation['column'] = match.group(2)
                elif op_type == 'create_index':
                    operation['index'] = match.group(1)
                    operation['table'] = match.group(2)
                elif op_type == 'drop_index':
                    operation['index'] = match.group(1)
                elif op_type == 'execute':
                    operation['sql'] = match.group(1)
                    
                # Extract additional context
                operation['context'] = self._extract_operation_context(content, match)
                
                operations.append(operation)
                
        return operations
        
    def _extract_operation_context(self, content: str, match: re.Match) -> Dict[str, Any]:
        """Extract additional context around an operation"""
        context = {}
        
        # Get surrounding lines
        lines = content.split('\n')
        line_num = content[:match.start()].count('\n')
        
        start_line = max(0, line_num - 5)
        end_line = min(len(lines), line_num + 10)
        
        context_lines = lines[start_line:end_line]
        context_text = '\n'.join(context_lines)
        
        # Check for nullable=False
        if 'nullable=False' in context_text:
            context['not_null'] = True
            
        # Check for unique constraint
        if 'unique=True' in context_text:
            context['unique'] = True
            
        # Check for default value
        default_match = re.search(r'server_default=([^,\)]+)', context_text)
        if default_match:
            context['default'] = default_match.group(1)
            
        # Check for type information
        type_match = re.search(r'sa\.(\w+)(?:\([^)]*\))?', context_text)
        if type_match:
            context['column_type'] = type_match.group(1)
            
        return context
        
    def _analyze_operation(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single operation for risks and issues"""
        analysis = {
            'operation': operation,
            'risk': 'LOW',
            'warnings': [],
            'recommendations': [],
            'estimated_time': 0
        }
        
        op_type = operation['type']
        
        # Analyze based on operation type
        if op_type == 'DROP_TABLE':
            analysis['risk'] = 'HIGH'
            analysis['warnings'].append('Table and all data will be permanently deleted')
            analysis['recommendations'].append('Create backup before dropping table')
            analysis['estimated_time'] = 1
            
        elif op_type == 'DROP_COLUMN':
            analysis['risk'] = 'HIGH'
            analysis['warnings'].append('Column data will be permanently lost')
            analysis['recommendations'].append('Consider backing up column data first')
            analysis['estimated_time'] = 5
            
        elif op_type == 'ADD_COLUMN':
            context = operation.get('context', {})
            
            if context.get('not_null') and not context.get('default'):
                analysis['risk'] = 'MEDIUM'
                analysis['warnings'].append('Adding NOT NULL column without default value')
                analysis['recommendations'].append('Consider adding default value or making nullable first')
                
            if context.get('unique'):
                analysis['risk'] = 'MEDIUM'
                analysis['warnings'].append('Adding unique constraint may fail if duplicates exist')
                analysis['recommendations'].append('Check for duplicate values before applying')
                
            analysis['estimated_time'] = 10
            
        elif op_type == 'ALTER_COLUMN':
            analysis['risk'] = 'MEDIUM'
            analysis['warnings'].append('Column alteration may fail with incompatible data')
            analysis['recommendations'].append('Test type conversion on sample data')
            analysis['estimated_time'] = 30
            
        elif op_type == 'DROP_CONSTRAINT':
            analysis['risk'] = 'MEDIUM'
            analysis['warnings'].append('Dropping constraint may allow invalid data')
            analysis['estimated_time'] = 5
            
        elif op_type == 'EXECUTE':
            sql = operation.get('sql', '').upper()
            
            if any(danger in sql for danger in ['DROP', 'DELETE', 'TRUNCATE']):
                analysis['risk'] = 'HIGH'
                analysis['warnings'].append('Raw SQL contains dangerous operations')
                
            analysis['estimated_time'] = 60  # Unknown, estimate high
            
        # Get table name for row count estimation
        if 'table' in operation:
            analysis['table'] = operation['table']
            
        return analysis
        
    def _estimate_row_count(self, table_name: str) -> int:
        """Estimate row count for a table"""
        # In a real implementation, this would query the database
        # For now, return a mock estimate
        estimates = {
            'users': 10000,
            'files': 50000,
            'conversations': 25000,
            'agents': 100,
            'sessions': 100000
        }
        
        return estimates.get(table_name, 1000)
        
    def check_migration_compatibility(self, migration_path: Path) -> Dict[str, Any]:
        """Check migration compatibility with different database versions"""
        compatibility = {
            'postgresql_14': True,
            'postgresql_13': True,
            'postgresql_12': True,
            'warnings': []
        }
        
        try:
            content = migration_path.read_text()
            
            # Check for version-specific features
            if 'GENERATED ALWAYS AS' in content:
                compatibility['postgresql_12'] = False
                compatibility['warnings'].append('Generated columns require PostgreSQL 12+')
                
            if 'INCLUDE' in content and 'INDEX' in content:
                compatibility['postgresql_12'] = False
                compatibility['warnings'].append('Index INCLUDE requires PostgreSQL 11+')
                
        except Exception as e:
            logger.error(f"Error checking compatibility: {e}")
            
        return compatibility
        
    def suggest_optimizations(self, operations: List[Dict[str, Any]]) -> List[str]:
        """Suggest optimizations for migration operations"""
        suggestions = []
        
        # Check for missing indexes on foreign keys
        for op in operations:
            if op['type'] == 'ADD_COLUMN' and op.get('context', {}).get('foreign_key'):
                suggestions.append(
                    f"Consider adding index on foreign key column {op['column']}"
                )
                
        # Check for multiple operations on same table
        table_ops = {}
        for op in operations:
            if 'table' in op:
                table = op['table']
                if table not in table_ops:
                    table_ops[table] = []
                table_ops[table].append(op)
                
        for table, ops in table_ops.items():
            if len(ops) > 3:
                suggestions.append(
                    f"Multiple operations on table '{table}'. "
                    "Consider combining for better performance"
                )
                
        return suggestions