#!/usr/bin/env python3
"""
Gerador de documentação de arquitetura do projeto.
Cria arquivos markdown com a estrutura e descrições dos diretórios.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Configurações
PROJECT_ROOT = Path(__file__).parent.parent.parent
ARCHITECTURE_DIR = PROJECT_ROOT / "architecture"
IGNORE_DIRS = {'.git', '__pycache__', 'node_modules', '.pytest_cache', '.venv', 'venv', '.env'}
IGNORE_FILES = {'.pyc', '.pyo', '.pyd', '.so', '.egg', '.egg-info', '.DS_Store'}

# Descrições conhecidas dos diretórios principais
KNOWN_DESCRIPTIONS = {
    "app": "Código principal da aplicação backend",
    "app/aiagent": "Sistema de agentes de IA para atendimento automatizado",
    "app/aiagent/models": "Modelos SQLAlchemy para agentes de IA",
    "app/aiagent/routes": "Endpoints da API para funcionalidades de IA",
    "app/aiagent/schemas": "Schemas Pydantic para validação de dados",
    "app/aiagent/services": "Lógica de negócio dos agentes de IA",
    "app/core": "Funcionalidades centrais e compartilhadas",
    "app/core/config": "Configurações e variáveis de ambiente",
    "app/core/logging": "Sistema de logging centralizado",
    "app/core/scheduler": "Agendador de tarefas (APScheduler)",
    "app/core/services": "Serviços compartilhados do sistema",
    "app/api": "Configuração e roteamento da API",
    "app/auth": "Sistema de autenticação e autorização",
    "app/auth/models": "Modelos de usuário e permissões",
    "app/auth/routes": "Endpoints de autenticação",
    "app/auth/services": "Lógica de autenticação JWT",
    "app/db": "Configuração e gerenciamento do banco de dados",
    "app/domain": "Modelos de domínio e entidades de negócio",
    "app/domain/models": "Modelos SQLAlchemy do domínio",
    "app/domain/schemas": "Schemas de validação do domínio",
    "app/infrastructure": "Camada de infraestrutura e serviços externos",
    "app/integrations": "Integrações com serviços externos",
    "app/integrations/wassenger": "Integração com WhatsApp via Wassenger",
    "app/integrations/openai": "Integração com OpenAI GPT",
    "app/integrations/webhooks": "Handlers de webhooks externos",
    "frontend": "Aplicação frontend React",
    "scripts": "Scripts utilitários e de manutenção",
    "logs": "Arquivos de log da aplicação",
    "architecture": "Documentação da arquitetura do projeto",
    "hooks": "Scripts de hooks do Claude Code",
    "alembic": "Migrações do banco de dados",
    "documents": "Documentação geral do projeto",
}

# Descrições de arquivos comuns
FILE_DESCRIPTIONS = {
    "__init__.py": "Inicializador do módulo Python",
    "setup.py": "Configuração de instalação do pacote",
    "requirements.txt": "Dependências Python do projeto",
    "README.md": "Documentação principal",
    "CHANGELOG.md": "Histórico de mudanças",
    ".env": "Variáveis de ambiente",
    ".gitignore": "Arquivos ignorados pelo Git",
    "docker-compose.yml": "Configuração Docker Compose",
    "Dockerfile": "Imagem Docker da aplicação",
    "package.json": "Configuração e dependências Node.js",
    "tsconfig.json": "Configuração TypeScript",
    # Arquivos específicos
    "main.py": "Ponto de entrada da aplicação FastAPI",
    "api.py": "Configuração central da API",
    "database.py": "Configuração de conexão com banco de dados",
    "config.py": "Configurações gerais da aplicação",
    "models.py": "Modelos de dados",
    "schemas.py": "Schemas de validação",
    "routes.py": "Definição de rotas/endpoints",
    "service.py": "Lógica de negócio",
    "utils.py": "Funções utilitárias",
}

def should_ignore(path: Path) -> bool:
    """Verifica se o arquivo/diretório deve ser ignorado."""
    name = path.name
    
    # Ignora diretórios especiais
    if path.is_dir() and name in IGNORE_DIRS:
        return True
    
    # Ignora arquivos por extensão
    if path.is_file():
        if any(name.endswith(ext) for ext in IGNORE_FILES):
            return True
    
    return False

def get_tree_structure(directory: Path, prefix: str = "", is_last: bool = True) -> List[str]:
    """Gera estrutura em árvore estilo 'tree' command."""
    lines = []
    
    if not directory.exists():
        return lines
    
    # Conectores da árvore
    connector = "└── " if is_last else "├── "
    
    # Adiciona o diretório atual
    if prefix == "":  # Raiz
        lines.append(f"{directory.name}/")
    else:
        lines.append(f"{prefix}{connector}{directory.name}/")
    
    # Prepara o prefixo para os filhos
    if prefix == "":
        child_prefix = ""
    else:
        child_prefix = prefix + ("    " if is_last else "│   ")
    
    # Lista e ordena conteúdo
    try:
        items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        items = [item for item in items if not should_ignore(item)]
        
        for i, item in enumerate(items):
            is_last_item = i == len(items) - 1
            
            if item.is_dir():
                lines.extend(get_tree_structure(item, child_prefix, is_last_item))
            else:
                connector = "└── " if is_last_item else "├── "
                lines.append(f"{child_prefix}{connector}{item.name}")
    except PermissionError:
        pass
    
    return lines

def get_file_description(file_path: Path, base_path: Path) -> str:
    """Obtém descrição de um arquivo baseado em seu nome e localização."""
    name = file_path.name
    relative_path = file_path.relative_to(base_path)
    
    # Verifica descrições conhecidas
    if name in FILE_DESCRIPTIONS:
        return FILE_DESCRIPTIONS[name]
    
    # Descrições baseadas em padrões
    if name.endswith("_service.py"):
        return f"Serviço de {name.replace('_service.py', '').replace('_', ' ')}"
    elif name.endswith("_routes.py"):
        return f"Rotas API para {name.replace('_routes.py', '').replace('_', ' ')}"
    elif name.endswith("_model.py") or name.endswith("_models.py"):
        return f"Modelo de dados para {name.replace('_model.py', '').replace('_models.py', '').replace('_', ' ')}"
    elif name.endswith("_schema.py") or name.endswith("_schemas.py"):
        return f"Schema de validação para {name.replace('_schema.py', '').replace('_schemas.py', '').replace('_', ' ')}"
    elif name.endswith("_test.py") or name.startswith("test_"):
        return f"Testes para {name.replace('_test.py', '').replace('test_', '').replace('_', ' ')}"
    elif name.endswith(".md"):
        return "Documentação"
    elif name.endswith(".json"):
        return "Arquivo de configuração JSON"
    elif name.endswith(".yml") or name.endswith(".yaml"):
        return "Arquivo de configuração YAML"
    elif name.endswith(".sql"):
        return "Script SQL"
    elif name.endswith(".sh"):
        return "Script Shell"
    elif name.endswith(".py"):
        return "Módulo Python"
    
    return "Arquivo do projeto"

def generate_directory_documentation(directory: Path, output_file: Path, detailed: bool = False):
    """Gera documentação para um diretório específico."""
    lines = []
    
    # Cabeçalho
    dir_name = directory.name
    relative_path = directory.relative_to(PROJECT_ROOT)
    
    lines.append(f"# Arquitetura - {dir_name}")
    lines.append(f"\n> Documentação da estrutura do diretório `{relative_path}`")
    lines.append(f"\n_Última atualização: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n")
    
    # Descrição do diretório
    description = KNOWN_DESCRIPTIONS.get(str(relative_path), "")
    if description:
        lines.append(f"## 📋 Descrição\n")
        lines.append(f"{description}\n")
    
    # Estrutura em árvore
    lines.append("## 🌳 Estrutura de Diretórios\n")
    lines.append("```")
    tree_lines = get_tree_structure(directory, "", True)
    lines.extend(tree_lines)
    lines.append("```\n")
    
    # Tabela detalhada se solicitado
    if detailed:
        lines.append("## 📁 Detalhamento dos Arquivos\n")
        lines.append("| Arquivo/Diretório | Tipo | Descrição |")
        lines.append("|-------------------|------|-----------|")
        
        # Coleta todos os arquivos recursivamente
        for root, dirs, files in os.walk(directory):
            root_path = Path(root)
            
            # Remove diretórios ignorados
            dirs[:] = [d for d in dirs if not should_ignore(root_path / d)]
            
            # Processa diretórios
            for dir_name in sorted(dirs):
                dir_path = root_path / dir_name
                relative = dir_path.relative_to(directory)
                desc = KNOWN_DESCRIPTIONS.get(str(dir_path.relative_to(PROJECT_ROOT)), "Diretório do projeto")
                lines.append(f"| `{relative}/` | 📁 Dir | {desc} |")
            
            # Processa arquivos
            for file_name in sorted(files):
                file_path = root_path / file_name
                if not should_ignore(file_path):
                    relative = file_path.relative_to(directory)
                    desc = get_file_description(file_path, directory)
                    icon = "📄" if file_name.endswith('.py') else "📋"
                    lines.append(f"| `{relative}` | {icon} | {desc} |")
        
        lines.append("")
    
    # Estatísticas
    lines.append("## 📊 Estatísticas\n")
    
    # Conta arquivos e diretórios
    total_files = 0
    total_dirs = 0
    file_types = {}
    
    for root, dirs, files in os.walk(directory):
        root_path = Path(root)
        dirs[:] = [d for d in dirs if not should_ignore(root_path / d)]
        
        total_dirs += len(dirs)
        
        for file in files:
            if not should_ignore(root_path / file):
                total_files += 1
                ext = Path(file).suffix.lower()
                file_types[ext] = file_types.get(ext, 0) + 1
    
    lines.append(f"- **Total de arquivos**: {total_files}")
    lines.append(f"- **Total de diretórios**: {total_dirs}")
    lines.append(f"- **Tipos de arquivo**:")
    
    for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
        if ext:
            lines.append(f"  - `{ext}`: {count} arquivo(s)")
    
    lines.append("")
    
    # Salva o arquivo
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"✅ Gerado: {output_file}")

def generate_main_readme():
    """Gera o README principal da arquitetura."""
    output_file = ARCHITECTURE_DIR / "README.md"
    
    lines = []
    lines.append("# 🏗️ Arquitetura do Projeto Hermes Panel Admin")
    lines.append("\n> Documentação completa da estrutura e arquitetura do projeto")
    lines.append(f"\n_Última atualização: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n")
    
    lines.append("## 📚 Índice de Documentação\n")
    lines.append("Esta pasta contém a documentação detalhada da arquitetura de cada módulo:\n")
    
    # Lista documentações disponíveis
    docs = [
        ("app.md", "Arquitetura completa do backend"),
        ("frontend.md", "Estrutura do frontend React"),
        ("scripts.md", "Scripts utilitários"),
        ("logs.md", "Sistema de logging"),
    ]
    
    for doc, desc in docs:
        lines.append(f"- [`{doc}`](./{doc}) - {desc}")
    
    lines.append("\n### 📁 Documentação Detalhada dos Módulos Core\n")
    
    core_modules = [
        ("app/aiagent", "Sistema de Agentes de IA"),
        ("app/core", "Funcionalidades Centrais"),
        ("app/api", "Configuração da API"),
        ("app/auth", "Autenticação e Autorização"),
        ("app/db", "Camada de Dados"),
        ("app/domain", "Modelos de Domínio"),
        ("app/infrastructure", "Infraestrutura"),
        ("app/integrations", "Integrações Externas"),
    ]
    
    for module, desc in core_modules:
        doc_name = module.replace('/', '_') + ".md"
        lines.append(f"- [`{doc_name}`](./{doc_name}) - {desc}")
    
    lines.append("\n## 🔄 Atualização Automática\n")
    lines.append("Esta documentação é mantida automaticamente por hooks do Claude Code.")
    lines.append("Sempre que novos arquivos ou diretórios são criados, a documentação é atualizada.\n")
    
    lines.append("## 🏛️ Visão Geral da Arquitetura\n")
    lines.append("```")
    lines.append("hermespaneladm/")
    lines.append("├── app/              # Backend FastAPI")
    lines.append("│   ├── aiagent/      # Sistema de IA")
    lines.append("│   ├── core/         # Núcleo da aplicação")
    lines.append("│   ├── auth/         # Autenticação")
    lines.append("│   ├── integrations/ # APIs externas")
    lines.append("│   └── domain/       # Modelos de negócio")
    lines.append("├── frontend/         # Frontend React")
    lines.append("├── scripts/          # Scripts úteis")
    lines.append("├── architecture/     # Esta documentação")
    lines.append("├── hooks/            # Hooks Claude Code")
    lines.append("└── logs/             # Arquivos de log")
    lines.append("```")
    
    # Salva
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"✅ Gerado: {output_file}")

def main():
    """Função principal do gerador."""
    print("🏗️  Gerando documentação de arquitetura...")
    
    # Cria diretório de arquitetura
    ARCHITECTURE_DIR.mkdir(exist_ok=True)
    
    # Gera README principal
    generate_main_readme()
    
    # Gera documentação dos diretórios principais (visão geral)
    main_dirs = [
        (PROJECT_ROOT / "app", "app.md", False),
        (PROJECT_ROOT / "frontend", "frontend.md", False),
        (PROJECT_ROOT / "scripts", "scripts.md", False),
        (PROJECT_ROOT / "logs", "logs.md", False),
    ]
    
    for directory, filename, detailed in main_dirs:
        if directory.exists():
            output = ARCHITECTURE_DIR / filename
            generate_directory_documentation(directory, output, detailed)
    
    # Gera documentação detalhada dos módulos core
    detailed_modules = [
        (PROJECT_ROOT / "app" / "aiagent", True),
        (PROJECT_ROOT / "app" / "core", True),
        (PROJECT_ROOT / "app" / "api", True),
        (PROJECT_ROOT / "app" / "auth", True),
        (PROJECT_ROOT / "app" / "db", True),
        (PROJECT_ROOT / "app" / "domain", True),
        (PROJECT_ROOT / "app" / "infrastructure", True),
        (PROJECT_ROOT / "app" / "integrations", True),
    ]
    
    for directory, detailed in detailed_modules:
        if directory.exists():
            filename = str(directory.relative_to(PROJECT_ROOT)).replace('/', '_') + ".md"
            output = ARCHITECTURE_DIR / filename
            generate_directory_documentation(directory, output, detailed)
    
    print("\n✨ Documentação de arquitetura gerada com sucesso!")
    print(f"📁 Arquivos criados em: {ARCHITECTURE_DIR}")

if __name__ == "__main__":
    main()