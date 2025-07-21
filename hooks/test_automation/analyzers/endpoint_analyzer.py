"""
Endpoint Analyzer
Detects and analyzes FastAPI endpoints for test generation
"""

import ast
import re
from typing import Dict, List, Optional, Any, Set
from pathlib import Path

from ..utils.logger import logger


class EndpointAnalyzer:
    """Analyzes FastAPI endpoints and extracts test information"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    def analyze(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Analyze file content for endpoints"""
        endpoints = []
        
        try:
            # Parse AST
            tree = ast.parse(content)
            
            # Find router instance
            router_name = self._find_router_instance(tree)
            if not router_name:
                return endpoints
                
            # Find all endpoint decorators
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    endpoint_info = self._extract_endpoint_info(
                        node, router_name, content
                    )
                    if endpoint_info:
                        endpoints.append(endpoint_info)
                        
        except Exception as e:
            logger.error(f"Error analyzing endpoints in {file_path}: {e}")
            
        return endpoints
        
    def _find_router_instance(self, tree: ast.AST) -> Optional[str]:
        """Find FastAPI router instance name"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                # Check for APIRouter assignment
                if isinstance(node.value, ast.Call):
                    if hasattr(node.value.func, 'id') and node.value.func.id == 'APIRouter':
                        if node.targets and hasattr(node.targets[0], 'id'):
                            return node.targets[0].id
                    elif hasattr(node.value.func, 'attr') and node.value.func.attr == 'APIRouter':
                        if node.targets and hasattr(node.targets[0], 'id'):
                            return node.targets[0].id
                            
        # Default to 'router' if not found
        return 'router'
        
    def _extract_endpoint_info(self, node: ast.FunctionDef, 
                             router_name: str, content: str) -> Optional[Dict[str, Any]]:
        """Extract endpoint information from function"""
        # Check if function has router decorator
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                if (hasattr(decorator.func.value, 'id') and 
                    decorator.func.value.id == router_name):
                    
                    method = decorator.func.attr.upper()
                    if method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                        # Extract path
                        path = None
                        if decorator.args and isinstance(decorator.args[0], ast.Constant):
                            path = decorator.args[0].value
                            
                        if not path:
                            continue
                            
                        # Extract function details
                        endpoint_info = {
                            'name': node.name,
                            'method': method,
                            'path': path,
                            'parameters': self._extract_parameters(node),
                            'path_params': self._extract_path_params(path),
                            'query_params': [],
                            'body_params': [],
                            'auth_required': False,
                            'file_upload': False,
                            'response_model': None,
                            'status_code': 200,
                            'tags': [],
                            'description': ast.get_docstring(node) or ''
                        }
                        
                        # Analyze function parameters
                        self._analyze_function_params(node, endpoint_info)
                        
                        # Extract decorator options
                        self._extract_decorator_options(decorator, endpoint_info)
                        
                        return endpoint_info
                        
        return None
        
    def _extract_parameters(self, node: ast.FunctionDef) -> List[Dict[str, Any]]:
        """Extract all function parameters"""
        params = []
        
        for arg in node.args.args:
            param_info = {
                'name': arg.arg,
                'type': None,
                'default': None,
                'annotation': None
            }
            
            # Get type annotation
            if arg.annotation:
                param_info['annotation'] = self._get_annotation_string(arg.annotation)
                param_info['type'] = self._determine_param_type(arg.annotation)
                
            params.append(param_info)
            
        return params
        
    def _extract_path_params(self, path: str) -> List[str]:
        """Extract path parameters from endpoint path"""
        return re.findall(r'\{(\w+)\}', path)
        
    def _analyze_function_params(self, node: ast.FunctionDef, 
                               endpoint_info: Dict[str, Any]) -> None:
        """Analyze function parameters for special types"""
        for i, arg in enumerate(node.args.args):
            if not arg.annotation:
                continue
                
            annotation_str = self._get_annotation_string(arg.annotation)
            
            # Check for auth dependency
            if 'Depends' in annotation_str and 'current_user' in annotation_str:
                endpoint_info['auth_required'] = True
                
            # Check for file upload
            if 'UploadFile' in annotation_str or 'File' in annotation_str:
                endpoint_info['file_upload'] = True
                
            # Check for query params
            if arg.arg not in endpoint_info['path_params'] and not self._is_special_param(annotation_str):
                # Check if it has a default value
                if i < len(node.args.defaults):
                    default_index = i - (len(node.args.args) - len(node.args.defaults))
                    if default_index >= 0:
                        endpoint_info['query_params'].append({
                            'name': arg.arg,
                            'type': annotation_str,
                            'required': False
                        })
                    else:
                        endpoint_info['body_params'].append({
                            'name': arg.arg,
                            'type': annotation_str
                        })
                else:
                    # No default, could be body param
                    if arg.arg not in ['self', 'request', 'response', 'db']:
                        endpoint_info['body_params'].append({
                            'name': arg.arg,
                            'type': annotation_str
                        })
                        
    def _is_special_param(self, annotation: str) -> bool:
        """Check if parameter is a special FastAPI type"""
        special_types = [
            'Request', 'Response', 'Depends', 'Body', 'Query', 
            'Path', 'Header', 'Cookie', 'Form', 'File', 'UploadFile',
            'BackgroundTasks', 'SecurityScopes', 'HTTPConnection',
            'WebSocket', 'WebSocketDisconnect', 'State'
        ]
        return any(special in annotation for special in special_types)
        
    def _get_annotation_string(self, annotation: ast.AST) -> str:
        """Convert annotation AST to string"""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Attribute):
            return f"{self._get_annotation_string(annotation.value)}.{annotation.attr}"
        elif isinstance(annotation, ast.Subscript):
            return f"{self._get_annotation_string(annotation.value)}[{self._get_annotation_string(annotation.slice)}]"
        elif isinstance(annotation, ast.Constant):
            return repr(annotation.value)
        elif isinstance(annotation, ast.Call):
            return self._get_annotation_string(annotation.func)
        else:
            return 'Any'
            
    def _determine_param_type(self, annotation: ast.AST) -> str:
        """Determine parameter type category"""
        annotation_str = self._get_annotation_string(annotation)
        
        if 'int' in annotation_str.lower():
            return 'integer'
        elif 'str' in annotation_str.lower():
            return 'string'
        elif 'bool' in annotation_str.lower():
            return 'boolean'
        elif 'float' in annotation_str.lower():
            return 'float'
        elif 'list' in annotation_str.lower():
            return 'array'
        elif 'dict' in annotation_str.lower():
            return 'object'
        elif 'UploadFile' in annotation_str:
            return 'file'
        else:
            return 'object'
            
    def _extract_decorator_options(self, decorator: ast.Call, 
                                 endpoint_info: Dict[str, Any]) -> None:
        """Extract options from endpoint decorator"""
        # Check keyword arguments
        for keyword in decorator.keywords:
            if keyword.arg == 'response_model' and isinstance(keyword.value, ast.Name):
                endpoint_info['response_model'] = keyword.value.id
            elif keyword.arg == 'status_code' and isinstance(keyword.value, ast.Constant):
                endpoint_info['status_code'] = keyword.value.value
            elif keyword.arg == 'tags' and isinstance(keyword.value, ast.List):
                endpoint_info['tags'] = [
                    elem.value for elem in keyword.value.elts 
                    if isinstance(elem, ast.Constant)
                ]