"""
Service Test Generator
Generates test files for service classes and functions
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from ..templates.service_templates import ServiceTestTemplates
from ..utils.logger import logger


class ServiceTestGenerator:
    """Generates tests for services"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.templates = ServiceTestTemplates()
        self.test_dir = Path(config['test_generator']['test_directory'])
        self.test_prefix = config['test_generator']['test_prefix']
        
    def generate(self, service: Dict[str, Any], module: str, 
                source_file: str) -> Optional[str]:
        """Generate test file for service"""
        try:
            # Create test directory
            module_test_dir = self.test_dir / module
            module_test_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate test file name
            test_filename = f"{self.test_prefix}{self._to_snake_case(service['name'])}.py"
            test_file_path = module_test_dir / test_filename
            
            # Check if test already exists
            if test_file_path.exists() and not self._should_overwrite(test_file_path):
                logger.info(f"Test file already exists: {test_file_path}")
                return None
                
            # Generate test content
            test_content = self._generate_test_content(service, module, source_file)
            
            # Write test file
            test_file_path.write_text(test_content)
            logger.info(f"Generated test file: {test_file_path}")
            
            return str(test_file_path)
            
        except Exception as e:
            logger.error(f"Error generating test for {service['name']}: {e}")
            return None
            
    def _should_overwrite(self, test_file: Path) -> bool:
        """Check if we should overwrite existing test file"""
        try:
            content = test_file.read_text()
            return 'Auto-generated tests for' in content
        except:
            return False
            
    def _generate_test_content(self, service: Dict[str, Any], 
                             module: str, source_file: str) -> str:
        """Generate complete test file content"""
        # Generate header
        header = self.templates.generate_header(
            service['name'],
            source_file,
            datetime.now()
        )
        
        # Generate imports
        imports = self.templates.generate_imports(service, module)
        
        # Generate content based on service type
        if service['type'] == 'class':
            content = self._generate_class_tests(service)
        else:
            content = self._generate_function_tests(service)
            
        return header + '\n' + imports + '\n\n' + content
        
    def _generate_class_tests(self, service: Dict[str, Any]) -> str:
        """Generate tests for service class"""
        class_name = f"Test{service['name']}"
        
        content = f'class {class_name}:\n'
        content += f'    """Test suite for {service["name"]}"""\n\n'
        
        # Generate fixture for service instance
        content += self._generate_service_fixture(service)
        
        # Generate tests for each method
        for method in service['methods']:
            content += self._generate_method_test(method, service['name'])
            
            # Generate error case tests
            if method['raises']:
                content += self._generate_error_test(method, service['name'])
                
            # Generate edge case tests
            if self._should_generate_edge_cases(method):
                content += self._generate_edge_cases(method, service['name'])
                
        # Add integration test placeholder
        if self.config['test_generator']['generation_rules']['services']['generate_integration_tests']:
            content += self._generate_integration_test_placeholder(service)
            
        return content
        
    def _generate_function_tests(self, service: Dict[str, Any]) -> str:
        """Generate tests for standalone function"""
        # Similar to method tests but without class context
        content = ""
        
        # Generate main test
        content += self._generate_function_test(service)
        
        # Generate error tests
        if service['raises']:
            content += self._generate_function_error_test(service)
            
        return content
        
    def _generate_service_fixture(self, service: Dict[str, Any]) -> str:
        """Generate pytest fixture for service instance"""
        fixture_name = self._to_snake_case(service['name'])
        
        fixture = f"""    @pytest.fixture
    async def {fixture_name}(self, db: AsyncSession):
        \"\"\"Create {service['name']} instance\"\"\"
"""
        
        # Add dependencies
        if service['dependencies']:
            for dep in service['dependencies']:
                fixture += f"        # TODO: Mock or create {dep['name']}\n"
                
        fixture += f"        return {service['name']}()\n\n"
        
        return fixture
        
    def _generate_method_test(self, method: Dict[str, Any], 
                            service_name: str) -> str:
        """Generate test for service method"""
        test_name = f"test_{method['name']}"
        service_fixture = self._to_snake_case(service_name)
        
        # Build fixture list
        fixtures = ['self', f'{service_fixture}: {service_name}']
        
        # Add common fixtures based on method name
        if 'create' in method['name'] or 'update' in method['name']:
            fixtures.append('db: AsyncSession')
            
        # Add fixtures for parameters
        for param in method['parameters']:
            if param['name'] not in ['self', 'db']:
                # TODO: Smarter fixture detection
                pass
                
        fixture_str = ', '.join(fixtures)
        
        # Generate test body
        test = f"""    {'async ' if method['is_async'] else ''}def {test_name}(
        {fixture_str}
    ):
        \"\"\"Test {method['name']} method\"\"\"
        # Arrange
"""
        
        # Add parameter setup
        for param in method['parameters']:
            if param['name'] not in ['self', 'db']:
                test += f"        {param['name']} = # TODO: Create test {param['name']}\n"
                
        test += f"""        
        # Act
        result = {'await ' if method['is_async'] else ''}{service_fixture}.{method['name']}(
"""
        
        # Add method parameters
        param_names = [p['name'] for p in method['parameters'] if p['name'] not in ['self']]
        if param_names:
            test += '            ' + ', '.join(param_names) + '\n'
            
        test += """        )
        
        # Assert
"""
        
        # Add assertions based on return type
        if method['returns']:
            test += f"        assert result is not None\n"
            test += f"        # TODO: Add assertions based on {method['returns']}\n"
        else:
            test += "        # TODO: Add appropriate assertions\n"
            
        test += "\n"
        
        return test
        
    def _generate_error_test(self, method: Dict[str, Any], 
                           service_name: str) -> str:
        """Generate error case test"""
        test_name = f"test_{method['name']}_error"
        service_fixture = self._to_snake_case(service_name)
        
        test = f"""    async def {test_name}(
        self,
        {service_fixture}: {service_name}
    ):
        \"\"\"Test {method['name']} error handling\"\"\"
"""
        
        for exception in method['raises']:
            test += f"""        # Test {exception}
        with pytest.raises({exception}):
            await {service_fixture}.{method['name']}(
                # TODO: Add parameters that trigger {exception}
            )
"""
        
        test += "\n"
        
        return test
        
    def _generate_edge_cases(self, method: Dict[str, Any], 
                           service_name: str) -> str:
        """Generate edge case tests"""
        # This would need more sophisticated analysis
        # For now, just add placeholders
        
        edge_cases = []
        
        # Check for list/search methods
        if any(keyword in method['name'] for keyword in ['list', 'search', 'find']):
            edge_cases.append('empty_results')
            edge_cases.append('large_dataset')
            
        # Check for create/update methods
        if any(keyword in method['name'] for keyword in ['create', 'update']):
            edge_cases.append('duplicate_data')
            edge_cases.append('concurrent_modification')
            
        if not edge_cases:
            return ""
            
        test = f"""    # Edge case tests for {method['name']}
"""
        
        for case in edge_cases:
            test += f"""    async def test_{method['name']}_{case}(self):
        \"\"\"Test {method['name']} with {case.replace('_', ' ')}\"\"\"
        # TODO: Implement {case} test
        pass
        
"""
        
        return test
        
    def _generate_function_test(self, function: Dict[str, Any]) -> str:
        """Generate test for standalone function"""
        test_name = f"test_{function['name']}"
        
        test = f"""{'async ' if function['is_async'] else ''}def {test_name}():
    \"\"\"Test {function['name']} function\"\"\"
    # Arrange
"""
        
        for param in function['parameters']:
            test += f"    {param['name']} = # TODO: Create test {param['name']}\n"
            
        test += f"""    
    # Act
    result = {'await ' if function['is_async'] else ''}{function['name']}(
"""
        
        param_names = [p['name'] for p in function['parameters']]
        if param_names:
            test += '        ' + ', '.join(param_names) + '\n'
            
        test += """    )
    
    # Assert
"""
        
        if function['returns']:
            test += f"    assert result is not None\n"
            test += f"    # TODO: Add assertions based on {function['returns']}\n"
        else:
            test += "    # TODO: Add appropriate assertions\n"
            
        test += "\n"
        
        return test
        
    def _generate_function_error_test(self, function: Dict[str, Any]) -> str:
        """Generate error test for function"""
        test = ""
        
        for exception in function['raises']:
            test += f"""def test_{function['name']}_raises_{exception.lower()}():
    \"\"\"Test {function['name']} raises {exception}\"\"\"""
    with pytest.raises({exception}):
        {'await ' if function['is_async'] else ''}{function['name']}(
            # TODO: Add parameters that trigger {exception}
        )

"""
        
        return test
        
    def _generate_integration_test_placeholder(self, service: Dict[str, Any]) -> str:
        """Generate integration test placeholder"""
        return f"""    @pytest.mark.integration
    async def test_{self._to_snake_case(service['name'])}_integration(self):
        \"\"\"Integration test for {service['name']}\"\"\"
        # TODO: Implement full workflow test
        pass
"""
        
    def _should_generate_edge_cases(self, method: Dict[str, Any]) -> bool:
        """Determine if edge cases should be generated"""
        edge_case_keywords = [
            'list', 'search', 'find', 'create', 'update', 
            'delete', 'process', 'calculate'
        ]
        return any(keyword in method['name'] for keyword in edge_case_keywords)
        
    def _to_snake_case(self, camel_str: str) -> str:
        """Convert CamelCase to snake_case"""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()