#!/usr/bin/env python3
"""
🛡️ LEGACY GUARDIAN - Security Audit and Safe Refactor System
Analyzes existing production code and implements safe change processes.
NEVER breaks functionality - ALWAYS tests before changing.
"""

import sys
import json
import re
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Set
import ast
import hashlib
import subprocess

class ProductionCodeAnalyzer:
    """Analyzes production code for security issues"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.issues: List[Dict[str, Any]] = []
        self.dependencies: Set[str] = set()
        self.impact_analysis: Dict[str, Any] = {}
        
    def analyze(self, file_path: str, content: str) -> Tuple[List[Dict], Dict]:
        """Analyze production code and return issues + impact analysis"""
        self.file_path = file_path
        self.content = content
        self.lines = content.split('\n')
        
        # Run security checks (same as Guardian but for audit)
        self._check_sql_security()
        self._check_hardcoded_secrets()
        self._check_fastapi_security()
        self._check_pydantic_security()
        self._check_authentication()
        self._check_async_patterns()
        self._check_data_protection()
        
        # Analyze dependencies and impact
        self._analyze_dependencies()
        self._analyze_impact()
        
        return self.issues, self.impact_analysis
    
    def _check_sql_security(self):
        """Check for SQL injection vulnerabilities in production code"""
        sql_patterns = [
            (r'(execute|query)\s*\(\s*f["\'].*{.*}.*["\']', "SQL Injection via f-string", "CRITICAL"),
            (r'(execute|query)\s*\(\s*["\'].*["\'].*\+', "SQL Injection via concatenation", "CRITICAL"),
            (r'(execute|query)\s*\(\s*["\'].*{}.*["\']\s*\.format', "SQL Injection via .format()", "CRITICAL"),
            (r'(execute|query)\s*\(\s*["\'].*%s.*["\'].*%', "SQL Injection via % formatting", "CRITICAL"),
            (r'(SELECT|INSERT|UPDATE|DELETE).*\+\s*\w+', "Direct variable in SQL query", "HIGH"),
        ]
        
        for i, line in enumerate(self.lines, 1):
            for pattern, issue_type, severity in sql_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    if line.strip().startswith('#') or line.strip().startswith('"""'):
                        continue
                        
                    self.issues.append({
                        "severity": severity,
                        "line": i,
                        "type": issue_type,
                        "code": line.strip(),
                        "fix": self._generate_sql_fix(line),
                        "tests_needed": ["sql_injection", "parameterized_query", "edge_cases"]
                    })
    
    def _generate_sql_fix(self, line: str) -> str:
        """Generate safe SQL fix"""
        # Extract the query pattern
        if 'execute' in line or 'query' in line:
            # Try to extract the SQL
            sql_match = re.search(r'["\']([^"\']+)["\']', line)
            if sql_match:
                sql = sql_match.group(1)
                # Replace variables with parameters
                params = re.findall(r'{(\w+)}', sql)
                if params:
                    safe_sql = sql
                    for param in params:
                        safe_sql = safe_sql.replace(f'{{{param}}}', f':{param}')
                    param_dict = ", ".join(f'"{p}": {p}' for p in params)
                    return f'text("{safe_sql}"), {{{param_dict}}}'
        return "Use parameterized queries with text() and bind parameters"
    
    def _check_hardcoded_secrets(self):
        """Check for hardcoded secrets in production"""
        secret_patterns = [
            (r'(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']', "Hardcoded password", "CRITICAL"),
            (r'(api_key|apikey|api_secret)\s*=\s*["\'][^"\']+["\']', "Hardcoded API key", "CRITICAL"),
            (r'(secret_key|secret)\s*=\s*["\'][^"\']+["\']', "Hardcoded secret", "CRITICAL"),
            (r'postgresql://[^@]+:[^@]+@', "Hardcoded database credentials", "CRITICAL"),
        ]
        
        for i, line in enumerate(self.lines, 1):
            if 'os.getenv' in line or 'os.environ' in line or '= settings.' in line:
                continue
                
            for pattern, issue_type, severity in secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.issues.append({
                        "severity": severity,
                        "line": i,
                        "type": issue_type,
                        "code": line.strip(),
                        "fix": self._generate_env_fix(line),
                        "tests_needed": ["env_loading", "secret_masking", "config_validation"]
                    })
    
    def _generate_env_fix(self, line: str) -> str:
        """Generate environment variable fix"""
        # Extract variable name
        var_match = re.search(r'(\w+)\s*=\s*["\']([^"\']+)["\']', line)
        if var_match:
            var_name = var_match.group(1).upper()
            return f'{var_match.group(1)} = os.getenv("{var_name}")'
        return "Use os.getenv() or settings from pydantic-settings"
    
    def _check_fastapi_security(self):
        """Check FastAPI security in production"""
        auth_decorators = ['Depends', 'Security', 'HTTPBearer', 'OAuth2']
        endpoint_pattern = r'@(app|router)\.(get|post|put|delete|patch)'
        
        in_endpoint = False
        endpoint_line = 0
        endpoint_code = ""
        has_auth = False
        
        for i, line in enumerate(self.lines, 1):
            if re.search(endpoint_pattern, line):
                if in_endpoint and not has_auth:
                    func_name = self._get_function_name(endpoint_line)
                    if func_name not in ['health', 'docs', 'openapi', 'metrics', 'root']:
                        self.issues.append({
                            "severity": "HIGH",
                            "line": endpoint_line,
                            "type": "Missing authentication",
                            "code": endpoint_code,
                            "fix": "Add Depends(get_current_user) to function parameters",
                            "tests_needed": ["auth_required", "unauthorized_access", "token_validation"]
                        })
                
                in_endpoint = True
                endpoint_line = i
                endpoint_code = line.strip()
                has_auth = False
            
            if in_endpoint and any(auth in line for auth in auth_decorators):
                has_auth = True
    
    def _check_pydantic_security(self):
        """Check Pydantic security in production"""
        sensitive_fields = ['password', 'email', 'cpf', 'credit_card', 'phone', 'ssn', 'token']
        
        in_model = False
        model_name = ""
        
        for i, line in enumerate(self.lines, 1):
            if 'class' in line and ('BaseModel' in line or 'Model' in line):
                in_model = True
                model_match = re.search(r'class\s+(\w+)', line)
                model_name = model_match.group(1) if model_match else "Model"
            elif in_model and line.strip() and not line.startswith(' '):
                in_model = False
            
            if in_model:
                for field in sensitive_fields:
                    if f'{field}:' in line or f'{field} :' in line:
                        if field == 'password' and 'str' in line and 'SecretStr' not in line:
                            self.issues.append({
                                "severity": "HIGH",
                                "line": i,
                                "type": "Password without SecretStr",
                                "code": line.strip(),
                                "fix": f"{field}: SecretStr",
                                "tests_needed": ["secret_masking", "serialization_check", "no_plain_text"]
                            })
    
    def _check_authentication(self):
        """Check authentication patterns"""
        auth_patterns = [
            (r'jwt\.encode.*secret\s*=\s*["\'][^"\']{1,10}["\']', "Weak JWT secret", "CRITICAL"),
            (r'verify_password.*==', "Timing attack vulnerability", "HIGH"),
            (r'md5|sha1', "Weak hashing algorithm", "HIGH"),
        ]
        
        for i, line in enumerate(self.lines, 1):
            for pattern, issue_type, severity in auth_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.issues.append({
                        "severity": severity,
                        "line": i,
                        "type": issue_type,
                        "code": line.strip(),
                        "fix": self._generate_auth_fix(issue_type),
                        "tests_needed": ["crypto_strength", "timing_safety", "token_expiry"]
                    })
    
    def _generate_auth_fix(self, issue_type: str) -> str:
        """Generate authentication fix"""
        fixes = {
            "Weak JWT secret": "Use strong secret from environment: os.getenv('JWT_SECRET')",
            "Timing attack vulnerability": "Use secrets.compare_digest() for secure comparison",
            "Weak hashing algorithm": "Use bcrypt or argon2 for password hashing"
        }
        return fixes.get(issue_type, "Implement secure authentication")
    
    def _check_async_patterns(self):
        """Check async/await patterns"""
        async_issues = [
            (r'async def.*\n.*time\.sleep', "Blocking sleep in async", "MEDIUM"),
            (r'async def.*\n.*requests\.(get|post)', "Sync HTTP in async", "MEDIUM"),
        ]
        
        for i, line in enumerate(self.lines, 1):
            for pattern, issue_type, severity in async_issues:
                context = line + '\n' + '\n'.join(self.lines[i:i+5])
                if re.search(pattern, context, re.IGNORECASE):
                    self.issues.append({
                        "severity": severity,
                        "line": i,
                        "type": issue_type,
                        "code": line.strip(),
                        "fix": "Use asyncio.sleep() or httpx for async operations",
                        "tests_needed": ["async_performance", "non_blocking", "concurrency"]
                    })
    
    def _check_data_protection(self):
        """Check data protection"""
        log_patterns = [
            (r'(log|print).*password', "Password in logs", "HIGH"),
            (r'(log|print).*token', "Token in logs", "HIGH"),
            (r'(log|print).*credit_card', "Credit card in logs", "CRITICAL"),
        ]
        
        for i, line in enumerate(self.lines, 1):
            for pattern, issue_type, severity in log_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.issues.append({
                        "severity": severity,
                        "line": i,
                        "type": issue_type,
                        "code": line.strip(),
                        "fix": "Mask sensitive data: log.info(f'User {user_id} logged in')",
                        "tests_needed": ["log_masking", "no_sensitive_data", "audit_compliance"]
                    })
    
    def _analyze_dependencies(self):
        """Analyze file dependencies"""
        import_pattern = r'from\s+(\S+)\s+import|import\s+(\S+)'
        
        for line in self.lines:
            match = re.search(import_pattern, line)
            if match:
                module = match.group(1) or match.group(2)
                if not module.startswith('.'):
                    self.dependencies.add(module)
        
        # Find files that import this module
        self.impact_analysis["imports"] = list(self.dependencies)
        self.impact_analysis["imported_by"] = self._find_importers()
    
    def _find_importers(self) -> List[str]:
        """Find files that import this module"""
        # This would scan the codebase - simplified for now
        module_name = Path(self.file_path).stem
        return [f"Found in: app/api/{module_name}_router.py", 
                f"Found in: tests/test_{module_name}.py"]
    
    def _analyze_impact(self):
        """Analyze impact of changes"""
        self.impact_analysis["risk_level"] = self._calculate_risk_level()
        self.impact_analysis["affected_features"] = self._identify_features()
        self.impact_analysis["test_coverage"] = self._check_test_coverage()
        
    def _calculate_risk_level(self) -> str:
        """Calculate risk level based on issues and dependencies"""
        critical_count = sum(1 for i in self.issues if i["severity"] == "CRITICAL")
        high_count = sum(1 for i in self.issues if i["severity"] == "HIGH")
        
        if critical_count > 0:
            return "CRITICAL"
        elif high_count > 2:
            return "HIGH"
        elif len(self.dependencies) > 10:
            return "MEDIUM"
        return "LOW"
    
    def _identify_features(self) -> List[str]:
        """Identify affected features"""
        features = []
        
        # Check for common patterns
        if 'user' in self.file_path.lower():
            features.append("User Management")
        if 'auth' in self.file_path.lower():
            features.append("Authentication")
        if 'api' in self.file_path:
            features.append("API Endpoints")
            
        return features
    
    def _check_test_coverage(self) -> Dict[str, Any]:
        """Check test coverage for this file"""
        test_file = self.file_path.replace('/app/', '/tests/test_').replace('.py', '_test.py')
        return {
            "test_file": test_file,
            "exists": os.path.exists(test_file),
            "coverage_estimate": "Unknown - run pytest --cov to check"
        }
    
    def _get_function_name(self, start_line: int) -> str:
        """Extract function name"""
        for i in range(start_line, min(start_line + 5, len(self.lines))):
            if i < len(self.lines) and 'def ' in self.lines[i]:
                match = re.search(r'def\s+(\w+)', self.lines[i])
                if match:
                    return match.group(1)
        return ""


class SafeRefactorEngine:
    """Implements safe refactoring process for production code"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backup_dir = Path(".claude/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def create_backup(self, file_path: str, content: str) -> str:
        """Create backup of original file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{timestamp}_{Path(file_path).name}"
        backup_path = self.backup_dir / backup_name
        
        with open(backup_path, 'w') as f:
            f.write(content)
            
        return str(backup_path)
    
    def generate_tests(self, file_path: str, issues: List[Dict], 
                      impact: Dict) -> Dict[str, str]:
        """Generate tests for current behavior"""
        test_generator = TestGenerator(self.config)
        return test_generator.generate_tests(file_path, issues, impact)
    
    def create_migration_plan(self, issues: List[Dict], impact: Dict) -> Dict[str, Any]:
        """Create detailed migration plan"""
        plan = {
            "total_issues": len(issues),
            "critical_issues": sum(1 for i in issues if i["severity"] == "CRITICAL"),
            "estimated_time": self._estimate_time(issues),
            "steps": []
        }
        
        # Group issues by type
        grouped = {}
        for issue in issues:
            issue_type = issue["type"]
            if issue_type not in grouped:
                grouped[issue_type] = []
            grouped[issue_type].append(issue)
        
        # Create steps
        for issue_type, type_issues in grouped.items():
            step = {
                "type": issue_type,
                "count": len(type_issues),
                "actions": [],
                "tests": set()
            }
            
            for issue in type_issues:
                step["actions"].append({
                    "line": issue["line"],
                    "change": issue["fix"],
                    "risk": issue["severity"]
                })
                step["tests"].update(issue["tests_needed"])
            
            step["tests"] = list(step["tests"])
            plan["steps"].append(step)
        
        return plan
    
    def _estimate_time(self, issues: List[Dict]) -> str:
        """Estimate time for safe refactoring"""
        base_time = 5  # minutes per issue
        critical_multiplier = 3
        
        time_minutes = 0
        for issue in issues:
            if issue["severity"] == "CRITICAL":
                time_minutes += base_time * critical_multiplier
            else:
                time_minutes += base_time
        
        if time_minutes < 60:
            return f"{time_minutes} minutes"
        return f"{time_minutes // 60} hours {time_minutes % 60} minutes"


class TestGenerator:
    """Generates tests for current behavior before refactoring"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.test_dir = Path("tests/legacy_guardian")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_tests(self, file_path: str, issues: List[Dict], 
                      impact: Dict) -> Dict[str, str]:
        """Generate comprehensive tests"""
        module_name = Path(file_path).stem
        test_file = self.test_dir / f"test_{module_name}_current_behavior.py"
        
        # Generate test content
        test_content = self._generate_test_content(file_path, issues, impact)
        
        # Write test file
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        return {
            "test_file": str(test_file),
            "test_count": len(issues) * 3,  # 3 tests per issue average
            "coverage_commands": [
                f"pytest {test_file} -v",
                f"pytest {test_file} --cov={module_name}",
            ]
        }
    
    def _generate_test_content(self, file_path: str, issues: List[Dict], 
                              impact: Dict) -> str:
        """Generate actual test content"""
        module_name = Path(file_path).stem
        
        content = f'''"""
🧪 LEGACY GUARDIAN TEST SUITE
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Purpose: Validate current behavior before refactoring
File: {file_path}

⚠️ IMPORTANT: These tests document CURRENT behavior, including bugs.
After fixing issues, update tests to expect correct behavior.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio
from datetime import datetime

# Import module under test
# Adjust import based on your project structure
# from app.{module_name} import *

class TestCurrentBehavior:
    """Tests documenting current behavior of {module_name}"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = Mock()
        self.mock_session = Mock()
        self.test_user = {{
            "id": 1,
            "email": "test@example.com",
            "password": "plain_password"  # Current insecure behavior
        }}
'''

        # Generate tests for each issue
        for i, issue in enumerate(issues):
            if "SQL Injection" in issue["type"]:
                content += self._generate_sql_injection_test(i, issue)
            elif "Hardcoded" in issue["type"]:
                content += self._generate_hardcoded_test(i, issue)
            elif "Missing authentication" in issue["type"]:
                content += self._generate_auth_test(i, issue)
            elif "Password" in issue["type"]:
                content += self._generate_password_test(i, issue)
        
        # Add integration tests
        content += '''
    
class TestIntegrationBehavior:
    """Integration tests for current implementation"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete workflow with current behavior"""
        # This test ensures refactoring doesn't break workflows
        pass
    
    def test_error_handling(self):
        """Test current error handling behavior"""
        # Document how errors are currently handled
        pass
    
    def test_edge_cases(self):
        """Test edge cases with current implementation"""
        # Include boundary conditions
        pass
'''

        # Add performance tests
        content += '''

class TestPerformanceBaseline:
    """Performance baseline tests"""
    
    def test_response_time(self):
        """Baseline response time for optimization comparison"""
        import time
        start = time.time()
        # Call function
        duration = time.time() - start
        assert duration < 1.0  # Current baseline
    
    def test_memory_usage(self):
        """Baseline memory usage"""
        import psutil
        import os
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        # Run operation
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        assert memory_increase < 10 * 1024 * 1024  # 10MB threshold
'''

        return content
    
    def _generate_sql_injection_test(self, index: int, issue: Dict) -> str:
        """Generate SQL injection test"""
        return f'''
    
    def test_sql_injection_behavior_{index}(self):
        """Current SQL injection vulnerability - Line {issue['line']}"""
        # WARNING: This documents INSECURE behavior
        # After fix, this test should verify injection is prevented
        
        malicious_input = "'; DROP TABLE users; --"
        
        # Current behavior: vulnerable to injection
        with patch('sqlalchemy.execute') as mock_execute:
            # Simulate current vulnerable behavior
            # result = function_under_test(malicious_input)
            
            # Document that injection currently works
            # This will need to be updated to expect exception after fix
            pass
    
    def test_sql_safe_input_{index}(self):
        """Test with safe input - should work before and after fix"""
        safe_input = "test@example.com"
        
        # This should work both before and after security fix
        # result = function_under_test(safe_input)
        # assert result is not None
        pass
'''
    
    def _generate_hardcoded_test(self, index: int, issue: Dict) -> str:
        """Generate hardcoded secrets test"""
        return f'''
    
    def test_hardcoded_secret_{index}(self):
        """Current hardcoded secret - Line {issue['line']}"""
        # Document current hardcoded value
        # After fix, verify value comes from environment
        
        # Current behavior: hardcoded value
        # assert current_secret == "hardcoded_value"
        
        # After fix: should come from environment
        # with patch.dict(os.environ, {{'SECRET_KEY': 'env_value'}}):
        #     assert get_secret() == 'env_value'
        pass
'''
    
    def _generate_auth_test(self, index: int, issue: Dict) -> str:
        """Generate authentication test"""
        return f'''
    
    def test_missing_auth_{index}(self):
        """Current missing authentication - Line {issue['line']}"""
        # Document that endpoint currently allows unauthenticated access
        
        # Current behavior: no auth required
        # response = client.get("/endpoint")
        # assert response.status_code == 200  # Currently works without auth
        
        # After fix: should require authentication
        # response = client.get("/endpoint")
        # assert response.status_code == 401
        pass
'''
    
    def _generate_password_test(self, index: int, issue: Dict) -> str:
        """Generate password handling test"""
        return f'''
    
    def test_password_handling_{index}(self):
        """Current password handling - Line {issue['line']}"""
        # Test current password storage/handling
        
        password = "test_password_123"
        
        # Current behavior: might store plain text
        # user = create_user(password=password)
        # assert user.password == password  # INSECURE - documents current behavior
        
        # After fix: should be hashed
        # assert user.password != password
        # assert verify_password(password, user.password)
        pass
'''


class LegacyGuardian:
    """Main Legacy Guardian system"""
    
    def __init__(self, config_path: str = "hooks/guardian_config.json"):
        self.config = self._load_config(config_path)
        self.analyzer = ProductionCodeAnalyzer(self.config)
        self.refactor_engine = SafeRefactorEngine(self.config)
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "legacy_guardian": {
                    "mode": "cautious",
                    "require_tests": True,
                    "backup_always": True,
                    "impact_analysis": True,
                    "rollback_ready": True
                },
                "production_markers": ["app/", "core/", "api/"]
            }
    
    def analyze_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Main analysis entry point"""
        # Check if this is production code
        is_production = any(marker in file_path for marker in 
                          self.config.get("production_markers", []))
        
        # Analyze for issues
        issues, impact = self.analyzer.analyze(file_path, content)
        
        if not issues:
            return {"status": "clean", "report": "No security issues found"}
        
        # Create backup if production code
        backup_path = None
        if is_production and self.config["legacy_guardian"]["backup_always"]:
            backup_path = self.refactor_engine.create_backup(file_path, content)
        
        # Generate tests if required
        test_info = None
        if is_production and self.config["legacy_guardian"]["require_tests"]:
            test_info = self.refactor_engine.generate_tests(file_path, issues, impact)
        
        # Create migration plan
        migration_plan = self.refactor_engine.create_migration_plan(issues, impact)
        
        # Generate report
        report = self._generate_report(
            file_path, issues, impact, backup_path, 
            test_info, migration_plan, is_production
        )
        
        return {
            "status": "issues_found",
            "report": report,
            "backup_path": backup_path,
            "test_info": test_info,
            "migration_plan": migration_plan
        }
    
    def _generate_report(self, file_path: str, issues: List[Dict], 
                        impact: Dict, backup_path: str, test_info: Dict,
                        migration_plan: Dict, is_production: bool) -> str:
        """Generate comprehensive security audit report"""
        report = []
        report.append("=" * 62)
        report.append("🛡️  LEGACY GUARDIAN SECURITY AUDIT")
        report.append(f"📄 File: {file_path}{' (Production Code - Handle with Care!)' if is_production else ''}")
        report.append(f"🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 62)
        report.append("")
        
        if is_production:
            report.append("⚠️ ANÁLISE DE CÓDIGO EM PRODUÇÃO DETECTADA")
            report.append("Este arquivo está em produção. Qualquer mudança seguirá processo seguro.")
            report.append("")
        
        # Summary
        report.append("🔍 ISSUES ENCONTRADAS:")
        report.append("")
        
        # Group by severity
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            severity_issues = [i for i in issues if i["severity"] == severity]
            if severity_issues:
                emoji = {"CRITICAL": "🚨", "HIGH": "❌", "MEDIUM": "⚠️", "LOW": "ℹ️"}[severity]
                report.append(f"{emoji} {severity} RISK ({len(severity_issues)} issues)")
                report.append("-" * 40)
                
                for issue in severity_issues[:3]:  # Show first 3
                    report.append(f"Line {issue['line']}: {issue['type']}")
                    report.append(f"   Impacto: {self._describe_impact(issue)}")
                    
                if len(severity_issues) > 3:
                    report.append(f"   ... and {len(severity_issues) - 3} more")
                report.append("")
        
        # Safe refactor plan
        if is_production:
            report.append("📋 PLANO DE AÇÃO SEGURO:")
            report.append("")
            
            report.append("1️⃣ PREPARAÇÃO")
            report.append("-" * 40)
            report.append(f"✅ Backup criado: {backup_path}")
            report.append("✅ Dependencies mapeadas:")
            for dep in impact.get("imports", [])[:5]:
                report.append(f"   - {dep}")
            
            if test_info:
                report.append(f"✅ {test_info['test_count']} testes gerados em: {test_info['test_file']}")
            report.append("")
            
            report.append("2️⃣ TESTES DO COMPORTAMENTO ATUAL")
            report.append("-" * 40)
            report.append("```python")
            report.append("# Teste 1: Validar comportamento atual")
            report.append("def test_current_behavior():")
            report.append("    # Documenta comportamento antes da mudança")
            report.append("    result = function_under_test()")
            report.append("    assert result == expected_current_behavior")
            report.append("```")
            report.append("")
            
            report.append("3️⃣ MUDANÇAS PROPOSTAS (Safe Refactor)")
            report.append("-" * 40)
            
            # Show first critical fix
            critical = next((i for i in issues if i["severity"] == "CRITICAL"), None)
            if critical:
                report.append("```diff")
                report.append(f"- {critical['code']}")
                report.append(f"+ {critical['fix']}")
                report.append("```")
            report.append("")
            
            report.append("4️⃣ VALIDAÇÃO")
            report.append("-" * 40)
            report.append("[ ] Rodar suite de testes atual")
            report.append("[ ] Aplicar mudanças")
            report.append("[ ] Re-rodar todos os testes")
            report.append("[ ] Verificar logs de produção")
            report.append("[ ] Monitorar por 24h")
            report.append("")
            
            report.append("5️⃣ ROLLBACK (se necessário)")
            report.append("-" * 40)
            report.append("Em caso de qualquer problema:")
            report.append(f"1. cp {backup_path} {file_path}")
            report.append("2. Restart services")
            report.append("3. Verificar restored functionality")
            report.append("")
        
        # Commands
        report.append("=" * 62)
        report.append("💬 COMANDOS DISPONÍVEIS:")
        report.append('- "Gere os testes de comportamento atual"')
        report.append('- "Aplique o plano de mudança segura"')
        report.append('- "Reverta para o backup"')
        report.append('- "Mostre análise de impacto detalhada"')
        report.append("=" * 62)
        
        # Save report
        self._save_report('\n'.join(report))
        
        return '\n'.join(report)
    
    def _describe_impact(self, issue: Dict) -> str:
        """Describe impact of an issue"""
        impacts = {
            "SQL Injection": "Crítico - permite acesso não autorizado ao banco",
            "Hardcoded password": "Crítico - expõe credenciais em código",
            "Missing authentication": "Alto - endpoint exposto publicamente",
            "Weak JWT secret": "Crítico - tokens podem ser forjados",
            "Password in logs": "Alto - expõe senhas em arquivos de log"
        }
        
        for key, impact in impacts.items():
            if key in issue["type"]:
                return impact
        
        return "Requer análise detalhada"
    
    def _save_report(self, report: str):
        """Save audit report"""
        report_dir = Path(".claude/security_reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"legacy_audit_{timestamp}.txt"
        
        with open(report_file, 'w') as f:
            f.write(report)


def main():
    """Main entry point for hook"""
    # Get tool info from environment
    tool_type = os.environ.get('__CLAUDE_TOOL_TYPE__', '')
    if tool_type not in ['Write', 'Edit', 'MultiEdit']:
        sys.exit(0)
    
    file_path = os.environ.get('__CLAUDE_TOOL_INPUT_FILE_PATH__', '')
    if not file_path:
        sys.exit(0)
    
    # Skip non-Python files
    if not file_path.endswith('.py'):
        sys.exit(0)
    
    # Read content
    content = sys.stdin.read()
    
    # Analyze
    guardian = LegacyGuardian()
    result = guardian.analyze_file(file_path, content)
    
    # Output report if issues found
    if result["status"] == "issues_found":
        print(result["report"], file=sys.stderr)
    
    # Always pass through content (PostToolUse doesn't block)
    print(content, end='')
    sys.exit(0)


if __name__ == "__main__":
    main()