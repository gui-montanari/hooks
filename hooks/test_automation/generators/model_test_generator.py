"""
Model Test Generator
Generates test files for SQLAlchemy models and Pydantic schemas
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from ..templates.model_templates import ModelTestTemplates
from ..utils.logger import logger


class ModelTestGenerator:
    """Generates tests for models and schemas"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.templates = ModelTestTemplates()
        self.test_dir = Path(config['test_generator']['test_directory'])
        self.test_prefix = config['test_generator']['test_prefix']
        
    def generate(self, model: Dict[str, Any], module: str, 
                source_file: str) -> Optional[str]:
        """Generate test file for model"""
        try:
            # Create test directory
            module_test_dir = self.test_dir / module
            module_test_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate test file name
            test_filename = f"{self.test_prefix}{self._to_snake_case(model['name'])}.py"
            test_file_path = module_test_dir / test_filename
            
            # Check if test already exists
            if test_file_path.exists() and not self._should_overwrite(test_file_path):
                logger.info(f"Test file already exists: {test_file_path}")
                return None
                
            # Generate test content based on model type
            if model['type'] == 'sqlalchemy':
                test_content = self._generate_sqlalchemy_tests(model, module, source_file)
            else:  # pydantic
                test_content = self._generate_pydantic_tests(model, module, source_file)
                
            # Write test file
            test_file_path.write_text(test_content)
            logger.info(f"Generated test file: {test_file_path}")
            
            return str(test_file_path)
            
        except Exception as e:
            logger.error(f"Error generating test for {model['name']}: {e}")
            return None
            
    def _should_overwrite(self, test_file: Path) -> bool:
        """Check if we should overwrite existing test file"""
        try:
            content = test_file.read_text()
            return 'Auto-generated tests for' in content
        except:
            return False
            
    def _generate_sqlalchemy_tests(self, model: Dict[str, Any], 
                                 module: str, source_file: str) -> str:
        """Generate tests for SQLAlchemy model"""
        # Generate header
        header = self.templates.generate_header(
            model['name'],
            source_file,
            datetime.now()
        )
        
        # Generate imports
        imports = self.templates.generate_sqlalchemy_imports(model, module)
        
        # Generate test class
        class_name = f"Test{model['name']}"
        content = f'class {class_name}:\n'
        content += f'    """Test suite for {model["name"]} model"""\n\n'
        
        # Generate CRUD tests
        if self.config['test_generator']['generation_rules']['models']['generate_crud_tests']:
            content += self._generate_crud_tests(model)
            
        # Generate validation tests
        if self.config['test_generator']['generation_rules']['models']['generate_validation_tests']:
            content += self._generate_validation_tests(model)
            
        # Generate relationship tests
        if model['relationships'] and self.config['test_generator']['generation_rules']['models']['generate_relationship_tests']:
            content += self._generate_relationship_tests(model)
            
        # Generate constraint tests
        content += self._generate_constraint_tests(model)
        
        return header + '\n' + imports + '\n\n' + content
        
    def _generate_pydantic_tests(self, model: Dict[str, Any], 
                               module: str, source_file: str) -> str:
        """Generate tests for Pydantic schema"""
        # Generate header
        header = self.templates.generate_header(
            model['name'],
            source_file,
            datetime.now()
        )
        
        # Generate imports
        imports = self.templates.generate_pydantic_imports(model, module)
        
        # Generate test class
        class_name = f"Test{model['name']}"
        content = f'class {class_name}:\n'
        content += f'    """Test suite for {model["name"]} schema"""\n\n'
        
        # Generate validation tests
        content += self._generate_schema_validation_tests(model)
        
        # Generate serialization tests
        content += self._generate_serialization_tests(model)
        
        # Generate validator tests
        if model['validators']:
            content += self._generate_validator_tests(model)
            
        return header + '\n' + imports + '\n\n' + content
        
    def _generate_crud_tests(self, model: Dict[str, Any]) -> str:
        """Generate CRUD operation tests"""
        tests = ""
        
        # Create test
        tests += f"""    async def test_create_{self._to_snake_case(model['name'])}(
        self,
        db: AsyncSession
    ):
        """Test creating a {model['name']}"""
        # Arrange
        {self._to_snake_case(model['name'])}_data = {{
"""
        
        # Add required fields
        for field in model['fields']:
            if field['primary_key']:
                continue
            if not field['nullable'] and not field.get('default'):
                tests += f'            "{field["name"]}": # TODO: Add test value,\n'
                
        tests += f"""        }}
        
        # Act
        {self._to_snake_case(model['name'])} = {model['name']}(**{self._to_snake_case(model['name'])}_data)
        db.add({self._to_snake_case(model['name'])})
        await db.commit()
        await db.refresh({self._to_snake_case(model['name'])})
        
        # Assert
        assert {self._to_snake_case(model['name'])}.id is not None
        # TODO: Add more assertions
        
"""
        
        # Read test
        tests += f"""    async def test_get_{self._to_snake_case(model['name'])}(
        self,
        db: AsyncSession,
        {self._to_snake_case(model['name'])}_factory
    ):
        """Test retrieving a {model['name']}"""
        # Arrange
        {self._to_snake_case(model['name'])} = await {self._to_snake_case(model['name'])}_factory.create()
        
        # Act
        result = await db.get({model['name']}, {self._to_snake_case(model['name'])}.id)
        
        # Assert
        assert result is not None
        assert result.id == {self._to_snake_case(model['name'])}.id
        
"""
        
        # Update test
        tests += f"""    async def test_update_{self._to_snake_case(model['name'])}(
        self,
        db: AsyncSession,
        {self._to_snake_case(model['name'])}_factory
    ):
        """Test updating a {model['name']}"""
        # Arrange
        {self._to_snake_case(model['name'])} = await {self._to_snake_case(model['name'])}_factory.create()
        
        # Act
        # TODO: Update some fields
        await db.commit()
        await db.refresh({self._to_snake_case(model['name'])})
        
        # Assert
        # TODO: Verify updates
        
"""
        
        # Delete test
        tests += f"""    async def test_delete_{self._to_snake_case(model['name'])}(
        self,
        db: AsyncSession,
        {self._to_snake_case(model['name'])}_factory
    ):
        """Test deleting a {model['name']}"""
        # Arrange
        {self._to_snake_case(model['name'])} = await {self._to_snake_case(model['name'])}_factory.create()
        {self._to_snake_case(model['name'])}_id = {self._to_snake_case(model['name'])}.id
        
        # Act
        await db.delete({self._to_snake_case(model['name'])})
        await db.commit()
        
        # Assert
        result = await db.get({model['name']}, {self._to_snake_case(model['name'])}_id)
        assert result is None
        
"""
        
        return tests
        
    def _generate_validation_tests(self, model: Dict[str, Any]) -> str:
        """Generate field validation tests"""
        tests = ""
        
        # Test required fields
        required_fields = [f for f in model['fields'] 
                         if not f['nullable'] and not f.get('default') and not f['primary_key']]
        
        if required_fields:
            tests += f"""    @pytest.mark.parametrize("field", {[f['name'] for f in required_fields]})
    async def test_required_fields(self, db: AsyncSession, field: str):
        """Test that required fields cannot be null"""
        data = {{
            # TODO: Add all required fields except the one being tested
        }}
        data.pop(field, None)
        
        with pytest.raises(Exception):  # TODO: Specify exact exception
            {self._to_snake_case(model['name'])} = {model['name']}(**data)
            db.add({self._to_snake_case(model['name'])})
            await db.commit()
            
"""
        
        # Test unique constraints
        unique_fields = [f for f in model['fields'] if f.get('unique')]
        
        if unique_fields:
            tests += f"""    async def test_unique_constraints(
        self,
        db: AsyncSession,
        {self._to_snake_case(model['name'])}_factory
    ):
        """Test unique field constraints"""
"""
            for field in unique_fields:
                tests += f"""        # Test {field['name']} uniqueness
        {self._to_snake_case(model['name'])}1 = await {self._to_snake_case(model['name'])}_factory.create()
        
        with pytest.raises(IntegrityError):
            {self._to_snake_case(model['name'])}2 = await {self._to_snake_case(model['name'])}_factory.create(
                {field['name']}={self._to_snake_case(model['name'])}1.{field['name']}
            )
            
"""
        
        return tests
        
    def _generate_relationship_tests(self, model: Dict[str, Any]) -> str:
        """Generate relationship tests"""
        tests = ""
        
        for rel in model['relationships']:
            tests += f"""    async def test_{rel['name']}_relationship(
        self,
        db: AsyncSession,
        {self._to_snake_case(model['name'])}_factory
    ):
        """Test {rel['name']} relationship"""
        # TODO: Implement relationship test
        # - Create related objects
        # - Test accessing relationship
        # - Test cascade operations if applicable
        pass
        
"""
        
        return tests
        
    def _generate_constraint_tests(self, model: Dict[str, Any]) -> str:
        """Generate constraint tests"""
        tests = ""
        
        # Foreign key tests
        foreign_keys = [f for f in model['fields'] if f.get('foreign_key')]
        
        if foreign_keys:
            tests += """    async def test_foreign_key_constraints(self, db: AsyncSession):
        """Test foreign key constraints"""
"""
            for fk in foreign_keys:
                tests += f"""        # Test {fk['name']} foreign key
        with pytest.raises(IntegrityError):
            {self._to_snake_case(model['name'])} = {model['name']}(
                {fk['name']}=99999  # Non-existent ID
            )
            db.add({self._to_snake_case(model['name'])})
            await db.commit()
            
"""
        
        return tests
        
    def _generate_schema_validation_tests(self, model: Dict[str, Any]) -> str:
        """Generate Pydantic schema validation tests"""
        tests = ""
        
        # Test valid data
        tests += f"""    def test_valid_{self._to_snake_case(model['name'])}(self):
        """Test creating {model['name']} with valid data"""
        data = {{
"""
        
        for field in model['fields']:
            if field['required']:
                tests += f'            "{field["name"]}": # TODO: Add valid value,\n'
                
        tests += f"""        }}
        
        {self._to_snake_case(model['name'])} = {model['name']}(**data)
        assert {self._to_snake_case(model['name'])}.{model['fields'][0]['name']} == data["{model['fields'][0]['name']}"]
        
"""
        
        # Test invalid data
        tests += f"""    def test_invalid_{self._to_snake_case(model['name'])}(self):
        """Test {model['name']} validation errors"""
        with pytest.raises(ValidationError) as exc_info:
            {model['name']}(
                # TODO: Add invalid data
            )
        
        errors = exc_info.value.errors()
        assert len(errors) > 0
        
"""
        
        # Test optional fields
        optional_fields = [f for f in model['fields'] if not f['required']]
        
        if optional_fields:
            tests += f"""    def test_optional_fields(self):
        """Test {model['name']} with optional fields"""
        minimal_data = {{
            # TODO: Add only required fields
        }}
        
        {self._to_snake_case(model['name'])} = {model['name']}(**minimal_data)
        
        # Verify optional fields have defaults
"""
            for field in optional_fields:
                if field.get('default') is not None:
                    tests += f'        assert {self._to_snake_case(model["name"])}.{field["name"]} == {repr(field["default"])}\n'
                    
        return tests
        
    def _generate_serialization_tests(self, model: Dict[str, Any]) -> str:
        """Generate serialization/deserialization tests"""
        return f"""    def test_serialization(self):
        """Test {model['name']} serialization"""
        {self._to_snake_case(model['name'])} = {model['name']}(
            # TODO: Add test data
        )
        
        # Test dict serialization
        data = {self._to_snake_case(model['name'])}.model_dump()
        assert isinstance(data, dict)
        
        # Test JSON serialization
        json_str = {self._to_snake_case(model['name'])}.model_dump_json()
        assert isinstance(json_str, str)
        
        # Test deserialization
        loaded = {model['name']}.model_validate_json(json_str)
        assert loaded == {self._to_snake_case(model['name'])}
        
"""
        
    def _generate_validator_tests(self, model: Dict[str, Any]) -> str:
        """Generate custom validator tests"""
        tests = ""
        
        for validator in model['validators']:
            tests += f"""    def test_{validator['name']}_validator(self):
        """Test {validator['name']} validator"""
        # TODO: Test validator logic
        # - Test valid inputs
        # - Test invalid inputs that should be rejected
        pass
        
"""
        
        return tests
        
    def _to_snake_case(self, camel_str: str) -> str:
        """Convert CamelCase to snake_case"""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()