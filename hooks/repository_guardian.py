#!/usr/bin/env python3
"""
🛡️ REPOSITORY GUARDIAN - Proteção contra deleções acidentais
Previne deleções de arquivos críticos e operações destrutivas
Hook Type: PreToolUse
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Set, Tuple

# Arquivos/pastas que NUNCA devem ser deletados
PROTECTED_ITEMS = [
    # Git
    ".git",
    ".github",
    ".gitignore",
    ".gitattributes",
    
    # Environment & Config
    ".env",
    ".env.example",
    ".env.production",
    ".env.development",
    
    # Documentation
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    
    # Python
    "requirements.txt",
    "requirements-dev.txt",
    "setup.py",
    "setup.cfg",
    "pyproject.toml",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
    
    # JavaScript/Node
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    
    # Docker
    "docker-compose.yml",
    "docker-compose.yaml",
    "docker-compose.prod.yml",
    "docker-compose.dev.yml",
    "Dockerfile",
    "Dockerfile.prod",
    "Dockerfile.dev",
    ".dockerignore",
    
    # Database
    "alembic.ini",
    "migrations/",
    "alembic/",
    
    # Core directories
    "app/",
    "src/",
    "core/",
    "api/",
    "models/",
    "services/",
    "repositories/",
    "controllers/",
    "tests/",
    "test/",
    
    # Configuration
    "config/",
    ".vscode/",
    ".idea/",
    
    # CI/CD
    ".circleci/",
    ".travis.yml",
    ".gitlab-ci.yml",
    "azure-pipelines.yml",
    ".jenkins",
    
    # Security
    "hooks/",
    ".claude/",
    "guardian_config.json",
    
    # Certificates and keys (should never be in repo, but if they are...)
    "*.pem",
    "*.key",
    "*.crt",
    "*.p12",
]

# Padrões perigosos de deleção
DANGEROUS_PATTERNS = [
    "*",
    ".",
    "./*",
    "**/*",
    "../*",
    "~/*",
    "/",
]

# Comandos bash perigosos
DANGEROUS_COMMANDS = [
    # Deleção massiva
    ("rm -rf", "Deleta recursivamente sem confirmação"),
    ("rm -fr", "Deleta recursivamente sem confirmação"),
    ("rm -Rf", "Deleta recursivamente sem confirmação"),
    
    # Git perigoso
    ("git clean -fdx", "Remove TODOS os arquivos não rastreados, incluindo .gitignore"),
    ("git clean -ffdx", "Força remoção de todos os arquivos"),
    ("git reset --hard HEAD~", "Perde commits permanentemente"),
    ("git push --force", "Pode destruir histórico remoto"),
    ("git push -f", "Pode destruir histórico remoto"),
    
    # Permissões perigosas
    ("chmod -R 000", "Remove todas as permissões"),
    ("chmod -R 777", "Permissões inseguras para todos"),
    ("chown -R", "Muda proprietário recursivamente"),
    
    # Find destrutivo
    ("find . -delete", "Deleta tudo que encontrar"),
    ("find / -delete", "EXTREMAMENTE perigoso"),
    ("find . -exec rm", "Deleta via find"),
    
    # Disk operations
    ("dd if=/dev/zero", "Pode sobrescrever disco"),
    ("dd of=/", "Escrita direta no sistema"),
    ("mkfs", "Formata partições"),
    
    # Truncate
    ("> /dev/null 2>&1", "Pode esconder erros críticos"),
    ("truncate -s 0", "Esvazia arquivos"),
    
    # System
    ("shutdown", "Desliga o sistema"),
    ("reboot", "Reinicia o sistema"),
    ("systemctl stop", "Para serviços"),
    ("kill -9", "Força término de processos"),
    ("pkill", "Mata processos por nome"),
    ("killall", "Mata todos os processos"),
]


class RepositoryGuardian:
    """Guardião do repositório contra operações destrutivas"""
    
    def __init__(self):
        self.protected_items = set(PROTECTED_ITEMS)
        self.dangerous_patterns = set(DANGEROUS_PATTERNS)
        
    def check_bash_command(self, command: str) -> Tuple[bool, str]:
        """Verifica comandos bash perigosos"""
        command_lower = command.lower().strip()
        
        # Verifica comandos perigosos conhecidos
        for danger_cmd, description in DANGEROUS_COMMANDS:
            if danger_cmd in command_lower:
                # Verifica se afeta itens protegidos
                for protected in self.protected_items:
                    if protected in command:
                        return False, f"""
🚨 OPERAÇÃO EXTREMAMENTE PERIGOSA DETECTADA!

Comando: {command}
Tipo: {description}
Item protegido: {protected}

Este comando poderia DESTRUIR seu repositório!

🛡️ ALTERNATIVAS SEGURAS:
- Use 'git stash' para salvar mudanças temporariamente
- Use 'git clean -fd' (sem x) para limpar apenas untracked files
- Delete arquivos específicos ao invés de usar wildcards
- Faça backup antes de operações destrutivas

Se REALMENTE precisar executar:
1. Faça backup completo primeiro: tar -czf backup.tar.gz .
2. Verifique com 'ls' o que será afetado
3. Use comandos mais específicos e seguros
"""
                
                # Verifica padrões perigosos mesmo sem item protegido específico
                for pattern in self.dangerous_patterns:
                    if pattern in command and pattern != ".":
                        return False, f"""
⚠️ COMANDO PERIGOSO COM WILDCARD!

Comando: {command}
Padrão perigoso: {pattern}

Este comando pode deletar MÚLTIPLOS arquivos ou TODO o repositório!

🛡️ SEJA MAIS ESPECÍFICO:
❌ rm -rf *
✅ rm -rf build/ dist/

❌ find . -delete  
✅ find . -name "*.pyc" -delete

❌ git clean -fdx
✅ git clean -fd

💡 DICA: Use 'ls' ou 'find' primeiro para ver o que será afetado.
"""
                
                # Comando perigoso genérico
                return False, f"""
⚠️ COMANDO POTENCIALMENTE PERIGOSO!

Comando: {command}
Tipo: {description}

🛡️ RECOMENDAÇÕES:
1. Verifique exatamente o que será afetado
2. Considere alternativas mais seguras
3. Faça backup se necessário
4. Use flags mais seguras quando possível

Tem certeza que deseja continuar? Revise o comando cuidadosamente.
"""
        
        return True, ""
    
    def check_file_deletion(self, files: List[str]) -> Tuple[bool, str]:
        """Verifica tentativas de deletar arquivos protegidos"""
        protected_hits = []
        
        for file in files:
            file_path = Path(file)
            
            # Verifica match exato
            if file in self.protected_items:
                protected_hits.append((file, "arquivo/pasta crítico"))
                continue
            
            # Verifica se é subpasta de item protegido
            for protected in self.protected_items:
                if file.startswith(f"{protected}/") or str(file_path).startswith(f"{protected}/"):
                    protected_hits.append((file, f"parte de {protected}"))
                    continue
                
                # Verifica wildcards em nomes protegidos
                if protected.endswith("/") and file.startswith(protected.rstrip("/")):
                    protected_hits.append((file, f"pasta crítica {protected}"))
        
        if protected_hits:
            files_list = "\n".join([f"❌ {f} ({reason})" for f, reason in protected_hits[:10]])
            more_msg = f"\n... e mais {len(protected_hits) - 10} arquivos" if len(protected_hits) > 10 else ""
            
            return False, f"""
🛡️ ARQUIVOS PROTEGIDOS DETECTADOS!

Tentativa de deletar {len(protected_hits)} arquivo(s) crítico(s):

{files_list}{more_msg}

Estes arquivos/pastas são ESSENCIAIS para o funcionamento do projeto.

🔧 ALTERNATIVAS:
- Use 'Edit' para modificar arquivos ao invés de deletar
- Use 'git checkout' para reverter mudanças
- Crie backups antes de grandes mudanças
- Seja específico sobre o que realmente precisa remover

⚠️ Deleção bloqueada por segurança.
"""
        
        return True, ""
    
    def is_mass_deletion(self, files: List[str]) -> Tuple[bool, str]:
        """Detecta tentativas de deleção em massa"""
        total_files = len(files)
        
        # Deleção direta de muitos arquivos
        if total_files > 10:
            return True, f"Tentando deletar {total_files} arquivos de uma vez"
        
        # Verifica se está deletando pastas com muitos arquivos
        total_affected = 0
        large_dirs = []
        
        for file in files:
            if os.path.isdir(file):
                try:
                    file_count = sum(1 for _ in Path(file).rglob("*"))
                    total_affected += file_count
                    
                    if file_count > 20:
                        large_dirs.append((file, file_count))
                except:
                    pass
        
        if total_affected > 50 or large_dirs:
            details = "\n".join([f"📁 {d} ({c} arquivos)" for d, c in large_dirs[:5]])
            return True, f"""
Total de arquivos afetados: {total_affected}

Pastas grandes:
{details}

Isso parece uma deleção em massa!
"""
        
        return False, ""
    
    def analyze_operation(self, data: dict) -> Tuple[bool, str]:
        """Analisa a operação e retorna (permitir, mensagem)"""
        tool = data.get("tool", "")
        
        if tool not in ["Bash", "Delete", "MultiDelete", "Move"]:
            return True, ""
        
        params = data.get("parameters", {})
        
        # Análise de comandos Bash
        if tool == "Bash":
            command = params.get("command", "")
            return self.check_bash_command(command)
        
        # Análise de Delete/MultiDelete
        elif tool in ["Delete", "MultiDelete"]:
            files = params.get("files", [])
            if not files and params.get("file"):
                files = [params.get("file")]
            
            # Verifica arquivos protegidos
            allowed, msg = self.check_file_deletion(files)
            if not allowed:
                return False, msg
            
            # Verifica deleção em massa
            is_mass, mass_msg = self.is_mass_deletion(files)
            if is_mass:
                files_preview = "\n".join([f"- {f}" for f in files[:10]])
                more = f"\n... e mais {len(files) - 10} arquivos" if len(files) > 10 else ""
                
                return False, f"""
🚨 DELEÇÃO EM MASSA DETECTADA!

{mass_msg}

Arquivos marcados para deleção:
{files_preview}{more}

🛡️ PRÁTICAS SEGURAS:
1. Delete em pequenos grupos (max 10 arquivos)
2. Use 'git clean' para arquivos não rastreados
3. Use 'git checkout' para reverter mudanças
4. Revise a lista antes de confirmar

⚠️ Por segurança, esta operação foi bloqueada.
"""
        
        # Análise de Move (pode ser usado para "deletar" movendo para /tmp ou /dev/null)
        elif tool == "Move":
            source = params.get("source", "")
            destination = params.get("destination", "")
            
            dangerous_destinations = ["/tmp", "/dev/null", "/dev/zero", "~/.Trash"]
            
            for protected in self.protected_items:
                if source == protected or source.startswith(f"{protected}/"):
                    for danger in dangerous_destinations:
                        if danger in destination:
                            return False, f"""
🚨 TENTATIVA DE MOVER ARQUIVO PROTEGIDO PARA LIXEIRA!

Origem: {source} (PROTEGIDO)
Destino: {destination}

Isso é equivalente a DELETAR o arquivo!

Use operações seguras ao invés de mover para locais temporários.
"""
        
        return True, ""


def main():
    """Hook principal"""
    try:
        # Lê dados do stdin
        data = json.load(sys.stdin)
        
        # Cria o guardião
        guardian = RepositoryGuardian()
        
        # Analisa a operação
        allowed, message = guardian.analyze_operation(data)
        
        if not allowed:
            # Bloqueia a operação
            print(json.dumps({
                "action": "block",
                "reason": message
            }))
            sys.exit(2)
        
        # Permite a operação
        sys.exit(0)
        
    except json.JSONDecodeError:
        # Input inválido, permite operação por segurança
        sys.exit(0)
    except Exception as e:
        # Em caso de erro, permite operação (fail open)
        # mas loga o erro
        print(f"Repository Guardian Error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()