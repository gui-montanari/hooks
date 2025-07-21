#!/usr/bin/env python3
"""
Hook para atualizar automaticamente a documentação de arquitetura
quando novos arquivos ou diretórios são criados/modificados.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
import re

# Configurações
PROJECT_ROOT = Path(__file__).parent.parent.parent
ARCHITECTURE_DIR = PROJECT_ROOT / "architecture"
IGNORE_DIRS = {'.git', '__pycache__', 'node_modules', '.pytest_cache', '.venv', 'venv', '.env'}
IGNORE_FILES = {'.pyc', '.pyo', '.pyd', '.so', '.egg', '.egg-info', '.DS_Store'}

# Mapeamento de diretórios para arquivos de documentação
DOC_MAPPING = {
    "app": "app.md",
    "app/aiagent": "app_aiagent.md",
    "app/core": "app_core.md",
    "app/api": "app_api.md",
    "app/auth": "app_auth.md",
    "app/db": "app_db.md",
    "app/domain": "app_domain.md",
    "app/infrastructure": "app_infrastructure.md",
    "app/integrations": "app_integrations.md",
    "frontend": "frontend.md",
    "scripts": "scripts.md",
    "logs": "logs.md",
}

def get_doc_file_for_path(file_path: Path) -> Path:
    """Determina qual arquivo de documentação deve ser atualizado."""
    relative_path = file_path.relative_to(PROJECT_ROOT)
    
    # Verifica cada mapeamento, do mais específico para o mais geral
    for dir_path, doc_file in sorted(DOC_MAPPING.items(), key=lambda x: len(x[0]), reverse=True):
        if str(relative_path).startswith(dir_path):
            return ARCHITECTURE_DIR / doc_file
    
    # Se não encontrar, usa o arquivo app.md como padrão para arquivos dentro de app/
    if str(relative_path).startswith("app/"):
        return ARCHITECTURE_DIR / "app.md"
    
    return None

def update_tree_in_file(doc_file: Path, new_file: Path):
    """Atualiza a árvore de diretórios no arquivo de documentação."""
    if not doc_file.exists():
        print(f"⚠️  Arquivo de documentação não encontrado: {doc_file}")
        return
    
    with open(doc_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Encontra a seção de estrutura
    tree_pattern = r'(## 🌳 Estrutura de Diretórios\n\n```\n)(.*?)(```)'
    match = re.search(tree_pattern, content, re.DOTALL)
    
    if not match:
        print(f"⚠️  Seção de estrutura não encontrada em {doc_file}")
        return
    
    # Gera nova árvore
    base_dir = get_base_dir_for_doc(doc_file)
    new_tree = generate_tree(base_dir)
    
    # Substitui a árvore antiga
    new_content = content[:match.start(2)] + new_tree + content[match.end(2):]
    
    # Atualiza timestamp
    timestamp_pattern = r'(_Última atualização: )(.*?)(_)'
    new_content = re.sub(timestamp_pattern, 
                        f'\\g<1>{datetime.now().strftime("%Y-%m-%d %H:%M")}\\g<3>', 
                        new_content)
    
    # Salva o arquivo atualizado
    with open(doc_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ Atualizado: {doc_file}")

def get_base_dir_for_doc(doc_file: Path) -> Path:
    """Retorna o diretório base para um arquivo de documentação."""
    doc_name = doc_file.stem
    
    # Remove prefixo app_ e converte para caminho
    if doc_name.startswith("app_"):
        path = "app/" + doc_name[4:]
    else:
        path = doc_name
    
    # Converte underscores para barras
    path = path.replace('_', '/')
    
    return PROJECT_ROOT / path

def generate_tree(directory: Path) -> str:
    """Gera a estrutura em árvore de um diretório."""
    lines = []
    
    def add_tree(path: Path, prefix: str = "", is_last: bool = True):
        if should_ignore(path):
            return
        
        name = path.name
        if path.is_dir():
            name += "/"
        
        connector = "└── " if is_last else "├── "
        
        if prefix == "":  # Raiz
            lines.append(name)
        else:
            lines.append(f"{prefix}{connector}{name}")
        
        if path.is_dir():
            # Prepara prefixo para filhos
            child_prefix = prefix + ("    " if is_last else "│   ") if prefix else ""
            
            try:
                items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
                items = [item for item in items if not should_ignore(item)]
                
                for i, item in enumerate(items):
                    add_tree(item, child_prefix, i == len(items) - 1)
            except PermissionError:
                pass
    
    add_tree(directory)
    return '\n'.join(lines)

def should_ignore(path: Path) -> bool:
    """Verifica se o arquivo/diretório deve ser ignorado."""
    name = path.name
    
    if path.is_dir() and name in IGNORE_DIRS:
        return True
    
    if path.is_file() and any(name.endswith(ext) for ext in IGNORE_FILES):
        return True
    
    return False

def update_file_table(doc_file: Path, new_file: Path, action: str):
    """Atualiza a tabela de arquivos detalhados se existir."""
    if not doc_file.exists():
        return
    
    with open(doc_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verifica se tem tabela de detalhamento
    if "## 📁 Detalhamento dos Arquivos" not in content:
        return
    
    # Extrai informações do novo arquivo
    relative_path = new_file.relative_to(get_base_dir_for_doc(doc_file))
    file_type = "📁 Dir" if new_file.is_dir() else "📄"
    description = get_file_description(new_file)
    
    # Encontra a tabela
    table_pattern = r'(## 📁 Detalhamento dos Arquivos\n\n.*?\n\|.*?\|.*?\|.*?\|\n)(.*?)(\n\n)'
    match = re.search(table_pattern, content, re.DOTALL)
    
    if match:
        table_content = match.group(2)
        
        if action == "create":
            # Adiciona nova linha
            new_row = f"| `{relative_path}` | {file_type} | {description} |"
            
            # Adiciona ordenadamente
            lines = table_content.strip().split('\n')
            lines.append(new_row)
            lines.sort()
            
            new_table = '\n'.join(lines)
            new_content = content[:match.start(2)] + new_table + content[match.end(2):]
            
            with open(doc_file, 'w', encoding='utf-8') as f:
                f.write(new_content)

def get_file_description(file_path: Path) -> str:
    """Obtém descrição básica de um arquivo."""
    name = file_path.name
    
    if name == "__init__.py":
        return "Inicializador do módulo Python"
    elif name.endswith("_service.py"):
        return f"Serviço de {name.replace('_service.py', '').replace('_', ' ')}"
    elif name.endswith("_routes.py"):
        return f"Rotas API para {name.replace('_routes.py', '').replace('_', ' ')}"
    elif name.endswith("_model.py") or name.endswith("_models.py"):
        return f"Modelo de dados"
    elif name.endswith("_schema.py") or name.endswith("_schemas.py"):
        return f"Schema de validação"
    elif name.endswith(".py"):
        return "Módulo Python"
    elif file_path.is_dir():
        return "Diretório do projeto"
    
    return "Arquivo do projeto"

def update_statistics(doc_file: Path):
    """Atualiza as estatísticas no arquivo de documentação."""
    if not doc_file.exists():
        return
    
    base_dir = get_base_dir_for_doc(doc_file)
    
    # Conta arquivos e diretórios
    total_files = 0
    total_dirs = 0
    file_types = {}
    
    for root, dirs, files in os.walk(base_dir):
        root_path = Path(root)
        dirs[:] = [d for d in dirs if not should_ignore(root_path / d)]
        
        total_dirs += len(dirs)
        
        for file in files:
            if not should_ignore(root_path / file):
                total_files += 1
                ext = Path(file).suffix.lower()
                file_types[ext] = file_types.get(ext, 0) + 1
    
    with open(doc_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Atualiza estatísticas
    stats_pattern = r'(## 📊 Estatísticas\n\n)(.*?)(\n\n)'
    match = re.search(stats_pattern, content, re.DOTALL)
    
    if match:
        new_stats = []
        new_stats.append(f"- **Total de arquivos**: {total_files}")
        new_stats.append(f"- **Total de diretórios**: {total_dirs}")
        new_stats.append(f"- **Tipos de arquivo**:")
        
        for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
            if ext:
                new_stats.append(f"  - `{ext}`: {count} arquivo(s)")
        
        new_content = content[:match.start(2)] + '\n'.join(new_stats) + content[match.end(2):]
        
        with open(doc_file, 'w', encoding='utf-8') as f:
            f.write(new_content)

def main():
    """Função principal do hook."""
    # Lê dados do hook
    try:
        hook_data = json.load(sys.stdin)
    except:
        sys.exit(0)
    
    # Extrai informações
    tool_name = hook_data.get("tool", "")
    params = hook_data.get("params", {})
    
    # Processa apenas ferramentas que criam/modificam arquivos
    if tool_name not in ["Write", "Edit", "MultiEdit"]:
        sys.exit(0)
    
    # Determina o arquivo afetado
    file_path = None
    
    if tool_name == "Write":
        file_path = params.get("file_path")
    elif tool_name == "Edit":
        file_path = params.get("file_path")
    elif tool_name == "MultiEdit":
        file_path = params.get("file_path")
    
    if not file_path:
        sys.exit(0)
    
    file_path = Path(file_path)
    
    # Verifica se é dentro do projeto
    try:
        relative_path = file_path.relative_to(PROJECT_ROOT)
    except ValueError:
        # Arquivo fora do projeto
        sys.exit(0)
    
    # Ignora arquivos na pasta architecture
    if str(relative_path).startswith("architecture/"):
        sys.exit(0)
    
    # Determina qual documentação atualizar
    doc_file = get_doc_file_for_path(file_path)
    
    if not doc_file:
        sys.exit(0)
    
    print(f"🔄 Atualizando documentação de arquitetura...")
    print(f"📄 Arquivo modificado: {relative_path}")
    
    # Atualiza a árvore
    update_tree_in_file(doc_file, file_path)
    
    # Atualiza a tabela de arquivos (se existir)
    update_file_table(doc_file, file_path, "create" if tool_name == "Write" else "update")
    
    # Atualiza estatísticas
    update_statistics(doc_file)
    
    print(f"✅ Documentação atualizada automaticamente!")

if __name__ == "__main__":
    main()