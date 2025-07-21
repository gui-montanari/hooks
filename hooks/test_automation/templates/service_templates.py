"""
Templates for service test generation
"""

from datetime import datetime
from typing import Dict, Any


class ServiceTestTemplates:
    """Templates for generating service tests"""
    
    def generate_header(self, service_name: str, source_file: str, 
                       timestamp: datetime) -> str:
        """Generate file header with metadata"""
        return f'''"""
Auto-generated tests for {service_name} service
Generated at: {timestamp.strftime("%Y-%m-%d %H:%M:%S")}
Source: {source_file}
"""
'''
    
    def generate_imports(self, service: Dict[str, Any], module: str) -> str:
        """Generate necessary imports"""
        imports = [
            "import pytest",
            "from unittest.mock import Mock, AsyncMock, patch",
            "from sqlalchemy.ext.asyncio import AsyncSession",
        ]
        
        # Add service import
        imports.append(f"from app.{module}.services import {service['name']}")
        
        # Add model imports
        imports.append(f"from app.{module}.models import *")
        
        # Add exception imports if needed
        if service.get('raises') or any(m.get('raises') for m in service.get('methods', [])):
            imports.append("from app.core.exceptions import *")
            
        # Add factory imports
        imports.append("from tests.factories import *")
        
        return '\n'.join(imports)