#!/usr/bin/env python3
"""
🛡️ GUARDIAN - Security Hook for New Code Protection
Protects against security vulnerabilities in new code being written.
Focuses on prevention with minimal interruptions.
"""

import sys
import json
import re
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import ast

class SecurityIssue:
    """Represents a security issue found in code"""
    def __init__(self, severity: str, line: int, message: str, 
                 fix_suggestion: str, learn_more: str = ""):
        self.severity = severity
        self.line = line
        self.message = message
        self.fix_suggestion = fix_suggestion
        self.learn_more = learn_more

class Guardian:
    """Main security analyzer for new code"""
    
    def __init__(self, config_path: str = "hooks/guardian_config.json"):
        self.config = self._load_config(config_path)
        self.issues: List[SecurityIssue] = []
        self.file_path = ""
        self.content = ""
        self.lines: List[str] = []
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Return default config if file doesn't exist
            return {
                "guardian": {
                    "mode": "strict",
                    "block_critical_only": True,
                    "educational_messages": True
                },
                "ignored_paths": ["tests/", "migrations/", ".venv/", "alembic/"]
            }
    
    def analyze_file(self, file_path: str, content: str) -> List[SecurityIssue]:
        """Main analysis method"""
        self.file_path = file_path
        self.content = content
        self.lines = content.split('\n')
        self.issues = []
        
        # Skip if in ignored paths
        if any(ignored in file_path for ignored in self.config.get("ignored_paths", [])):
            return []
        
        # Run all security checks
        self._check_sql_security()
        self._check_hardcoded_secrets()
        self._check_fastapi_security()
        self._check_pydantic_security()
        self._check_authentication()
        self._check_async_patterns()
        self._check_data_protection()
        
        return self.issues
    
    def _check_sql_security(self):
        """Check for SQL injection vulnerabilities"""
        sql_patterns = [
            # F-string SQL
            (r'(execute|query)\s*\(\s*f["\'].*{.*}.*["\']', "SQL Injection via f-string"),
            # String concatenation
            (r'(execute|query)\s*\(\s*["\'].*["\'].*\+', "SQL Injection via concatenation"),
            # .format() SQL
            (r'(execute|query)\s*\(\s*["\'].*{}.*["\']\s*\.format', "SQL Injection via .format()"),
            # % formatting
            (r'(execute|query)\s*\(\s*["\'].*%s.*["\'].*%', "SQL Injection via % formatting"),
            # Direct variable in SQL
            (r'(SELECT|INSERT|UPDATE|DELETE).*\+\s*\w+', "Direct variable in SQL query"),
        ]
        
        for i, line in enumerate(self.lines, 1):
            for pattern, issue_type in sql_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Skip if it's in a comment or string
                    if line.strip().startswith('#') or line.strip().startswith('"""'):
                        continue
                        
                    self.issues.append(SecurityIssue(
                        severity="HIGH",
                        line=i,
                        message=f"{issue_type} detected",
                        fix_suggestion="Use parameterized queries: text('SELECT * FROM users WHERE id = :id')",
                        learn_more="https://owasp.org/www-community/attacks/SQL_Injection"
                    ))
    
    def _check_hardcoded_secrets(self):
        """Check for hardcoded secrets and credentials"""
        secret_patterns = [
            (r'(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
            (r'(api_key|apikey|api_secret)\s*=\s*["\'][^"\']+["\']', "Hardcoded API key"),
            (r'(secret_key|secret)\s*=\s*["\'][^"\']+["\']', "Hardcoded secret"),
            (r'(token|access_token|refresh_token)\s*=\s*["\'][^"\']+["\']', "Hardcoded token"),
            (r'postgresql://[^@]+:[^@]+@', "Hardcoded database credentials"),
            (r'mysql://[^@]+:[^@]+@', "Hardcoded database credentials"),
            (r'mongodb://[^@]+:[^@]+@', "Hardcoded database credentials"),
        ]
        
        for i, line in enumerate(self.lines, 1):
            # Skip if it's getting from environment
            if 'os.getenv' in line or 'os.environ' in line:
                continue
                
            for pattern, issue_type in secret_patterns:
                if match := re.search(pattern, line, re.IGNORECASE):
                    # Skip if it's a variable assignment from env
                    if '= os.' in line or '= settings.' in line:
                        continue
                        
                    self.issues.append(SecurityIssue(
                        severity="CRITICAL",
                        line=i,
                        message=f"{issue_type} detected",
                        fix_suggestion="Use environment variables: os.getenv('SECRET_KEY')",
                        learn_more="https://12factor.net/config"
                    ))
    
    def _check_fastapi_security(self):
        """Check FastAPI-specific security issues"""
        # Check for endpoints without authentication
        auth_decorators = ['Depends', 'Security', 'HTTPBearer', 'OAuth2']
        endpoint_pattern = r'@(app|router)\.(get|post|put|delete|patch)'
        
        in_endpoint = False
        endpoint_line = 0
        has_auth = False
        
        for i, line in enumerate(self.lines, 1):
            if re.search(endpoint_pattern, line):
                # Check previous endpoint
                if in_endpoint and not has_auth:
                    # Check if it's a public endpoint
                    func_name = self._get_function_name(endpoint_line)
                    if func_name not in ['health', 'docs', 'openapi', 'metrics', 'root']:
                        self.issues.append(SecurityIssue(
                            severity="HIGH",
                            line=endpoint_line,
                            message="Endpoint without authentication",
                            fix_suggestion="Add authentication: Depends(get_current_user)",
                            learn_more="https://fastapi.tiangolo.com/tutorial/security/"
                        ))
                
                in_endpoint = True
                endpoint_line = i
                has_auth = False
            
            if in_endpoint and any(auth in line for auth in auth_decorators):
                has_auth = True
        
        # Check CORS wildcard
        if 'allow_origins=["*"]' in self.content or 'allow_origins = ["*"]' in self.content:
            self.issues.append(SecurityIssue(
                severity="HIGH",
                line=self._find_line('allow_origins=["*"]'),
                message="CORS wildcard origin detected",
                fix_suggestion='Use specific origins: allow_origins=["https://example.com"]',
                learn_more="https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS"
            ))
    
    def _check_pydantic_security(self):
        """Check Pydantic model security"""
        sensitive_fields = ['password', 'email', 'cpf', 'credit_card', 'phone', 'ssn']
        
        in_model = False
        model_line = 0
        
        for i, line in enumerate(self.lines, 1):
            if 'class' in line and ('BaseModel' in line or 'Model' in line):
                in_model = True
                model_line = i
            elif in_model and line.strip() and not line.startswith(' '):
                in_model = False
            
            if in_model:
                for field in sensitive_fields:
                    if f'{field}:' in line or f'{field} :' in line:
                        # Check for proper validation
                        if field == 'password' and 'str' in line and 'SecretStr' not in line:
                            self.issues.append(SecurityIssue(
                                severity="HIGH",
                                line=i,
                                message="Password field without SecretStr",
                                fix_suggestion="Use SecretStr for passwords: password: SecretStr",
                                learn_more="https://docs.pydantic.dev/latest/usage/types/secrets/"
                            ))
                        elif field == 'email' and 'str' in line and 'EmailStr' not in line:
                            self.issues.append(SecurityIssue(
                                severity="MEDIUM",
                                line=i,
                                message="Email field without EmailStr validation",
                                fix_suggestion="Use EmailStr for email validation: email: EmailStr",
                                learn_more="https://docs.pydantic.dev/latest/usage/types/string/"
                            ))
    
    def _check_authentication(self):
        """Check authentication and authorization issues"""
        # Check JWT configuration
        jwt_patterns = [
            (r'jwt\.encode.*algorithm\s*=\s*["\']HS256["\'].*secret\s*=\s*["\'][^"\']{1,10}["\']', 
             "Weak JWT secret key"),
            (r'verify_password.*==', "Timing attack vulnerability in password comparison"),
            (r'md5|sha1', "Weak hashing algorithm"),
        ]
        
        for i, line in enumerate(self.lines, 1):
            for pattern, issue_type in jwt_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    if 'md5' in line.lower() or 'sha1' in line.lower():
                        self.issues.append(SecurityIssue(
                            severity="HIGH",
                            line=i,
                            message=f"{issue_type} detected",
                            fix_suggestion="Use bcrypt or argon2 for password hashing",
                            learn_more="https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html"
                        ))
                    else:
                        self.issues.append(SecurityIssue(
                            severity="HIGH",
                            line=i,
                            message=f"{issue_type} detected",
                            fix_suggestion="Use strong secrets and secure comparison",
                            learn_more="https://owasp.org/www-project-cheat-sheets/"
                        ))
    
    def _check_async_patterns(self):
        """Check for async/await issues"""
        async_issues = [
            (r'async def.*\n.*time\.sleep', "Blocking sleep in async function"),
            (r'async def.*\n.*requests\.(get|post|put|delete)', "Sync HTTP call in async function"),
            (r'def.*await', "await in non-async function"),
        ]
        
        for i, line in enumerate(self.lines, 1):
            for pattern, issue_type in async_issues:
                if re.search(pattern, line + '\n' + '\n'.join(self.lines[i:i+5]), re.IGNORECASE):
                    self.issues.append(SecurityIssue(
                        severity="MEDIUM",
                        line=i,
                        message=f"{issue_type} detected",
                        fix_suggestion="Use asyncio.sleep() or httpx for async operations",
                        learn_more="https://docs.python.org/3/library/asyncio.html"
                    ))
    
    def _check_data_protection(self):
        """Check data protection issues"""
        # Check for logging sensitive data
        log_patterns = [
            (r'(log|logger|print).*password', "Password in logs"),
            (r'(log|logger|print).*token', "Token in logs"),
            (r'(log|logger|print).*credit_card', "Credit card in logs"),
        ]
        
        for i, line in enumerate(self.lines, 1):
            for pattern, issue_type in log_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.issues.append(SecurityIssue(
                        severity="HIGH",
                        line=i,
                        message=f"{issue_type} detected",
                        fix_suggestion="Mask sensitive data before logging",
                        learn_more="https://owasp.org/www-project-logging-cheat-sheet/"
                    ))
    
    def _find_line(self, text: str) -> int:
        """Find line number containing text"""
        for i, line in enumerate(self.lines, 1):
            if text in line:
                return i
        return 1
    
    def _get_function_name(self, start_line: int) -> str:
        """Extract function name from decorator line"""
        for i in range(start_line, min(start_line + 5, len(self.lines))):
            if 'def ' in self.lines[i]:
                match = re.search(r'def\s+(\w+)', self.lines[i])
                if match:
                    return match.group(1)
        return ""
    
    def generate_report(self, issues: List[SecurityIssue]) -> str:
        """Generate security report"""
        if not issues:
            return ""
        
        # Only block on critical issues
        critical_issues = [i for i in issues if i.severity == "CRITICAL"]
        if self.config.get("guardian", {}).get("block_critical_only", True):
            if not critical_issues:
                return ""  # Don't block, just log
        
        report = []
        report.append("=" * 62)
        report.append("🛡️  GUARDIAN SECURITY CHECK")
        report.append(f"📄 File: {self.file_path}")
        report.append(f"🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 62)
        report.append("")
        
        if critical_issues:
            report.append("🚨 BLOQUEADO: Vulnerabilidades Críticas Detectadas!")
            report.append("")
        
        # Group issues by severity
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            severity_issues = [i for i in issues if i.severity == severity]
            if severity_issues:
                emoji = {"CRITICAL": "🚨", "HIGH": "❌", "MEDIUM": "⚠️", "LOW": "ℹ️"}[severity]
                report.append(f"{emoji} {severity} ({len(severity_issues)} issues)")
                report.append("-" * 40)
                
                for issue in severity_issues:
                    report.append(f"Line {issue.line}: {issue.message}")
                    report.append(f"   ✅ Fix: {issue.fix_suggestion}")
                    if issue.learn_more and self.config.get("guardian", {}).get("educational_messages", True):
                        report.append(f"   📚 Learn more: {issue.learn_more}")
                    report.append("")
        
        report.append("=" * 62)
        
        # Save report
        self._save_report('\n'.join(report))
        
        return '\n'.join(report)
    
    def _save_report(self, report: str):
        """Save report to file"""
        report_dir = Path(".claude/security_reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"guardian_report_{timestamp}.txt"
        
        with open(report_file, 'w') as f:
            f.write(report)


def main():
    """Main entry point for hook"""
    # Get file info from environment
    tool_type = os.environ.get('__CLAUDE_TOOL_TYPE__', '')
    if tool_type not in ['Write', 'Edit', 'MultiEdit']:
        sys.exit(0)
    
    file_path = os.environ.get('__CLAUDE_TOOL_INPUT_FILE_PATH__', '')
    if not file_path:
        sys.exit(0)
    
    # Skip non-Python files
    if not file_path.endswith('.py'):
        sys.exit(0)
    
    # Read content from stdin
    content = sys.stdin.read()
    
    # Analyze
    guardian = Guardian()
    issues = guardian.analyze_file(file_path, content)
    
    if issues:
        # Check if we should block
        critical_issues = [i for i in issues if i.severity == "CRITICAL"]
        if critical_issues:
            report = guardian.generate_report(issues)
            print(report, file=sys.stderr)
            sys.exit(1)  # Block the operation
        else:
            # Just log warnings
            report = guardian.generate_report(issues)
            if report:
                print(report, file=sys.stderr)
    
    # Pass through the content
    print(content, end='')
    sys.exit(0)


if __name__ == "__main__":
    main()