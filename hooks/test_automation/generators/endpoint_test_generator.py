"""
Endpoint Test Generator
Generates test files for FastAPI endpoints
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..templates.endpoint_templates import EndpointTestTemplates
from ..utils.logger import logger


class EndpointTestGenerator:
    """Generates tests for FastAPI endpoints"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.templates = EndpointTestTemplates()
        self.test_dir = Path(config['test_generator']['test_directory'])
        self.test_prefix = config['test_generator']['test_prefix']
        
    def generate(self, endpoint: Dict[str, Any], module: str, 
                source_file: str) -> Optional[str]:
        """Generate test file for endpoint"""
        try:
            # Create test directory
            module_test_dir = self.test_dir / module
            module_test_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate test file name
            test_filename = f"{self.test_prefix}{endpoint['name']}.py"
            test_file_path = module_test_dir / test_filename
            
            # Check if test already exists
            if test_file_path.exists() and not self._should_overwrite(test_file_path):
                logger.info(f"Test file already exists: {test_file_path}")
                return None
                
            # Generate test content
            test_content = self._generate_test_content(endpoint, module, source_file)
            
            # Write test file
            test_file_path.write_text(test_content)
            logger.info(f"Generated test file: {test_file_path}")
            
            return str(test_file_path)
            
        except Exception as e:
            logger.error(f"Error generating test for {endpoint['name']}: {e}")
            return None
            
    def _should_overwrite(self, test_file: Path) -> bool:
        """Check if we should overwrite existing test file"""
        # Check if file has auto-generated marker
        try:
            content = test_file.read_text()
            return 'Auto-generated tests for' in content
        except:
            return False
            
    def _generate_test_content(self, endpoint: Dict[str, Any], 
                             module: str, source_file: str) -> str:
        """Generate complete test file content"""
        # Generate header
        header = self.templates.generate_header(
            endpoint['name'],
            source_file,
            datetime.now()
        )
        
        # Generate imports
        imports = self.templates.generate_imports(endpoint, module)
        
        # Generate test class
        class_name = f"Test{self._to_camel_case(endpoint['name'])}"
        class_def = f'class {class_name}:\n'
        class_def += f'    """Tests for {endpoint["method"]} {endpoint["path"]}"""\n\n'
        
        # Generate test methods
        test_methods = []
        
        # Success test
        test_methods.append(
            self._generate_success_test(endpoint)
        )
        
        # Auth tests if required
        if endpoint['auth_required']:
            test_methods.append(
                self._generate_unauthorized_test(endpoint)
            )
            test_methods.append(
                self._generate_forbidden_test(endpoint)
            )
            
        # Validation tests
        if endpoint['body_params'] or endpoint['query_params']:
            test_methods.append(
                self._generate_validation_test(endpoint)
            )
            
        # Not found test for endpoints with path params
        if endpoint['path_params']:
            test_methods.append(
                self._generate_not_found_test(endpoint)
            )
            
        # File upload test
        if endpoint['file_upload']:
            test_methods.append(
                self._generate_file_upload_test(endpoint)
            )
            
        # Additional edge case tests
        if self.config['test_generator']['generation_rules']['endpoints']['generate_edge_cases']:
            test_methods.extend(
                self._generate_edge_case_tests(endpoint)
            )
            
        # Combine all parts
        content = header + '\n' + imports + '\n\n' + class_def
        content += '\n'.join(test_methods)
        
        # Add TODOs
        content += self._generate_todos(endpoint)
        
        return content
        
    def _generate_success_test(self, endpoint: Dict[str, Any]) -> str:
        """Generate successful request test"""
        method_name = f"test_{endpoint['name']}_success"
        
        # Build fixture list
        fixtures = ['self', 'client: AsyncClient']
        if endpoint['auth_required']:
            fixtures.append('auth_headers: dict')
        if endpoint['path_params']:
            for param in endpoint['path_params']:
                fixtures.append(f'test_{param}: int')
                
        fixture_str = ', '.join(fixtures)
        
        # Build request
        path = endpoint['path']
        for param in endpoint['path_params']:
            path = path.replace(f'{{{param}}}', f'{{test_{param}}}')
            
        request_parts = [f'response = await client.{endpoint["method"].lower()}(']
        request_parts.append(f'            f"{path}"')
        
        if endpoint['body_params']:
            request_parts.append('            json={')
            for param in endpoint['body_params']:
                request_parts.append(f'                "{param["name"]}": "test_value",')
            request_parts.append('            }')
            
        if endpoint['query_params']:
            request_parts.append('            params={')
            for param in endpoint['query_params']:
                request_parts.append(f'                "{param["name"]}": "test_value",')
            request_parts.append('            }')
            
        if endpoint['auth_required']:
            request_parts.append('            headers=auth_headers')
            
        request_parts.append('        )')
        
        test = f"""    async def {method_name}(
        {fixture_str}
    ):
        \"\"\"Test successful {endpoint['name']} request\"\"\""""
        # Arrange
        # TODO: Set up test data
        
        # Act
        {',\\n        '.join(request_parts)}
        
        # Assert
        assert response.status_code == {endpoint['status_code']}
        data = response.json()
        # TODO: Add more specific assertions based on response model
"""
        return test
        
    def _generate_unauthorized_test(self, endpoint: Dict[str, Any]) -> str:
        """Generate unauthorized test"""
        method_name = f"test_{endpoint['name']}_unauthorized"
        
        fixtures = ['self', 'client: AsyncClient']
        if endpoint['path_params']:
            for param in endpoint['path_params']:
                fixtures.append(f'test_{param}: int')
                
        fixture_str = ', '.join(fixtures)
        
        path = endpoint['path']
        for param in endpoint['path_params']:
            path = path.replace(f'{{{param}}}', f'{{test_{param}}}')
            
        test = f"""    async def {method_name}(
        {fixture_str}
    ):
        """Test {endpoint['name']} without authentication"""
        response = await client.{endpoint['method'].lower()}(
            f"{path}"
        )
        
        assert response.status_code == 401
        assert "detail" in response.json()
"""
        return test
        
    def _generate_forbidden_test(self, endpoint: Dict[str, Any]) -> str:
        """Generate forbidden access test"""
        method_name = f"test_{endpoint['name']}_forbidden"
        
        # This is context-specific, so we'll add a TODO
        test = f"""    async def {method_name}(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test {endpoint['name']} with insufficient permissions"""
        # TODO: Implement based on endpoint's permission requirements
        # Example: trying to access another user's resource
        pass
"""
        return test
        
    def _generate_validation_test(self, endpoint: Dict[str, Any]) -> str:
        """Generate validation error test"""
        method_name = f"test_{endpoint['name']}_validation_error"
        
        fixtures = ['self', 'client: AsyncClient']
        if endpoint['auth_required']:
            fixtures.append('auth_headers: dict')
            
        fixture_str = ', '.join(fixtures)
        
        test = f"""    async def {method_name}(
        {fixture_str}
    ):
        """Test {endpoint['name']} with invalid data"""
        invalid_data = {{
            # TODO: Add invalid data based on validation rules
            "invalid_field": "invalid_value"
        }}
        
        response = await client.{endpoint['method'].lower()}(
            "{endpoint['path']}",
            json=invalid_data{',\\n            headers=auth_headers' if endpoint['auth_required'] else ''}
        )
        
        assert response.status_code == 422
        errors = response.json()["detail"]
        assert len(errors) > 0
        # TODO: Verify specific validation errors
"""
        return test
        
    def _generate_not_found_test(self, endpoint: Dict[str, Any]) -> str:
        """Generate not found test for path parameters"""
        method_name = f"test_{endpoint['name']}_not_found"
        
        fixtures = ['self', 'client: AsyncClient']
        if endpoint['auth_required']:
            fixtures.append('auth_headers: dict')
            
        fixture_str = ', '.join(fixtures)
        
        path = endpoint['path']
        for param in endpoint['path_params']:
            path = path.replace(f'{{{param}}}', '99999')  # Non-existent ID
            
        test = f"""    async def {method_name}(
        {fixture_str}
    ):
        """Test {endpoint['name']} with non-existent resource"""
        response = await client.{endpoint['method'].lower()}(
            "{path}"{',\\n            headers=auth_headers' if endpoint['auth_required'] else ''}
        )
        
        assert response.status_code == 404
"""
        return test
        
    def _generate_file_upload_test(self, endpoint: Dict[str, Any]) -> str:
        """Generate file upload test"""
        method_name = f"test_{endpoint['name']}_file_upload"
        
        test = f"""    async def {method_name}(
        self,
        client: AsyncClient,
        auth_headers: dict,
        create_upload_file
    ):
        """Test {endpoint['name']} with file upload"""
        # Arrange
        file = create_upload_file("test.pdf", b"test content")
        
        # Act
        response = await client.{endpoint['method'].lower()}(
            "{endpoint['path']}",
            files={{"file": file}},
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == {endpoint['status_code']}
        # TODO: Add assertions for file handling
"""
        return test
        
    def _generate_edge_case_tests(self, endpoint: Dict[str, Any]) -> List[str]:
        """Generate edge case tests"""
        tests = []
        
        # Add edge cases based on endpoint characteristics
        # This is a placeholder - would need more sophisticated analysis
        
        return tests
        
    def _generate_todos(self, endpoint: Dict[str, Any]) -> str:
        """Generate TODO comments"""
        todos = [
            "",
            "    # TODO: Add tests for:",
        ]
        
        if endpoint['query_params']:
            todos.append("    # - Query parameter combinations")
            
        if endpoint['path_params']:
            todos.append("    # - Edge cases for path parameters")
            
        if 'list' in endpoint['name'] or 'search' in endpoint['name']:
            todos.append("    # - Pagination")
            todos.append("    # - Filtering")
            todos.append("    # - Sorting")
            
        if endpoint['file_upload']:
            todos.append("    # - File size limits")
            todos.append("    # - Invalid file types")
            
        todos.append("    # - Rate limiting")
        todos.append("    # - Concurrent requests")
        
        return '\n'.join(todos) if len(todos) > 2 else ""
        
    def _to_camel_case(self, snake_str: str) -> str:
        """Convert snake_case to CamelCase"""
        components = snake_str.split('_')
        return ''.join(x.title() for x in components)