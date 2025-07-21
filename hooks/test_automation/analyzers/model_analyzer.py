"""
Model Analyzer
Detects and analyzes SQLAlchemy models and Pydantic schemas
"""

import ast
from typing import Dict, List, Optional, Any

from ..utils.logger import logger


class ModelAnalyzer:
    """Analyzes models and schemas"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    def analyze(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Analyze file content for models and schemas"""
        models = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check for SQLAlchemy model
                    if self._is_sqlalchemy_model(node):
                        model_info = self._extract_sqlalchemy_model(node)
                        if model_info:
                            models.append(model_info)
                            
                    # Check for Pydantic model
                    elif self._is_pydantic_model(node):
                        schema_info = self._extract_pydantic_schema(node)
                        if schema_info:
                            models.append(schema_info)
                            
        except Exception as e:
            logger.error(f"Error analyzing models in {file_path}: {e}")
            
        return models
        
    def _is_sqlalchemy_model(self, node: ast.ClassDef) -> bool:
        """Check if class is a SQLAlchemy model"""
        for base in node.bases:
            if hasattr(base, 'id') and base.id in ['Base', 'DeclarativeBase']:
                return True
            if hasattr(base, 'attr') and base.attr == 'Base':
                return True
        return False
        
    def _is_pydantic_model(self, node: ast.ClassDef) -> bool:
        """Check if class is a Pydantic model"""
        for base in node.bases:
            if hasattr(base, 'id') and 'BaseModel' in base.id:
                return True
            if hasattr(base, 'attr') and 'BaseModel' in base.attr:
                return True
        return False
        
    def _extract_sqlalchemy_model(self, node: ast.ClassDef) -> Dict[str, Any]:
        """Extract SQLAlchemy model information"""
        model_info = {
            'type': 'sqlalchemy',
            'name': node.name,
            'table_name': None,
            'fields': [],
            'relationships': [],
            'indexes': [],
            'constraints': []
        }
        
        for item in node.body:
            # Extract __tablename__
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if hasattr(target, 'id') and target.id == '__tablename__':
                        if isinstance(item.value, ast.Constant):
                            model_info['table_name'] = item.value.value
                            
            # Extract columns
            elif isinstance(item, ast.AnnAssign) and hasattr(item.target, 'id'):
                field_info = self._extract_sqlalchemy_field(item)
                if field_info:
                    if field_info.get('is_relationship'):
                        model_info['relationships'].append(field_info)
                    else:
                        model_info['fields'].append(field_info)
                        
        return model_info
        
    def _extract_sqlalchemy_field(self, node: ast.AnnAssign) -> Optional[Dict[str, Any]]:
        """Extract SQLAlchemy field information"""
        if not hasattr(node.target, 'id'):
            return None
            
        field_info = {
            'name': node.target.id,
            'type': None,
            'nullable': True,
            'primary_key': False,
            'unique': False,
            'foreign_key': None,
            'is_relationship': False
        }
        
        # Check if it's a Column
        if isinstance(node.value, ast.Call):
            if hasattr(node.value.func, 'id') and node.value.func.id == 'Column':
                # Extract column type
                if node.value.args:
                    field_info['type'] = self._get_column_type(node.value.args[0])
                    
                # Extract column options
                for keyword in node.value.keywords:
                    if keyword.arg == 'nullable':
                        field_info['nullable'] = self._get_bool_value(keyword.value)
                    elif keyword.arg == 'primary_key':
                        field_info['primary_key'] = self._get_bool_value(keyword.value)
                    elif keyword.arg == 'unique':
                        field_info['unique'] = self._get_bool_value(keyword.value)
                        
                # Check for ForeignKey in args
                for arg in node.value.args[1:]:
                    if isinstance(arg, ast.Call) and hasattr(arg.func, 'id'):
                        if arg.func.id == 'ForeignKey' and arg.args:
                            if isinstance(arg.args[0], ast.Constant):
                                field_info['foreign_key'] = arg.args[0].value
                                
            # Check if it's a relationship
            elif hasattr(node.value.func, 'id') and node.value.func.id == 'relationship':
                field_info['is_relationship'] = True
                if node.value.args and isinstance(node.value.args[0], ast.Constant):
                    field_info['related_model'] = node.value.args[0].value
                    
        return field_info
        
    def _extract_pydantic_schema(self, node: ast.ClassDef) -> Dict[str, Any]:
        """Extract Pydantic schema information"""
        schema_info = {
            'type': 'pydantic',
            'name': node.name,
            'fields': [],
            'validators': [],
            'config': {}
        }
        
        for item in node.body:
            # Extract fields
            if isinstance(item, ast.AnnAssign) and hasattr(item.target, 'id'):
                field_info = self._extract_pydantic_field(item)
                if field_info:
                    schema_info['fields'].append(field_info)
                    
            # Extract validators
            elif isinstance(item, ast.FunctionDef):
                for decorator in item.decorator_list:
                    if self._is_validator_decorator(decorator):
                        schema_info['validators'].append({
                            'name': item.name,
                            'fields': self._extract_validator_fields(decorator)
                        })
                        
            # Extract Config class
            elif isinstance(item, ast.ClassDef) and item.name == 'Config':
                schema_info['config'] = self._extract_config_options(item)
                
        return schema_info
        
    def _extract_pydantic_field(self, node: ast.AnnAssign) -> Dict[str, Any]:
        """Extract Pydantic field information"""
        field_info = {
            'name': node.target.id,
            'type': None,
            'required': True,
            'default': None,
            'validators': []
        }
        
        # Get type annotation
        if node.annotation:
            field_info['type'] = self._get_annotation_string(node.annotation)
            
        # Check for default value
        if node.value:
            if isinstance(node.value, ast.Constant):
                field_info['default'] = node.value.value
                field_info['required'] = False
            elif isinstance(node.value, ast.Call) and hasattr(node.value.func, 'id'):
                if node.value.func.id == 'Field':
                    field_info['required'] = False
                    # Extract Field options
                    for keyword in node.value.keywords:
                        if keyword.arg == 'default':
                            field_info['default'] = self._get_value(keyword.value)
                        elif keyword.arg == 'regex':
                            field_info['validators'].append({
                                'type': 'regex',
                                'pattern': self._get_value(keyword.value)
                            })
                        elif keyword.arg in ['gt', 'ge', 'lt', 'le']:
                            field_info['validators'].append({
                                'type': keyword.arg,
                                'value': self._get_value(keyword.value)
                            })
                            
        return field_info
        
    def _get_column_type(self, node: ast.AST) -> str:
        """Extract SQLAlchemy column type"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call) and hasattr(node.func, 'id'):
            return node.func.id
        return 'Unknown'
        
    def _get_annotation_string(self, annotation: ast.AST) -> str:
        """Convert annotation to string"""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Subscript):
            base = self._get_annotation_string(annotation.value)
            return f"{base}[...]"
        elif isinstance(annotation, ast.Attribute):
            return annotation.attr
        return 'Any'
        
    def _get_bool_value(self, node: ast.AST) -> bool:
        """Get boolean value from AST node"""
        if isinstance(node, ast.Constant):
            return bool(node.value)
        return False
        
    def _get_value(self, node: ast.AST) -> Any:
        """Get value from AST node"""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return node.id
        return None
        
    def _is_validator_decorator(self, decorator: ast.AST) -> bool:
        """Check if decorator is a Pydantic validator"""
        if isinstance(decorator, ast.Name) and decorator.id == 'validator':
            return True
        if isinstance(decorator, ast.Call) and hasattr(decorator.func, 'id'):
            return decorator.func.id == 'validator'
        return False
        
    def _extract_validator_fields(self, decorator: ast.AST) -> List[str]:
        """Extract fields from validator decorator"""
        fields = []
        if isinstance(decorator, ast.Call) and decorator.args:
            for arg in decorator.args:
                if isinstance(arg, ast.Constant):
                    fields.append(arg.value)
        return fields
        
    def _extract_config_options(self, config_class: ast.ClassDef) -> Dict[str, Any]:
        """Extract Pydantic Config options"""
        config = {}
        for item in config_class.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if hasattr(target, 'id'):
                        config[target.id] = self._get_value(item.value)
        return config