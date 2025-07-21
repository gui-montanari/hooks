"""
Templates for model test generation
"""

from datetime import datetime
from typing import Dict, Any


class ModelTestTemplates:
    """Templates for generating model tests"""
    
    def generate_header(self, model_name: str, source_file: str, 
                       timestamp: datetime) -> str:
        """Generate file header with metadata"""
        return f'''"""
Auto-generated tests for {model_name} model
Generated at: {timestamp.strftime("%Y-%m-%d %H:%M:%S")}
Source: {source_file}
Coverage target: 80%
"""
'''
    
    def generate_sqlalchemy_imports(self, model: Dict[str, Any], module: str) -> str:
        """Generate imports for SQLAlchemy model tests"""
        imports = [
            "import pytest",
            "from sqlalchemy.ext.asyncio import AsyncSession",
            "from sqlalchemy.exc import IntegrityError",
        ]
        
        # Add model import
        imports.append(f"from app.{module}.models import {model['name']}")
        
        # Add factory imports
        imports.append(f"from tests.factories import {model['name']}Factory")
        
        return '\n'.join(imports)
    
    def generate_pydantic_imports(self, model: Dict[str, Any], module: str) -> str:
        """Generate imports for Pydantic schema tests"""
        imports = [
            "import pytest",
            "from pydantic import ValidationError",
        ]
        
        # Add schema import
        imports.append(f"from app.{module}.schemas import {model['name']}")
        
        return '\n'.join(imports)