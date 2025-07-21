#!/usr/bin/env python3
"""
Hook para organizar automaticamente arquivos criados no diretório scripts.
Detecta o tipo de arquivo e o move para o subdiretório apropriado.
"""

import json
import os
import sys
import shutil
from pathlib import Path
import re

# Diretório raiz do projeto
PROJECT_ROOT = Path(__file__).parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# Mapeamento de padrões de arquivo para diretórios
FILE_PATTERNS = {
    "database/queries": [
        r"^create_.*\.sql$",
        r"^check_.*\.sql$",
        r".*_table\.sql$",
        r".*_schema\.sql$"
    ],
    "database/fixes": [
        r"^fix_.*\.sql$",
        r"^URGENT_.*\.sql$",
        r".*_fix\.sql$"
    ],
    "database/migrations": [
        r"^migrate_.*\.sql$",
        r"^migration_.*\.sql$",
        r"^\d{4}_.*\.sql$"  # Migrations numeradas
    ],
    "tests/webhooks": [
        r"^test_.*webhook.*\.py$",
        r"^test_webhook.*\.py$"
    ],
    "tests/integration": [
        r"^test_.*integration.*\.py$",
        r"^test_.*system.*\.py$",
        r"^test_complete.*\.py$"
    ],
    "tests/e2e": [
        r"^test_e2e.*\.py$",
        r"^test_.*flow.*\.py$",
        r"^test_end_to_end.*\.py$"
    ],
    "tests/unit": [
        r"^test_(?!webhook|integration|system|complete|e2e|flow).*\.py$"
    ],
    "monitoring": [
        r"^monitor_.*\.(py|sh)$",
        r"^check_.*status.*\.(py|sh)$",
        r"^analyze_.*\.py$",
        r"^debug_.*\.py$"
    ],
    "docker": [
        r"^docker.*\.(yml|yaml|sh)$",
        r"^.*docker.*\.(sh|py)$",
        r"^Dockerfile.*$"
    ],
    "setup": [
        r"^setup_.*\.py$",
        r"^configure_.*\.py$",
        r"^create_test_.*\.py$",
        r"^update_.*key.*\.py$",
        r"^populate_.*\.py$"
    ],
    "docs": [
        r".*\.md$",
        r".*\.txt$",
        r"^README.*$"
    ],
    "utils": [
        r"^verify_.*\.py$",
        r"^validate_.*\.py$",
        r"^apply_.*\.py$",
        r"^diagnose_.*\.py$"
    ],
    "hooks": [
        r".*_hook\.py$",
        r"^hook_.*\.py$"
    ]
}

def determine_file_category(filename):
    """Determina a categoria do arquivo baseado em padrões de nome."""
    for category, patterns in FILE_PATTERNS.items():
        for pattern in patterns:
            if re.match(pattern, filename, re.IGNORECASE):
                return category
    
    # Categorias padrão por extensão
    ext = Path(filename).suffix.lower()
    if ext == ".sql":
        return "database/queries"
    elif ext == ".py" and filename.startswith("test_"):
        return "tests/unit"
    elif ext in [".md", ".txt"]:
        return "docs"
    elif ext in [".sh", ".py"]:
        return "utils"
    
    return None

def should_organize_file(filepath):
    """Verifica se o arquivo deve ser organizado."""
    # Não organizar arquivos que já estão em subdiretórios
    relative_path = Path(filepath).relative_to(SCRIPTS_DIR)
    if len(relative_path.parts) > 1:
        return False
    
    # Não organizar este próprio hook
    if Path(filepath).name == "file_organizer.py":
        return False
    
    return True

def organize_file(filepath):
    """Move o arquivo para o diretório apropriado."""
    filepath = Path(filepath)
    
    if not filepath.exists():
        return
    
    # Verifica se o arquivo está no diretório scripts
    try:
        relative_path = filepath.relative_to(SCRIPTS_DIR)
    except ValueError:
        # Arquivo não está no diretório scripts
        return
    
    if not should_organize_file(filepath):
        return
    
    filename = filepath.name
    category = determine_file_category(filename)
    
    if category:
        target_dir = SCRIPTS_DIR / category
        target_dir.mkdir(parents=True, exist_ok=True)
        
        target_path = target_dir / filename
        
        # Se o arquivo já existe no destino, adiciona um sufixo
        if target_path.exists():
            base = target_path.stem
            ext = target_path.suffix
            counter = 1
            while target_path.exists():
                target_path = target_dir / f"{base}_{counter}{ext}"
                counter += 1
        
        # Move o arquivo
        shutil.move(str(filepath), str(target_path))
        
        print(f"📁 Arquivo organizado: {filename} → {category}/")
        print(f"   Movido para: {target_path.relative_to(PROJECT_ROOT)}")

def main():
    """Processa hook de criação/modificação de arquivo."""
    try:
        hook_data = json.load(sys.stdin)
    except:
        sys.exit(0)
    
    # Verifica se é uma operação de escrita de arquivo
    tool_name = hook_data.get("tool", "")
    if tool_name not in ["Write", "Edit", "MultiEdit"]:
        return
    
    # Extrai o caminho do arquivo
    file_path = hook_data.get("params", {}).get("file_path", "")
    
    if file_path:
        organize_file(file_path)

if __name__ == "__main__":
    main()