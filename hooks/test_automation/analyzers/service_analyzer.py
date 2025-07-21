"""
Service Analyzer
Detects and analyzes service classes and functions for test generation
"""

import ast
from typing import Dict, List, Optional, Any

from ..utils.logger import logger


class ServiceAnalyzer:
    """Analyzes service classes and functions"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    def analyze(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Analyze file content for services"""
        services = []
        
        try:
            tree = ast.parse(content)
            
            # Find service classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if self._is_service_class(node):
                        service_info = self._extract_service_info(node)
                        if service_info:
                            services.append(service_info)
                            
                # Also find standalone service functions
                elif isinstance(node, ast.FunctionDef):
                    if self._is_service_function(node):
                        func_info = self._extract_function_info(node)
                        if func_info:
                            services.append(func_info)
                            
        except Exception as e:
            logger.error(f"Error analyzing services in {file_path}: {e}")
            
        return services
        
    def _is_service_class(self, node: ast.ClassDef) -> bool:
        """Check if class is a service class"""
        # Check class name
        if 'service' in node.name.lower():
            return True
            
        # Check base classes
        for base in node.bases:
            if hasattr(base, 'id') and 'service' in base.id.lower():
                return True
                
        # Check if it has service-like methods
        service_methods = ['create', 'get', 'update', 'delete', 'list', 'find']
        method_names = [item.name for item in node.body if isinstance(item, ast.FunctionDef)]
        
        matching_methods = sum(1 for method in service_methods if any(method in name for name in method_names))
        return matching_methods >= 2
        
    def _is_service_function(self, node: ast.FunctionDef) -> bool:
        """Check if function is a service function"""
        # Skip private and special methods
        if node.name.startswith('_'):
            return False
            
        # Check function name patterns
        service_patterns = [
            'create_', 'get_', 'update_', 'delete_', 'list_',
            'find_', 'search_', 'process_', 'calculate_', 'validate_'
        ]
        
        return any(node.name.startswith(pattern) for pattern in service_patterns)
        
    def _extract_service_info(self, node: ast.ClassDef) -> Dict[str, Any]:
        """Extract service class information"""
        methods = []
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and not item.name.startswith('_'):
                method_info = {
                    'name': item.name,
                    'is_async': isinstance(item, ast.AsyncFunctionDef),
                    'parameters': self._extract_parameters(item),
                    'returns': self._extract_return_type(item),
                    'raises': self._extract_exceptions(item),
                    'docstring': ast.get_docstring(item) or ''
                }
                methods.append(method_info)
                
        return {
            'type': 'class',
            'name': node.name,
            'methods': methods,
            'docstring': ast.get_docstring(node) or '',
            'dependencies': self._extract_dependencies(node)
        }
        
    def _extract_function_info(self, node: ast.FunctionDef) -> Dict[str, Any]:
        """Extract standalone function information"""
        return {
            'type': 'function',
            'name': node.name,
            'is_async': isinstance(node, ast.AsyncFunctionDef),
            'parameters': self._extract_parameters(node),
            'returns': self._extract_return_type(node),
            'raises': self._extract_exceptions(node),
            'docstring': ast.get_docstring(node) or '',
            'methods': []  # For compatibility
        }
        
    def _extract_parameters(self, node: ast.FunctionDef) -> List[Dict[str, Any]]:
        """Extract function parameters"""
        params = []
        
        for arg in node.args.args:
            if arg.arg == 'self':
                continue
                
            param_info = {
                'name': arg.arg,
                'type': None,
                'has_default': False
            }
            
            if arg.annotation:
                param_info['type'] = self._get_annotation_string(arg.annotation)
                
            params.append(param_info)
            
        # Check for defaults
        defaults_start = len(node.args.args) - len(node.args.defaults)
        for i, default in enumerate(node.args.defaults):
            param_index = defaults_start + i
            if param_index < len(params):
                params[param_index]['has_default'] = True
                
        return params
        
    def _extract_return_type(self, node: ast.FunctionDef) -> Optional[str]:
        """Extract return type annotation"""
        if node.returns:
            return self._get_annotation_string(node.returns)
        return None
        
    def _extract_exceptions(self, node: ast.FunctionDef) -> List[str]:
        """Extract exceptions that might be raised"""
        exceptions = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.Raise):
                if isinstance(child.exc, ast.Call) and hasattr(child.exc.func, 'id'):
                    exceptions.append(child.exc.func.id)
                elif isinstance(child.exc, ast.Name):
                    exceptions.append(child.exc.id)
                    
        return list(set(exceptions))
        
    def _extract_dependencies(self, node: ast.ClassDef) -> List[str]:
        """Extract class dependencies from __init__"""
        dependencies = []
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                for arg in item.args.args[1:]:  # Skip self
                    if arg.annotation:
                        dep_type = self._get_annotation_string(arg.annotation)
                        dependencies.append({
                            'name': arg.arg,
                            'type': dep_type
                        })
                        
        return dependencies
        
    def _get_annotation_string(self, annotation: ast.AST) -> str:
        """Convert annotation AST to string"""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Attribute):
            return f"{self._get_annotation_string(annotation.value)}.{annotation.attr}"
        elif isinstance(annotation, ast.Subscript):
            return f"{self._get_annotation_string(annotation.value)}[...]"
        else:
            return 'Any'