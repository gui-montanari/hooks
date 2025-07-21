#!/usr/bin/env python3
"""
Hook para proteger a raiz do projeto contra criação de novos arquivos.
Move automaticamente arquivos não permitidos para scripts/temp/.
"""

import json
import os
import sys
import shutil
from pathlib import Path

# Diretório raiz do projeto
PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
TEMP_DIR = SCRIPTS_DIR / "temp"

# Lista de arquivos permitidos na raiz do projeto
ALLOWED_ROOT_FILES = {
    # Arquivos essenciais atuais
    "BACKLOG.md",
    "CHANGELOG.md",
    "README.md",
    "alembic.ini",
    "pyproject.toml",
    "requirements.txt",
    "run.py",
    "setup_db.py",
    "list_api_routes.py",
    "reset_test_conversations_auto.py",
    "docker-compose.dev.yml",
    "docker-compose.homolog.yml",
    "docker-entrypoint.sh",
    "commands.md",
    
    # Arquivos do .gitignore que são permitidos
    ".env",
    ".env.local",
    "Dockerfile",
    
    # Arquivos de configuração do git/github
    ".gitignore",
    ".gitattributes",
    
    # Arquivos de CI/CD
    ".github",
    
    # Token counter (arquivo temporário do Claude)
    ".token_count.json",
}

# Diretórios permitidos na raiz
ALLOWED_ROOT_DIRS = {
    "app",
    "frontend",
    "alembic",
    "scripts",
    "logs",
    "architecture",
    "hooks",  # Pasta de hooks agora na raiz
    ".claude",
    ".git",
    ".github",
    "venv",
    ".venv",
    "__pycache__",
}

def is_root_file(filepath):
    """Verifica se o arquivo está na raiz do projeto."""
    filepath = Path(filepath)
    try:
        relative_path = filepath.relative_to(PROJECT_ROOT)
        # Se tem apenas um componente no caminho, está na raiz
        return len(relative_path.parts) == 1
    except ValueError:
        # Arquivo não está dentro do projeto
        return False

def should_block_file(filepath):
    """Verifica se o arquivo deve ser bloqueado/movido."""
    filepath = Path(filepath)
    
    # Se não está na raiz, não precisa bloquear
    if not is_root_file(filepath):
        return False
    
    filename = filepath.name
    
    # Verifica se é um arquivo permitido
    if filename in ALLOWED_ROOT_FILES:
        return False
    
    # Verifica se é um diretório (não bloqueia criação de diretórios permitidos)
    if filepath.is_dir() and filename in ALLOWED_ROOT_DIRS:
        return False
    
    # Qualquer outro arquivo na raiz deve ser bloqueado
    return True

def move_to_temp(filepath):
    """Move o arquivo para o diretório temporário."""
    filepath = Path(filepath)
    
    # Cria o diretório temp se não existir
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    
    # Define o caminho de destino
    target_path = TEMP_DIR / filepath.name
    
    # Se o arquivo já existe no destino, adiciona um sufixo
    if target_path.exists():
        base = target_path.stem
        ext = target_path.suffix
        counter = 1
        while target_path.exists():
            target_path = TEMP_DIR / f"{base}_{counter}{ext}"
            counter += 1
    
    # Move o arquivo
    try:
        shutil.move(str(filepath), str(target_path))
        return target_path
    except Exception as e:
        print(f"⚠️  Erro ao mover arquivo: {e}")
        return None

def main():
    """Processa hook de criação de arquivo."""
    try:
        hook_data = json.load(sys.stdin)
    except:
        sys.exit(0)
    
    # Verifica se é uma operação de escrita de arquivo
    tool_name = hook_data.get("tool", "")
    if tool_name != "Write":
        return
    
    # Extrai o caminho do arquivo
    file_path = hook_data.get("params", {}).get("file_path", "")
    
    if not file_path:
        return
    
    filepath = Path(file_path)
    
    # Verifica se o arquivo deve ser bloqueado
    if should_block_file(filepath):
        print(f"\n🚫 Arquivo criado na raiz do projeto: {filepath.name}")
        print(f"   A raiz do projeto deve conter apenas arquivos essenciais.")
        
        # Move o arquivo para temp
        new_path = move_to_temp(filepath)
        
        if new_path:
            print(f"📦 Arquivo movido para: {new_path.relative_to(PROJECT_ROOT)}")
            print(f"   Se este arquivo deve ficar na raiz, adicione '{filepath.name}' à lista ALLOWED_ROOT_FILES")
            print(f"   em hooks/root_file_guard.py")
        else:
            print(f"⚠️  Não foi possível mover o arquivo automaticamente.")
            print(f"   Por favor, mova manualmente para um local apropriado.")

if __name__ == "__main__":
    main()