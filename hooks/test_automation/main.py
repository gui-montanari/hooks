"""
Main Test Generator module
Coordinates test generation for different types of code
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .analyzers.endpoint_analyzer import EndpointAnalyzer
from .analyzers.service_analyzer import ServiceAnalyzer
from .analyzers.model_analyzer import ModelAnalyzer
from .generators.endpoint_test_generator import EndpointTestGenerator
from .generators.service_test_generator import ServiceTestGenerator
from .generators.model_test_generator import ModelTestGenerator
from .utils.config import config
from .utils.logger import logger


class TestGenerator:
    """Main test generator coordinating different analyzers and generators"""
    
    def __init__(self):
        self.config = config._config
        
        # Initialize analyzers
        self.endpoint_analyzer = EndpointAnalyzer(self.config)
        self.service_analyzer = ServiceAnalyzer(self.config)
        self.model_analyzer = ModelAnalyzer(self.config)
        
        # Initialize generators
        self.endpoint_generator = EndpointTestGenerator(self.config)
        self.service_generator = ServiceTestGenerator(self.config)
        self.model_generator = ModelTestGenerator(self.config)
        
        # Test directory
        self.test_dir = Path(self.config['test_generator']['test_directory'])
        
    def run(self, hook_data: Dict[str, Any]) -> None:
        """Main entry point for test generation"""
        try:
            # Check if enabled
            if not self.config['test_generator']['enabled']:
                return
                
            # Parse hook data
            tool_name = hook_data.get('tool', '')
            if tool_name not in ['Write', 'Edit', 'MultiEdit']:
                return
                
            # Get file path
            file_path = self._extract_file_path(hook_data)
            if not file_path:
                return
                
            # Check if it's a Python file in app directory
            if not self._should_generate_tests(file_path):
                return
                
            logger.info(f"🧪 Test Generator: Analyzing {file_path}")
            
            # Analyze file content
            content = self._get_file_content(file_path)
            if not content:
                return
                
            # Extract module name
            module_name = self._extract_module_name(file_path)
            
            # Generate tests based on file type
            tests_generated = []
            
            # Check for endpoints
            if self._is_endpoint_file(file_path):
                endpoints = self.endpoint_analyzer.analyze(content, file_path)
                if endpoints:
                    for endpoint in endpoints:
                        test_file = self.endpoint_generator.generate(
                            endpoint, module_name, file_path
                        )
                        if test_file:
                            tests_generated.append(test_file)
                            
            # Check for services
            elif self._is_service_file(file_path):
                services = self.service_analyzer.analyze(content, file_path)
                if services:
                    for service in services:
                        test_file = self.service_generator.generate(
                            service, module_name, file_path
                        )
                        if test_file:
                            tests_generated.append(test_file)
                            
            # Check for models
            elif self._is_model_file(file_path):
                models = self.model_analyzer.analyze(content, file_path)
                if models:
                    for model in models:
                        test_file = self.model_generator.generate(
                            model, module_name, file_path
                        )
                        if test_file:
                            tests_generated.append(test_file)
                            
            # Report results
            if tests_generated:
                self._report_generated_tests(tests_generated)
                
        except Exception as e:
            logger.error(f"Test Generator error: {e}")
            
    def _extract_file_path(self, hook_data: Dict[str, Any]) -> Optional[str]:
        """Extract file path from hook data"""
        params = hook_data.get('params', {})
        return params.get('file_path') or params.get('path')
        
    def _should_generate_tests(self, file_path: str) -> bool:
        """Check if we should generate tests for this file"""
        path = Path(file_path)
        
        # Must be Python file
        if path.suffix != '.py':
            return False
            
        # Must be in app directory
        if not str(path).startswith('app/'):
            return False
            
        # Skip __pycache__ and test files
        if '__pycache__' in str(path) or 'test' in path.name:
            return False
            
        # Skip __init__.py files
        if path.name == '__init__.py':
            return False
            
        return True
        
    def _get_file_content(self, file_path: str) -> Optional[str]:
        """Get file content"""
        try:
            return Path(file_path).read_text()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None
            
    def _extract_module_name(self, file_path: str) -> str:
        """Extract module name from file path"""
        # Pattern: app/{module}/...
        parts = Path(file_path).parts
        if len(parts) >= 2 and parts[0] == 'app':
            return parts[1]
        return 'unknown'
        
    def _is_endpoint_file(self, file_path: str) -> bool:
        """Check if file contains endpoints"""
        path = Path(file_path)
        
        # Common patterns for endpoint files
        endpoint_patterns = [
            r'api/',
            r'routes/',
            r'endpoints/',
            r'routers/',
            r'views/'
        ]
        
        for pattern in endpoint_patterns:
            if pattern in str(path):
                return True
                
        # Also check file name
        endpoint_names = ['api', 'routes', 'endpoints', 'router', 'views']
        return any(name in path.stem for name in endpoint_names)
        
    def _is_service_file(self, file_path: str) -> bool:
        """Check if file contains services"""
        path = Path(file_path)
        
        # Common patterns for service files
        service_patterns = [
            r'services/',
            r'service\.py$',
            r'_service\.py$'
        ]
        
        for pattern in service_patterns:
            if re.search(pattern, str(path)):
                return True
                
        return False
        
    def _is_model_file(self, file_path: str) -> bool:
        """Check if file contains models"""
        path = Path(file_path)
        
        # Common patterns for model files
        model_patterns = [
            r'models/',
            r'model\.py$',
            r'_model\.py$',
            r'schemas/',
            r'schema\.py$'
        ]
        
        for pattern in model_patterns:
            if re.search(pattern, str(path)):
                return True
                
        return False
        
    def _report_generated_tests(self, test_files: List[str]) -> None:
        """Report generated test files"""
        print("\n🧪 TEST GENERATOR REPORT")
        print("=" * 50)
        print(f"✅ Generated {len(test_files)} test file(s):")
        
        for test_file in test_files:
            print(f"   📄 {test_file}")
            
        print("\n💡 Tips:")
        print("   - Review generated tests and add more assertions")
        print("   - Run tests with: Claude, rode os testes automatizados")
        print("   - Check coverage with: Claude, mostre o status dos testes")
        print("=" * 50)