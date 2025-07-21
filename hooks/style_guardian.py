#!/usr/bin/env python3
"""
Style Guardian - Comprehensive code quality and style enforcer
Monitors and improves code quality through 10 specialized modules
"""

import ast
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Set
import importlib.util
from collections import defaultdict, Counter
import tokenize
import io

class StyleGuardian:
    """Main Style Guardian class that coordinates all style checks and fixes"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.config = self.load_config()
        self.report = {
            "timestamp": datetime.now().isoformat(),
            "files_analyzed": 0,
            "issues_fixed": 0,
            "suggestions": 0,
            "modules": {}
        }
        
        # Initialize all modules
        self.modules = {
            "import_optimizer": ImportOptimizer(self),
            "type_hint_enforcer": TypeHintEnforcer(self),
            "pattern_enforcer": PatternEnforcer(self),
            "docstring_enforcer": DocstringEnforcer(self),
            "complexity_guard": ComplexityGuard(self),
            "dead_code_detector": DeadCodeDetector(self),
            "naming_consistency": NamingConsistency(self),
            "magic_number_detector": MagicNumberDetector(self),
            "comment_quality": CommentQuality(self),
            "modern_python_converter": ModernPythonConverter(self)
        }
    
    def load_config(self) -> Dict:
        """Load configuration from style_guardian_config.json"""
        config_path = self.project_root / "hooks" / "style_guardian_config.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        return self.get_default_config()
    
    def get_default_config(self) -> Dict:
        """Return default configuration"""
        return {
            "style_guardian": {
                "enabled": True,
                "auto_fix": True,
                "mode": "moderate",
                "rules": {
                    "imports": {
                        "organize": True,
                        "remove_unused": True,
                        "group_order": ["stdlib", "third_party", "local"],
                        "force_absolute": True
                    },
                    "type_hints": {
                        "enforce": True,
                        "require_return_type": True,
                        "disallow_any": False,
                        "infer_types": True
                    },
                    "naming": {
                        "functions": "snake_case",
                        "classes": "PascalCase",
                        "constants": "UPPER_SNAKE_CASE",
                        "private_prefix": "_",
                        "boolean_prefix": ["is_", "has_", "can_", "should_"]
                    },
                    "docstrings": {
                        "enforce": True,
                        "style": "google",
                        "min_function_length": 3,
                        "require_examples": False
                    },
                    "complexity": {
                        "max_cyclomatic": 10,
                        "max_function_lines": 50,
                        "max_indentation": 4,
                        "max_parameters": 5,
                        "max_returns": 3
                    },
                    "modern_python": {
                        "use_f_strings": True,
                        "use_pathlib": True,
                        "use_type_unions": True,
                        "use_walrus": False
                    }
                },
                "ignore_patterns": [
                    "tests/",
                    "migrations/",
                    ".venv/",
                    "*_pb2.py",
                    "__pycache__/",
                    "*.pyc"
                ],
                "reporting": {
                    "save_reports": True,
                    "report_location": ".claude/style_reports/",
                    "include_metrics": True,
                    "track_improvements": True
                }
            }
        }
    
    def should_analyze_file(self, file_path: str) -> bool:
        """Check if file should be analyzed based on ignore patterns"""
        path = Path(file_path)
        
        # Check ignore patterns
        for pattern in self.config["style_guardian"]["ignore_patterns"]:
            if pattern.endswith('/'):
                if pattern in str(path):
                    return False
            elif path.match(pattern):
                return False
        
        return path.suffix == '.py'
    
    def analyze_file(self, file_path: str) -> Tuple[str, Dict]:
        """Analyze a single file and return fixed content and report"""
        if not self.should_analyze_file(file_path):
            return None, {}
        
        self.report["files_analyzed"] += 1
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")
            return None, {}
        
        # Parse AST
        try:
            tree = ast.parse(original_content)
        except SyntaxError as e:
            print(f"❌ Syntax error in {file_path}: {e}")
            return None, {}
        
        # Run all modules
        content = original_content
        file_report = {"modules": {}}
        
        for module_name, module in self.modules.items():
            if self.is_module_enabled(module_name):
                try:
                    new_content, module_report = module.process(file_path, content, tree)
                    if new_content != content:
                        content = new_content
                        # Re-parse AST if content changed
                        try:
                            tree = ast.parse(content)
                        except:
                            # If parsing fails, skip remaining modules
                            break
                    file_report["modules"][module_name] = module_report
                except Exception as e:
                    print(f"⚠️  Error in {module_name}: {e}")
        
        # Calculate improvements
        if content != original_content:
            file_report["improved"] = True
            file_report["changes"] = self.calculate_changes(original_content, content)
        else:
            file_report["improved"] = False
        
        return content, file_report
    
    def is_module_enabled(self, module_name: str) -> bool:
        """Check if a module is enabled in config"""
        # Map module names to config keys
        module_config_map = {
            "import_optimizer": "imports",
            "type_hint_enforcer": "type_hints",
            "pattern_enforcer": "naming",
            "docstring_enforcer": "docstrings",
            "complexity_guard": "complexity",
            "modern_python_converter": "modern_python"
        }
        
        config_key = module_config_map.get(module_name)
        if config_key and config_key in self.config["style_guardian"]["rules"]:
            rule_config = self.config["style_guardian"]["rules"][config_key]
            if isinstance(rule_config, dict):
                return rule_config.get("enabled", True)
        return True
    
    def calculate_changes(self, original: str, fixed: str) -> Dict:
        """Calculate what changed between original and fixed content"""
        original_lines = original.splitlines()
        fixed_lines = fixed.splitlines()
        
        return {
            "lines_changed": sum(1 for i in range(min(len(original_lines), len(fixed_lines))) 
                               if original_lines[i] != fixed_lines[i]),
            "lines_added": max(0, len(fixed_lines) - len(original_lines)),
            "lines_removed": max(0, len(original_lines) - len(fixed_lines))
        }
    
    def save_report(self):
        """Save analysis report"""
        if not self.config["style_guardian"]["reporting"]["save_reports"]:
            return
        
        report_dir = self.project_root / self.config["style_guardian"]["reporting"]["report_location"]
        report_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = report_dir / f"style_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.report, f, indent=2)
        
        # Also create markdown report
        self.create_markdown_report(report_dir)
    
    def create_markdown_report(self, report_dir: Path):
        """Create a markdown version of the report"""
        md_file = report_dir / "latest_report.md"
        
        with open(md_file, 'w') as f:
            f.write("# 🎨 Style Guardian Report\n")
            f.write(f"*Generated: {self.report['timestamp']}*\n\n")
            f.write(f"## 📊 Summary\n")
            f.write(f"- **Files Analyzed**: {self.report['files_analyzed']}\n")
            f.write(f"- **Issues Fixed**: {self.report['issues_fixed']}\n")
            f.write(f"- **Suggestions**: {self.report['suggestions']}\n\n")
            
            # Module summaries
            f.write("## 🔧 Module Activity\n")
            for module_name, module_data in self.report["modules"].items():
                if module_data.get("active"):
                    f.write(f"\n### {module_name.replace('_', ' ').title()}\n")
                    f.write(f"- Fixes: {module_data.get('fixes', 0)}\n")
                    f.write(f"- Suggestions: {module_data.get('suggestions', 0)}\n")


class ImportOptimizer:
    """Module 1: Organizes and optimizes imports"""
    
    def __init__(self, guardian):
        self.guardian = guardian
        self.stdlib_modules = self._get_stdlib_modules()
    
    def _get_stdlib_modules(self) -> Set[str]:
        """Get list of standard library modules"""
        import sys
        return set(sys.stdlib_module_names) if hasattr(sys, 'stdlib_module_names') else {
            'os', 'sys', 'json', 'datetime', 'pathlib', 'typing', 're', 'ast',
            'collections', 'itertools', 'functools', 'math', 'random', 'time',
            'logging', 'argparse', 'subprocess', 'threading', 'multiprocessing'
        }
    
    def process(self, file_path: str, content: str, tree: ast.AST) -> Tuple[str, Dict]:
        """Process imports and return optimized content"""
        report = {"fixes": 0, "suggestions": 0, "active": False}
        
        # Extract all imports
        imports = self._extract_imports(tree)
        if not imports:
            return content, report
        
        report["active"] = True
        
        # Group imports
        grouped = self._group_imports(imports)
        
        # Check for unused imports
        used_names = self._find_used_names(tree)
        unused = self._find_unused_imports(imports, used_names)
        
        if unused and self.guardian.config["style_guardian"]["rules"]["imports"]["remove_unused"]:
            report["fixes"] += len(unused)
            grouped = self._remove_unused_from_groups(grouped, unused)
        
        # Generate new import block
        if self.guardian.config["style_guardian"]["rules"]["imports"]["organize"]:
            new_import_block = self._generate_import_block(grouped)
            new_content = self._replace_imports(content, tree, new_import_block)
            if new_content != content:
                report["fixes"] += 1
                return new_content, report
        
        return content, report
    
    def _extract_imports(self, tree: ast.AST) -> List[ast.stmt]:
        """Extract all import statements from AST"""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(node)
        return imports
    
    def _group_imports(self, imports: List[ast.stmt]) -> Dict[str, List[str]]:
        """Group imports by category"""
        groups = {
            "stdlib": [],
            "third_party": [],
            "local": []
        }
        
        for imp in imports:
            if isinstance(imp, ast.Import):
                for alias in imp.names:
                    module = alias.name.split('.')[0]
                    import_str = f"import {alias.name}"
                    if alias.asname:
                        import_str += f" as {alias.asname}"
                    
                    if module in self.stdlib_modules:
                        groups["stdlib"].append(import_str)
                    elif module.startswith('app') or module.startswith('.'):
                        groups["local"].append(import_str)
                    else:
                        groups["third_party"].append(import_str)
            
            elif isinstance(imp, ast.ImportFrom):
                module = (imp.module or '').split('.')[0]
                
                items = []
                for alias in imp.names:
                    item = alias.name
                    if alias.asname:
                        item += f" as {alias.asname}"
                    items.append(item)
                
                import_str = f"from {imp.module or '.'} import {', '.join(items)}"
                
                if imp.level > 0 or module.startswith('app') or module.startswith('.'):
                    groups["local"].append(import_str)
                elif module in self.stdlib_modules:
                    groups["stdlib"].append(import_str)
                else:
                    groups["third_party"].append(import_str)
        
        # Sort within groups
        for group in groups.values():
            group.sort()
        
        return groups
    
    def _find_used_names(self, tree: ast.AST) -> Set[str]:
        """Find all names used in the code"""
        used = set()
        
        class NameVisitor(ast.NodeVisitor):
            def visit_Name(self, node):
                used.add(node.id)
            
            def visit_Attribute(self, node):
                if isinstance(node.value, ast.Name):
                    used.add(node.value.id)
                self.generic_visit(node)
        
        # Skip import statements when looking for usage
        for node in tree.body:
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                NameVisitor().visit(node)
        
        return used
    
    def _find_unused_imports(self, imports: List[ast.stmt], used_names: Set[str]) -> Set[str]:
        """Find unused imports"""
        unused = set()
        
        for imp in imports:
            if isinstance(imp, ast.Import):
                for alias in imp.names:
                    name = alias.asname or alias.name.split('.')[0]
                    if name not in used_names:
                        unused.add(alias.name)
            
            elif isinstance(imp, ast.ImportFrom):
                for alias in imp.names:
                    name = alias.asname or alias.name
                    if name not in used_names:
                        unused.add(f"{imp.module}.{alias.name}")
        
        return unused
    
    def _remove_unused_from_groups(self, groups: Dict[str, List[str]], unused: Set[str]) -> Dict[str, List[str]]:
        """Remove unused imports from groups"""
        new_groups = {}
        for group_name, imports in groups.items():
            new_groups[group_name] = [
                imp for imp in imports 
                if not any(u in imp for u in unused)
            ]
        return new_groups
    
    def _generate_import_block(self, groups: Dict[str, List[str]]) -> str:
        """Generate organized import block"""
        blocks = []
        
        order = self.guardian.config["style_guardian"]["rules"]["imports"]["group_order"]
        
        for group in order:
            if group in groups and groups[group]:
                if blocks:  # Add blank line between groups
                    blocks.append("")
                
                # Add comment for group
                if group == "stdlib":
                    blocks.append("# Standard library")
                elif group == "third_party":
                    blocks.append("# Third-party libraries")
                elif group == "local":
                    blocks.append("# Local application")
                
                blocks.extend(groups[group])
        
        return '\n'.join(blocks)
    
    def _replace_imports(self, content: str, tree: ast.AST, new_imports: str) -> str:
        """Replace import section in content"""
        lines = content.splitlines()
        
        # Find import section boundaries
        first_import = None
        last_import = None
        
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if first_import is None:
                    first_import = node.lineno - 1
                last_import = node.end_lineno - 1
            elif first_import is not None:
                # Stop at first non-import
                break
        
        if first_import is None:
            return content
        
        # Replace import section
        new_lines = lines[:first_import] + new_imports.splitlines() + lines[last_import + 1:]
        return '\n'.join(new_lines)


class TypeHintEnforcer:
    """Module 2: Enforces and adds type hints"""
    
    def __init__(self, guardian):
        self.guardian = guardian
        self.type_map = {
            'session': 'Session',
            'db': 'Session',
            'request': 'Request',
            'response': 'Response',
            'user': 'User',
            'email': 'str',
            'password': 'str',
            'token': 'str',
            'id': 'int',
            'user_id': 'int',
            'name': 'str',
            'message': 'str',
            'data': 'Dict[str, Any]',
            'result': 'Any',
            'status': 'str',
            'enabled': 'bool',
            'active': 'bool',
            'created_at': 'datetime',
            'updated_at': 'datetime'
        }
    
    def process(self, file_path: str, content: str, tree: ast.AST) -> Tuple[str, Dict]:
        """Add missing type hints"""
        report = {"fixes": 0, "suggestions": 0, "active": False}
        
        # Find functions without type hints
        functions_without_hints = self._find_functions_without_hints(tree)
        
        if not functions_without_hints:
            return content, report
        
        report["active"] = True
        lines = content.splitlines()
        
        for func in functions_without_hints:
            # Try to infer types
            inferred = self._infer_types(func)
            
            if inferred:
                # Generate new signature
                new_signature = self._generate_typed_signature(func, inferred)
                
                # Replace in content
                old_line = lines[func.lineno - 1]
                indent = len(old_line) - len(old_line.lstrip())
                new_line = ' ' * indent + new_signature
                
                lines[func.lineno - 1] = new_line
                report["fixes"] += 1
            else:
                report["suggestions"] += 1
        
        # Check if we need to add typing imports
        new_content = '\n'.join(lines)
        if report["fixes"] > 0:
            new_content = self._ensure_typing_imports(new_content)
        
        return new_content, report
    
    def _find_functions_without_hints(self, tree: ast.AST) -> List[ast.FunctionDef]:
        """Find functions missing type hints"""
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if missing parameter hints
                missing_param_hints = any(
                    arg.annotation is None 
                    for arg in node.args.args
                    if arg.arg != 'self'
                )
                
                # Check if missing return hint
                missing_return_hint = node.returns is None
                
                if missing_param_hints or missing_return_hint:
                    functions.append(node)
        
        return functions
    
    def _infer_types(self, func: ast.FunctionDef) -> Dict[str, str]:
        """Infer types for function parameters and return"""
        inferred = {}
        
        # Infer from parameter names
        for arg in func.args.args:
            if arg.arg == 'self':
                continue
            
            # Check common patterns
            if arg.arg in self.type_map:
                inferred[arg.arg] = self.type_map[arg.arg]
            elif arg.arg.endswith('_id'):
                inferred[arg.arg] = 'int'
            elif arg.arg.startswith('is_') or arg.arg.startswith('has_'):
                inferred[arg.arg] = 'bool'
        
        # Try to infer return type
        return_type = self._infer_return_type(func)
        if return_type:
            inferred['return'] = return_type
        
        return inferred
    
    def _infer_return_type(self, func: ast.FunctionDef) -> Optional[str]:
        """Infer return type from function body"""
        # Look for return statements
        returns = []
        
        for node in ast.walk(func):
            if isinstance(node, ast.Return):
                if node.value is None:
                    returns.append('None')
                elif isinstance(node.value, ast.Constant):
                    if isinstance(node.value.value, bool):
                        returns.append('bool')
                    elif isinstance(node.value.value, int):
                        returns.append('int')
                    elif isinstance(node.value.value, str):
                        returns.append('str')
                elif isinstance(node.value, ast.Name):
                    # Check if it's a known variable
                    if node.value.id in self.type_map:
                        returns.append(self.type_map[node.value.id])
        
        # If all returns are the same type
        if returns and all(r == returns[0] for r in returns):
            return returns[0]
        
        # If mixed or unknown
        if returns:
            return 'Any'
        
        return 'None'
    
    def _generate_typed_signature(self, func: ast.FunctionDef, inferred: Dict[str, str]) -> str:
        """Generate function signature with type hints"""
        params = []
        
        for arg in func.args.args:
            if arg.arg == 'self':
                params.append('self')
            else:
                type_hint = inferred.get(arg.arg, 'Any')
                params.append(f"{arg.arg}: {type_hint}")
        
        # Handle defaults
        defaults = func.args.defaults
        if defaults:
            default_offset = len(params) - len(defaults)
            for i, default in enumerate(defaults):
                param_idx = default_offset + i
                if '=' not in params[param_idx]:
                    # Add default value
                    default_str = ast.unparse(default) if hasattr(ast, 'unparse') else '...'
                    params[param_idx] += f" = {default_str}"
        
        return_type = inferred.get('return', 'None')
        signature = f"def {func.name}({', '.join(params)}) -> {return_type}:"
        
        return signature
    
    def _ensure_typing_imports(self, content: str) -> str:
        """Ensure necessary typing imports are present"""
        lines = content.splitlines()
        
        # Check what typing imports we need
        needed_imports = set()
        
        for line in lines:
            if 'Dict[' in line:
                needed_imports.add('Dict')
            if 'List[' in line:
                needed_imports.add('List')
            if 'Optional[' in line:
                needed_imports.add('Optional')
            if 'Any' in line and ': Any' in line:
                needed_imports.add('Any')
            if 'Tuple[' in line:
                needed_imports.add('Tuple')
            if 'Set[' in line:
                needed_imports.add('Set')
        
        if not needed_imports:
            return content
        
        # Find where to add import
        import_added = False
        for i, line in enumerate(lines):
            if line.startswith('from typing import'):
                # Update existing import
                existing = set(re.findall(r'\b(\w+)\b', line.split('import')[1]))
                all_imports = sorted(existing | needed_imports)
                lines[i] = f"from typing import {', '.join(all_imports)}"
                import_added = True
                break
        
        if not import_added:
            # Add new import after other imports
            for i, line in enumerate(lines):
                if line.startswith(('import ', 'from ')) or not line.strip():
                    continue
                else:
                    # Insert before this line
                    lines.insert(i, f"from typing import {', '.join(sorted(needed_imports))}")
                    break
        
        return '\n'.join(lines)


class PatternEnforcer:
    """Module 3: Enforces naming patterns and conventions"""
    
    def __init__(self, guardian):
        self.guardian = guardian
    
    def process(self, file_path: str, content: str, tree: ast.AST) -> Tuple[str, Dict]:
        """Enforce naming patterns"""
        report = {"fixes": 0, "suggestions": 0, "active": False}
        
        violations = []
        
        # Check all names in the AST
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not self._is_snake_case(node.name) and not node.name.startswith('_'):
                    violations.append({
                        'type': 'function',
                        'name': node.name,
                        'line': node.lineno,
                        'suggestion': self._to_snake_case(node.name)
                    })
            
            elif isinstance(node, ast.ClassDef):
                if not self._is_pascal_case(node.name):
                    violations.append({
                        'type': 'class',
                        'name': node.name,
                        'line': node.lineno,
                        'suggestion': self._to_pascal_case(node.name)
                    })
            
            elif isinstance(node, ast.Assign):
                # Check for constants (UPPER_SNAKE_CASE)
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        # If assigned at module level and looks like constant
                        if isinstance(node.value, ast.Constant) and target.id.isupper():
                            if not self._is_upper_snake_case(target.id):
                                violations.append({
                                    'type': 'constant',
                                    'name': target.id,
                                    'line': node.lineno,
                                    'suggestion': self._to_upper_snake_case(target.id)
                                })
        
        if violations:
            report["active"] = True
            report["suggestions"] = len(violations)
            
            # Add suggestions to report
            report["violations"] = violations
        
        return content, report
    
    def _is_snake_case(self, name: str) -> bool:
        """Check if name is in snake_case"""
        return bool(re.match(r'^[a-z_][a-z0-9_]*$', name))
    
    def _is_pascal_case(self, name: str) -> bool:
        """Check if name is in PascalCase"""
        return bool(re.match(r'^[A-Z][a-zA-Z0-9]*$', name))
    
    def _is_upper_snake_case(self, name: str) -> bool:
        """Check if name is in UPPER_SNAKE_CASE"""
        return bool(re.match(r'^[A-Z][A-Z0-9_]*$', name))
    
    def _to_snake_case(self, name: str) -> str:
        """Convert to snake_case"""
        # Handle camelCase and PascalCase
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _to_pascal_case(self, name: str) -> str:
        """Convert to PascalCase"""
        parts = name.split('_')
        return ''.join(word.capitalize() for word in parts)
    
    def _to_upper_snake_case(self, name: str) -> str:
        """Convert to UPPER_SNAKE_CASE"""
        return self._to_snake_case(name).upper()


class DocstringEnforcer:
    """Module 4: Enforces and generates docstrings"""
    
    def __init__(self, guardian):
        self.guardian = guardian
    
    def process(self, file_path: str, content: str, tree: ast.AST) -> Tuple[str, Dict]:
        """Add missing docstrings"""
        report = {"fixes": 0, "suggestions": 0, "active": False}
        
        lines = content.splitlines()
        functions_without_docstrings = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                # Check if has docstring
                has_docstring = (
                    node.body and
                    isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, ast.Constant) and
                    isinstance(node.body[0].value.value, str)
                )
                
                if not has_docstring:
                    # Check if function is long enough to require docstring
                    func_lines = node.end_lineno - node.lineno
                    min_lines = self.guardian.config["style_guardian"]["rules"]["docstrings"]["min_function_length"]
                    
                    if func_lines >= min_lines or isinstance(node, ast.ClassDef):
                        functions_without_docstrings.append(node)
        
        if not functions_without_docstrings:
            return content, report
        
        report["active"] = True
        
        # Sort by line number in reverse to avoid offset issues
        functions_without_docstrings.sort(key=lambda x: x.lineno, reverse=True)
        
        for node in functions_without_docstrings:
            docstring = self._generate_docstring(node)
            
            # Find the line after the function definition
            insert_line = node.lineno
            
            # Get indentation
            func_line = lines[node.lineno - 1]
            base_indent = len(func_line) - len(func_line.lstrip())
            docstring_indent = ' ' * (base_indent + 4)
            
            # Insert docstring
            docstring_lines = [
                docstring_indent + '"""' + docstring.splitlines()[0]
            ]
            
            for line in docstring.splitlines()[1:]:
                if line.strip():
                    docstring_lines.append(docstring_indent + line)
                else:
                    docstring_lines.append('')
            
            docstring_lines.append(docstring_indent + '"""')
            
            # Insert after function definition line
            lines.insert(insert_line, '\n'.join(docstring_lines))
            report["fixes"] += 1
        
        return '\n'.join(lines), report
    
    def _generate_docstring(self, node: ast.FunctionDef | ast.ClassDef) -> str:
        """Generate appropriate docstring"""
        if isinstance(node, ast.ClassDef):
            return f"{node.name} class."
        
        # For functions
        parts = [f"{node.name.replace('_', ' ').capitalize()}."]
        
        # Add parameter documentation
        if node.args.args and len(node.args.args) > 1:  # More than just self
            parts.append("\n\nArgs:")
            for arg in node.args.args:
                if arg.arg != 'self':
                    arg_type = "Any"
                    if arg.annotation:
                        arg_type = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else "Any"
                    parts.append(f"\n    {arg.arg}: {arg_type}")
        
        # Add return documentation
        if node.returns:
            return_type = ast.unparse(node.returns) if hasattr(ast, 'unparse') else "Any"
            parts.append(f"\n\nReturns:\n    {return_type}")
        
        return ''.join(parts)


class ComplexityGuard:
    """Module 5: Guards against complex code"""
    
    def __init__(self, guardian):
        self.guardian = guardian
    
    def process(self, file_path: str, content: str, tree: ast.AST) -> Tuple[str, Dict]:
        """Check code complexity"""
        report = {"fixes": 0, "suggestions": 0, "active": False, "complex_functions": []}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_complexity(node)
                
                max_complexity = self.guardian.config["style_guardian"]["rules"]["complexity"]["max_cyclomatic"]
                if complexity > max_complexity:
                    report["active"] = True
                    report["suggestions"] += 1
                    report["complex_functions"].append({
                        "name": node.name,
                        "line": node.lineno,
                        "complexity": complexity,
                        "max_allowed": max_complexity
                    })
        
        return content, report
    
    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # Each and/or adds complexity
                complexity += len(child.values) - 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
        
        return complexity


class DeadCodeDetector:
    """Module 6: Detects and removes dead code"""
    
    def __init__(self, guardian):
        self.guardian = guardian
    
    def process(self, file_path: str, content: str, tree: ast.AST) -> Tuple[str, Dict]:
        """Detect dead code"""
        report = {"fixes": 0, "suggestions": 0, "active": False, "dead_code": []}
        
        # Find all defined functions
        defined_functions = set()
        used_functions = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Skip special methods
                if not node.name.startswith('__'):
                    defined_functions.add(node.name)
            
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    used_functions.add(node.func.id)
        
        # Find unused functions
        unused = defined_functions - used_functions
        
        if unused:
            report["active"] = True
            report["suggestions"] = len(unused)
            report["dead_code"] = list(unused)
        
        return content, report


class NamingConsistency:
    """Module 7: Ensures naming consistency"""
    
    def __init__(self, guardian):
        self.guardian = guardian
    
    def process(self, file_path: str, content: str, tree: ast.AST) -> Tuple[str, Dict]:
        """Check naming consistency"""
        report = {"fixes": 0, "suggestions": 0, "active": False, "issues": []}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check boolean functions
                if self._returns_bool(node) and not any(
                    node.name.startswith(prefix) 
                    for prefix in self.guardian.config["style_guardian"]["rules"]["naming"]["boolean_prefix"]
                ):
                    report["active"] = True
                    report["suggestions"] += 1
                    report["issues"].append({
                        "type": "boolean_function",
                        "name": node.name,
                        "line": node.lineno,
                        "suggestion": f"is_{node.name}"
                    })
        
        return content, report
    
    def _returns_bool(self, node: ast.FunctionDef) -> bool:
        """Check if function returns boolean"""
        if node.returns:
            return_str = ast.unparse(node.returns) if hasattr(ast, 'unparse') else ""
            return return_str == 'bool'
        
        # Check return statements
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and child.value:
                if isinstance(child.value, ast.Constant) and isinstance(child.value.value, bool):
                    return True
        
        return False


class MagicNumberDetector:
    """Module 8: Detects magic numbers and suggests constants"""
    
    def __init__(self, guardian):
        self.guardian = guardian
    
    def process(self, file_path: str, content: str, tree: ast.AST) -> Tuple[str, Dict]:
        """Detect magic numbers"""
        report = {"fixes": 0, "suggestions": 0, "active": False, "magic_numbers": []}
        
        # Common acceptable numbers
        acceptable = {0, 1, 2, 10, 100, 1000, -1}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)) and node.value not in acceptable:
                    # Check if it's already a constant assignment
                    parent = self._get_parent_assign(tree, node)
                    if not parent or not self._is_constant_name(parent):
                        report["active"] = True
                        report["suggestions"] += 1
                        report["magic_numbers"].append({
                            "value": node.value,
                            "line": node.lineno,
                            "suggestion": self._suggest_constant_name(node.value)
                        })
        
        return content, report
    
    def _get_parent_assign(self, tree: ast.AST, target_node: ast.AST) -> Optional[str]:
        """Get parent assignment target if exists"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if node.value == target_node:
                    if node.targets and isinstance(node.targets[0], ast.Name):
                        return node.targets[0].id
        return None
    
    def _is_constant_name(self, name: str) -> bool:
        """Check if name follows constant naming convention"""
        return name.isupper() and '_' in name
    
    def _suggest_constant_name(self, value: float) -> str:
        """Suggest a constant name for a value"""
        if isinstance(value, float):
            return f"DEFAULT_RATE_{str(value).replace('.', '_')}"
        else:
            return f"DEFAULT_VALUE_{value}"


class CommentQuality:
    """Module 9: Ensures comment quality"""
    
    def __init__(self, guardian):
        self.guardian = guardian
    
    def process(self, file_path: str, content: str, tree: ast.AST) -> Tuple[str, Dict]:
        """Check comment quality"""
        report = {"fixes": 0, "suggestions": 0, "active": False, "issues": []}
        
        lines = content.splitlines()
        
        for i, line in enumerate(lines):
            # Find inline comments
            if '#' in line:
                code_part = line.split('#')[0]
                comment_part = line.split('#', 1)[1].strip()
                
                # Check for useless comments
                if self._is_useless_comment(code_part.strip(), comment_part):
                    report["active"] = True
                    report["suggestions"] += 1
                    report["issues"].append({
                        "type": "useless_comment",
                        "line": i + 1,
                        "comment": comment_part
                    })
                
                # Check for old TODOs
                if comment_part.startswith('TODO:'):
                    # Look for date pattern
                    date_match = re.search(r'\((\d{4}-\d{2}-\d{2})\)', comment_part)
                    if date_match:
                        todo_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                        age_days = (datetime.now() - todo_date).days
                        if age_days > 30:
                            report["active"] = True
                            report["suggestions"] += 1
                            report["issues"].append({
                                "type": "old_todo",
                                "line": i + 1,
                                "comment": comment_part,
                                "age_days": age_days
                            })
        
        return content, report
    
    def _is_useless_comment(self, code: str, comment: str) -> bool:
        """Check if comment is useless"""
        # Common useless patterns
        useless_patterns = [
            (r'^\s*(\w+)\s*\+=\s*1\s*$', r'increment|add|plus'),
            (r'^\s*(\w+)\s*-=\s*1\s*$', r'decrement|subtract|minus'),
            (r'^\s*return\s+\w+\s*$', r'return'),
            (r'^\s*import\s+', r'import'),
        ]
        
        comment_lower = comment.lower()
        
        for code_pattern, comment_pattern in useless_patterns:
            if re.match(code_pattern, code) and re.search(comment_pattern, comment_lower):
                return True
        
        return False


class ModernPythonConverter:
    """Module 10: Converts to modern Python idioms"""
    
    def __init__(self, guardian):
        self.guardian = guardian
    
    def process(self, file_path: str, content: str, tree: ast.AST) -> Tuple[str, Dict]:
        """Convert to modern Python"""
        report = {"fixes": 0, "suggestions": 0, "active": False}
        
        lines = content.splitlines()
        new_lines = []
        
        for line in lines:
            new_line = line
            
            # Convert % formatting to f-strings
            if self.guardian.config["style_guardian"]["rules"]["modern_python"]["use_f_strings"]:
                new_line = self._convert_to_fstring(new_line)
                if new_line != line:
                    report["fixes"] += 1
                    report["active"] = True
            
            # Convert os.path to pathlib
            if self.guardian.config["style_guardian"]["rules"]["modern_python"]["use_pathlib"]:
                if 'os.path.join' in new_line:
                    # Simple conversion
                    new_line = self._convert_to_pathlib(new_line)
                    if new_line != line:
                        report["fixes"] += 1
                        report["active"] = True
            
            new_lines.append(new_line)
        
        return '\n'.join(new_lines), report
    
    def _convert_to_fstring(self, line: str) -> str:
        """Convert % formatting and .format() to f-strings"""
        # Simple % formatting
        percent_match = re.search(r'"([^"]*%[sd][^"]*)".*?%\s*\((.*?)\)', line)
        if percent_match:
            template = percent_match.group(1)
            args = percent_match.group(2)
            
            # Simple conversion for single argument
            if '%s' in template and ',' not in args:
                new_template = template.replace('%s', f'{{{args.strip()}}}')
                return line.replace(percent_match.group(0), f'f"{new_template[1:-1]}"')
        
        # .format() method
        format_match = re.search(r'"([^"]*)\{[^}]*\}([^"]*)"\.format\((.*?)\)', line)
        if format_match:
            template = format_match.group(1) + '{}' + format_match.group(2)
            args = format_match.group(3)
            
            # Simple conversion for single argument
            if args and ',' not in args:
                new_template = template.replace('{}', f'{{{args.strip()}}}')
                return line.replace(format_match.group(0), f'f"{new_template[1:-1]}"')
        
        return line
    
    def _convert_to_pathlib(self, line: str) -> str:
        """Convert os.path operations to pathlib"""
        # Simple os.path.join conversion
        if 'os.path.join(' in line:
            # Extract the arguments
            match = re.search(r'os\.path\.join\((.*?)\)', line)
            if match:
                args = match.group(1)
                # Simple case with string literals
                if all(c in args for c in ['"', "'"]):
                    parts = [arg.strip().strip('"').strip("'") for arg in args.split(',')]
                    pathlib_version = ' / '.join(f'"{part}"' for part in parts)
                    return line.replace(match.group(0), f"Path({pathlib_version})")
        
        return line


def main():
    """Main function to run Style Guardian"""
    try:
        # Get environment from hooks
        env = json.loads(os.environ.get('HOOK_RESULT', '{}'))
        
        if not env.get('enabled', True):
            return
        
        # Get modified files
        tool_use = env.get('toolUse', {})
        tool_name = tool_use.get('toolName', '')
        
        if tool_name not in ['Write', 'Edit', 'MultiEdit']:
            return
        
        # Extract file paths
        params = tool_use.get('params', {})
        
        if tool_name == 'MultiEdit':
            file_paths = [params.get('file_path')]
        else:
            file_paths = [params.get('file_path')]
        
        # Initialize guardian
        guardian = StyleGuardian()
        
        # Process each file
        for file_path in file_paths:
            if file_path and guardian.should_analyze_file(file_path):
                print(f"\n🎨 Style Guardian analyzing: {file_path}")
                
                new_content, file_report = guardian.analyze_file(file_path)
                
                if new_content and file_report.get("improved"):
                    # Write improved content back
                    if guardian.config["style_guardian"]["auto_fix"]:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"✅ Applied {guardian.report['issues_fixed']} automatic fixes")
                    else:
                        print(f"💡 Found {guardian.report['issues_fixed']} issues (auto-fix disabled)")
                
                # Update global report
                guardian.report["modules"].update(file_report.get("modules", {}))
        
        # Save report
        guardian.save_report()
        
        # Print summary
        if guardian.report["issues_fixed"] > 0 or guardian.report["suggestions"] > 0:
            print(f"\n📊 Style Guardian Summary:")
            print(f"   - Files analyzed: {guardian.report['files_analyzed']}")
            print(f"   - Issues fixed: {guardian.report['issues_fixed']}")
            print(f"   - Suggestions: {guardian.report['suggestions']}")
    
    except Exception as e:
        print(f"❌ Style Guardian error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()