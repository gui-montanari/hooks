"""
Model Change Detector
Detects changes in SQLAlchemy models for modular architecture
"""

import ast
import difflib
import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Any

from ..utils.logger import logger


class ModelChangeDetector:
    """Detects changes in SQLAlchemy models"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cache_dir = Path(".migration_guardian_cache")
        self.cache_dir.mkdir(exist_ok=True)
        
    def detect_changes(self, file_path: str, module_name: str) -> Dict[str, Any]:
        """Detect model changes in a file"""
        try:
            # Read current file content
            current_content = Path(file_path).read_text()
            
            # Get cached content
            cached_content = self._get_cached_content(file_path)
            
            if not cached_content:
                # First time seeing this file
                self._cache_content(file_path, current_content)
                return self._analyze_new_file(current_content, module_name)
                
            # Compare changes
            changes = self._compare_models(cached_content, current_content, module_name)
            
            # Update cache
            self._cache_content(file_path, current_content)
            
            return changes
            
        except Exception as e:
            logger.error(f"Error detecting changes in {file_path}: {e}")
            return {}
            
    def _get_cached_content(self, file_path: str) -> Optional[str]:
        """Get cached file content"""
        cache_file = self._get_cache_path(file_path)
        if cache_file.exists():
            return cache_file.read_text()
        return None
        
    def _cache_content(self, file_path: str, content: str) -> None:
        """Cache file content"""
        cache_file = self._get_cache_path(file_path)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(content)
        
    def _get_cache_path(self, file_path: str) -> Path:
        """Get cache file path"""
        # Create unique cache filename
        file_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
        return self.cache_dir / f"{Path(file_path).name}_{file_hash}.cache"
        
    def _analyze_new_file(self, content: str, module_name: str) -> Dict[str, Any]:
        """Analyze a new model file"""
        models = self._parse_models(content)
        
        if not models:
            return {}
            
        changes = {
            'module': module_name,
            'changes': []
        }
        
        for model in models:
            changes['changes'].append({
                'type': 'CREATE_TABLE',
                'table': model['table_name'],
                'model': model['class_name'],
                'fields': model['fields'],
                'constraints': model.get('constraints', []),
                'indexes': model.get('indexes', [])
            })
            
        return changes
        
    def _compare_models(self, old_content: str, new_content: str, module_name: str) -> Dict[str, Any]:
        """Compare old and new model versions"""
        old_models = self._parse_models(old_content)
        new_models = self._parse_models(new_content)
        
        old_by_name = {m['class_name']: m for m in old_models}
        new_by_name = {m['class_name']: m for m in new_models}
        
        changes = {
            'module': module_name,
            'changes': []
        }
        
        # Check for new tables
        for name, model in new_by_name.items():
            if name not in old_by_name:
                changes['changes'].append({
                    'type': 'CREATE_TABLE',
                    'table': model['table_name'],
                    'model': name,
                    'fields': model['fields']
                })
                
        # Check for removed tables
        for name, model in old_by_name.items():
            if name not in new_by_name:
                changes['changes'].append({
                    'type': 'DROP_TABLE',
                    'table': model['table_name'],
                    'model': name,
                    'risk': 'HIGH'
                })
                
        # Check for table changes
        for name in set(old_by_name) & set(new_by_name):
            old_model = old_by_name[name]
            new_model = new_by_name[name]
            
            # Compare fields
            field_changes = self._compare_fields(old_model, new_model)
            if field_changes:
                changes['changes'].extend(field_changes)
                
            # Compare constraints
            constraint_changes = self._compare_constraints(old_model, new_model)
            if constraint_changes:
                changes['changes'].extend(constraint_changes)
                
        return changes
        
    def _parse_models(self, content: str) -> List[Dict[str, Any]]:
        """Parse SQLAlchemy models from file content"""
        try:
            tree = ast.parse(content)
            models = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a SQLAlchemy model
                    if self._is_sqlalchemy_model(node):
                        model_info = self._extract_model_info(node)
                        if model_info:
                            models.append(model_info)
                            
            return models
            
        except Exception as e:
            logger.error(f"Error parsing models: {e}")
            return []
            
    def _is_sqlalchemy_model(self, node: ast.ClassDef) -> bool:
        """Check if class is a SQLAlchemy model"""
        # Check for Base inheritance
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id in ['Base', 'DeclarativeBase']:
                return True
            if isinstance(base, ast.Attribute) and base.attr == 'Base':
                return True
        return False
        
    def _extract_model_info(self, node: ast.ClassDef) -> Optional[Dict[str, Any]]:
        """Extract model information from AST node"""
        model_info = {
            'class_name': node.name,
            'table_name': None,
            'fields': [],
            'constraints': [],
            'indexes': []
        }
        
        for item in node.body:
            # Extract __tablename__
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == '__tablename__':
                        if isinstance(item.value, ast.Constant):
                            model_info['table_name'] = item.value.value
                            
            # Extract Column definitions
            elif isinstance(item, ast.AnnAssign) and isinstance(item.value, ast.Call):
                if self._is_column_definition(item.value):
                    field_info = self._extract_field_info(item)
                    if field_info:
                        model_info['fields'].append(field_info)
                        
        # If no table name found, use lowercase class name
        if not model_info['table_name']:
            model_info['table_name'] = self._camel_to_snake(node.name) + 's'
            
        return model_info if model_info['fields'] else None
        
    def _is_column_definition(self, node: ast.Call) -> bool:
        """Check if call is a Column definition"""
        if isinstance(node.func, ast.Name) and node.func.id == 'Column':
            return True
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'Column':
            return True
        return False
        
    def _extract_field_info(self, node: ast.AnnAssign) -> Optional[Dict[str, Any]]:
        """Extract field information from Column definition"""
        try:
            field_info = {
                'name': node.target.id if isinstance(node.target, ast.Name) else None,
                'type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'foreign_key': None,
                'default': None
            }
            
            if not field_info['name']:
                return None
                
            # Extract column type and constraints from arguments
            if isinstance(node.value, ast.Call) and node.value.args:
                # First argument is usually the type
                type_arg = node.value.args[0]
                field_info['type'] = self._extract_type_name(type_arg)
                
                # Check for constraints in arguments
                for arg in node.value.args[1:]:
                    if isinstance(arg, ast.Call):
                        constraint_type = self._extract_constraint_type(arg)
                        if constraint_type == 'ForeignKey':
                            field_info['foreign_key'] = self._extract_foreign_key(arg)
                            
                # Check keyword arguments
                for keyword in node.value.keywords:
                    if keyword.arg == 'nullable':
                        field_info['nullable'] = self._get_bool_value(keyword.value)
                    elif keyword.arg == 'primary_key':
                        field_info['primary_key'] = self._get_bool_value(keyword.value)
                    elif keyword.arg == 'unique':
                        field_info['unique'] = self._get_bool_value(keyword.value)
                    elif keyword.arg == 'default':
                        field_info['default'] = self._extract_default_value(keyword.value)
                        
            return field_info
            
        except Exception as e:
            logger.error(f"Error extracting field info: {e}")
            return None
            
    def _extract_type_name(self, node: ast.AST) -> str:
        """Extract type name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id
            elif isinstance(node.func, ast.Attribute):
                return node.func.attr
        return "Unknown"
        
    def _extract_constraint_type(self, node: ast.Call) -> Optional[str]:
        """Extract constraint type from call"""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None
        
    def _extract_foreign_key(self, node: ast.Call) -> Optional[str]:
        """Extract foreign key reference"""
        if node.args and isinstance(node.args[0], ast.Constant):
            return node.args[0].value
        return None
        
    def _get_bool_value(self, node: ast.AST) -> bool:
        """Get boolean value from AST node"""
        if isinstance(node, ast.Constant):
            return bool(node.value)
        elif isinstance(node, ast.NameConstant):
            return bool(node.value)
        return False
        
    def _extract_default_value(self, node: ast.AST) -> Any:
        """Extract default value"""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Call):
            return f"{self._extract_type_name(node)}()"
        return None
        
    def _compare_fields(self, old_model: Dict, new_model: Dict) -> List[Dict[str, Any]]:
        """Compare fields between old and new model"""
        changes = []
        table_name = old_model['table_name']
        
        old_fields = {f['name']: f for f in old_model['fields']}
        new_fields = {f['name']: f for f in new_model['fields']}
        
        # Check for new fields
        for name, field in new_fields.items():
            if name not in old_fields:
                change = {
                    'type': 'ADD_COLUMN',
                    'table': table_name,
                    'column': name,
                    'column_type': field['type'],
                    'nullable': field['nullable'],
                    'default': field['default']
                }
                
                # Check if adding NOT NULL without default
                if not field['nullable'] and not field['default']:
                    change['risk'] = 'MEDIUM'
                    change['warning'] = 'Adding NOT NULL column without default value'
                    
                changes.append(change)
                
        # Check for removed fields
        for name, field in old_fields.items():
            if name not in new_fields:
                changes.append({
                    'type': 'DROP_COLUMN',
                    'table': table_name,
                    'column': name,
                    'risk': 'HIGH',
                    'warning': 'Data will be permanently lost'
                })
                
        # Check for field modifications
        for name in set(old_fields) & set(new_fields):
            old_field = old_fields[name]
            new_field = new_fields[name]
            
            # Type change
            if old_field['type'] != new_field['type']:
                changes.append({
                    'type': 'ALTER_COLUMN_TYPE',
                    'table': table_name,
                    'column': name,
                    'old_type': old_field['type'],
                    'new_type': new_field['type'],
                    'risk': 'MEDIUM',
                    'warning': 'Type conversion may fail or lose precision'
                })
                
            # Nullable change
            if old_field['nullable'] != new_field['nullable']:
                changes.append({
                    'type': 'ALTER_COLUMN_NULLABLE',
                    'table': table_name,
                    'column': name,
                    'nullable': new_field['nullable'],
                    'risk': 'LOW' if new_field['nullable'] else 'MEDIUM'
                })
                
        return changes
        
    def _compare_constraints(self, old_model: Dict, new_model: Dict) -> List[Dict[str, Any]]:
        """Compare constraints between models"""
        changes = []
        # TODO: Implement constraint comparison
        return changes
        
    def _camel_to_snake(self, name: str) -> str:
        """Convert CamelCase to snake_case"""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()