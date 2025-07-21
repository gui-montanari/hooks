"""
Templates for endpoint test generation
"""

from datetime import datetime
from typing import Dict, Any, List


class EndpointTestTemplates:
    """Templates for generating endpoint tests"""
    
    def generate_header(self, endpoint_name: str, source_file: str, 
                       timestamp: datetime) -> str:
        """Generate file header with metadata"""
        return f'''"""
Auto-generated tests for {endpoint_name} endpoint
Generated at: {timestamp.strftime("%Y-%m-%d %H:%M:%S")}
Source: {source_file}
"""
'''
    
    def generate_imports(self, endpoint: Dict[str, Any], module: str) -> str:
        """Generate necessary imports"""
        imports = [
            "import pytest",
            "from httpx import AsyncClient",
            "from sqlalchemy.ext.asyncio import AsyncSession",
        ]
        
        # Add module imports
        imports.append(f"from app.{module}.models import *")
        
        # Add auth imports if needed
        if endpoint['auth_required']:
            imports.append("from tests.utils.auth import create_test_token, get_auth_headers")
            
        # Add factory imports
        imports.append("from tests.factories import *")
        
        # Add file upload imports
        if endpoint['file_upload']:
            imports.append("from tests.utils.files import create_upload_file")
            
        # Add response model import if specified
        if endpoint.get('response_model'):
            imports.append(f"from app.{module}.schemas import {endpoint['response_model']}")
            
        return '\n'.join(imports)