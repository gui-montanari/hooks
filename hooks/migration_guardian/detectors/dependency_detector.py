"""
Dependency Detector
Detects cross-module dependencies in SQLAlchemy models
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Any

from ..utils.logger import logger


class DependencyDetector:
    """Detects dependencies between modules"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.module_tables = self._scan_module_tables()
        
    def analyze_dependencies(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze dependencies for the given changes"""
        dependencies = {
            'cross_module': False,
            'dependencies': [],
            'affected_modules': set(),
            'dependency_graph': {}
        }
        
        if not changes or not changes.get('changes'):
            return dependencies
            
        current_module = changes['module']
        dependencies['affected_modules'].add(current_module)
        
        # Analyze each change for dependencies
        for change in changes['changes']:
            deps = self._analyze_change_dependencies(change, current_module)
            dependencies['dependencies'].extend(deps)
            
            # Update affected modules
            for dep in deps:
                dependencies['affected_modules'].add(dep['to_module'])
                dependencies['cross_module'] = True
                
        # Build dependency graph
        dependencies['dependency_graph'] = self._build_dependency_graph(
            dependencies['dependencies']
        )
        
        # Calculate migration order
        dependencies['migration_order'] = self._calculate_migration_order(
            dependencies['dependency_graph']
        )
        
        return dependencies
        
    def _scan_module_tables(self) -> Dict[str, Dict[str, str]]:
        """Scan all modules to map tables to modules"""
        module_tables = {}
        app_dir = Path("app")
        
        if not app_dir.exists():
            return module_tables
            
        for module_dir in app_dir.iterdir():
            if module_dir.is_dir() and (module_dir / "models").exists():
                module_name = module_dir.name
                module_tables[module_name] = {}
                
                # Scan model files
                for model_file in (module_dir / "models").glob("*.py"):
                    if model_file.name.startswith("__"):
                        continue
                        
                    tables = self._extract_tables_from_file(model_file)
                    for table in tables:
                        module_tables[module_name][table] = model_file.name
                        
        return module_tables
        
    def _extract_tables_from_file(self, file_path: Path) -> List[str]:
        """Extract table names from a model file"""
        tables = []
        
        try:
            content = file_path.read_text()
            
            # Find __tablename__ definitions
            table_pattern = r'__tablename__\s*=\s*["\']([^"\']+)["\']'
            matches = re.findall(table_pattern, content)
            tables.extend(matches)
            
            # Also try to infer from class names if no __tablename__
            class_pattern = r'class\s+(\w+)\s*\([^)]*Base[^)]*\):'
            class_matches = re.findall(class_pattern, content)
            
            for class_name in class_matches:
                # Convert to table name (simple pluralization)
                table_name = self._class_to_table_name(class_name)
                if table_name not in tables:
                    tables.append(table_name)
                    
        except Exception as e:
            logger.error(f"Error extracting tables from {file_path}: {e}")
            
        return tables
        
    def _analyze_change_dependencies(self, change: Dict[str, Any], 
                                   current_module: str) -> List[Dict[str, Any]]:
        """Analyze dependencies for a specific change"""
        dependencies = []
        
        # Check for foreign key dependencies
        if change.get('foreign_key'):
            dep = self._analyze_foreign_key_dependency(
                change['foreign_key'], current_module
            )
            if dep:
                dependencies.append(dep)
                
        # Check for table references in changes
        if change['type'] in ['CREATE_TABLE', 'ADD_COLUMN']:
            for field in change.get('fields', []):
                if field.get('foreign_key'):
                    dep = self._analyze_foreign_key_dependency(
                        field['foreign_key'], current_module
                    )
                    if dep:
                        dependencies.append(dep)
                        
        return dependencies
        
    def _analyze_foreign_key_dependency(self, foreign_key: str, 
                                      current_module: str) -> Optional[Dict[str, Any]]:
        """Analyze a foreign key reference"""
        # Parse foreign key format: "table.column" or "schema.table.column"
        parts = foreign_key.split('.')
        
        if len(parts) >= 2:
            table_name = parts[-2]
            
            # Find which module owns this table
            for module, tables in self.module_tables.items():
                if table_name in tables:
                    if module != current_module:
                        return {
                            'from_module': current_module,
                            'to_module': module,
                            'type': 'foreign_key',
                            'table': table_name,
                            'reference': foreign_key
                        }
                        
        return None
        
    def _build_dependency_graph(self, dependencies: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
        """Build a dependency graph from the list of dependencies"""
        graph = {}
        
        for dep in dependencies:
            from_module = dep['from_module']
            to_module = dep['to_module']
            
            if from_module not in graph:
                graph[from_module] = set()
            graph[from_module].add(to_module)
            
            # Ensure all modules are in the graph
            if to_module not in graph:
                graph[to_module] = set()
                
        return graph
        
    def _calculate_migration_order(self, graph: Dict[str, Set[str]]) -> List[str]:
        """Calculate the order in which migrations should be applied"""
        # Topological sort
        visited = set()
        order = []
        
        def visit(module: str):
            if module in visited:
                return
            visited.add(module)
            
            # Visit dependencies first
            for dep in graph.get(module, set()):
                visit(dep)
                
            order.append(module)
            
        # Visit all modules
        for module in graph:
            visit(module)
            
        return order
        
    def _class_to_table_name(self, class_name: str) -> str:
        """Convert class name to table name"""
        # Simple conversion: CamelCase to snake_case + plural
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', class_name)
        table_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        
        # Simple pluralization
        if not table_name.endswith('s'):
            if table_name.endswith('y'):
                table_name = table_name[:-1] + 'ies'
            else:
                table_name += 's'
                
        return table_name
        
    def get_module_dependencies_report(self) -> Dict[str, Any]:
        """Get a comprehensive report of all module dependencies"""
        report = {
            'modules': {},
            'cross_dependencies': []
        }
        
        # Scan all model files for foreign keys
        app_dir = Path("app")
        
        for module_dir in app_dir.iterdir():
            if module_dir.is_dir() and (module_dir / "models").exists():
                module_name = module_dir.name
                module_info = {
                    'tables': list(self.module_tables.get(module_name, {}).keys()),
                    'depends_on': set(),
                    'depended_by': set()
                }
                
                # Scan for foreign keys
                for model_file in (module_dir / "models").glob("*.py"):
                    if model_file.name.startswith("__"):
                        continue
                        
                    foreign_keys = self._extract_foreign_keys_from_file(model_file)
                    for fk in foreign_keys:
                        dep_module = self._find_module_for_table(fk['table'])
                        if dep_module and dep_module != module_name:
                            module_info['depends_on'].add(dep_module)
                            report['cross_dependencies'].append({
                                'from': module_name,
                                'to': dep_module,
                                'type': 'foreign_key',
                                'details': fk
                            })
                            
                report['modules'][module_name] = module_info
                
        # Update depended_by relationships
        for dep in report['cross_dependencies']:
            if dep['to'] in report['modules']:
                report['modules'][dep['to']]['depended_by'].add(dep['from'])
                
        return report
        
    def _extract_foreign_keys_from_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract foreign key definitions from a file"""
        foreign_keys = []
        
        try:
            content = file_path.read_text()
            
            # Pattern for ForeignKey definitions
            fk_pattern = r'ForeignKey\s*\(\s*["\']([^"\']+)["\']\s*\)'
            matches = re.findall(fk_pattern, content)
            
            for match in matches:
                parts = match.split('.')
                if len(parts) >= 2:
                    foreign_keys.append({
                        'table': parts[-2],
                        'column': parts[-1],
                        'reference': match
                    })
                    
        except Exception as e:
            logger.error(f"Error extracting foreign keys from {file_path}: {e}")
            
        return foreign_keys
        
    def _find_module_for_table(self, table_name: str) -> Optional[str]:
        """Find which module owns a table"""
        for module, tables in self.module_tables.items():
            if table_name in tables:
                return module
        return None