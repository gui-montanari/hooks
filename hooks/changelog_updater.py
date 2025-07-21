#!/usr/bin/env python3
"""
Hook para atualizar CHANGELOG.md a cada 10k tokens com mudanças reais do código.
Analisa commits recentes e mantém o padrão do arquivo existente.
"""

import json
import sys
import subprocess
from datetime import datetime
from pathlib import Path
import re

# Configurações
TOKEN_COUNT_FILE = Path(__file__).parent.parent / ".token_count.json"
CHANGELOG_FILE = Path(__file__).parent.parent / "CHANGELOG.md"
MILESTONE_INTERVAL = 10000  # Atualiza a cada 10k
PROJECT_ROOT = Path(__file__).parent.parent

def load_token_count():
    """Carrega contagem atual de tokens."""
    if TOKEN_COUNT_FILE.exists():
        with open(TOKEN_COUNT_FILE, 'r') as f:
            return json.load(f)
    return {"total": 0, "last_update": None, "last_milestone": 0}

def save_token_count(data):
    """Salva contagem de tokens."""
    with open(TOKEN_COUNT_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def should_update_changelog(current_total, last_milestone):
    """Verifica se deve atualizar o changelog."""
    current_milestone = (current_total // MILESTONE_INTERVAL) * MILESTONE_INTERVAL
    return current_milestone > last_milestone and current_milestone > 0

def get_last_changelog_date():
    """Obtém a data da última entrada no changelog."""
    if not CHANGELOG_FILE.exists():
        return None
    
    with open(CHANGELOG_FILE, 'r') as f:
        content = f.read()
    
    # Procura por datas no formato [YYYY-MM-DD]
    date_pattern = r'\[(\d{4}-\d{2}-\d{2})\]'
    matches = re.findall(date_pattern, content)
    
    if matches:
        # Retorna a data mais recente (primeira no arquivo)
        return matches[0]
    return None

def get_recent_commits(since_date=None):
    """Obtém commits recentes do git."""
    try:
        # Se não tiver data, pega commits das últimas 24 horas
        if not since_date:
            cmd = ["git", "log", "--since=24.hours.ago", "--pretty=format:%H|%ai|%s|%b", "--no-merges"]
        else:
            cmd = ["git", "log", f"--since={since_date}", "--pretty=format:%H|%ai|%s|%b", "--no-merges"]
        
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return []
        
        commits = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('|', 3)
                if len(parts) >= 3:
                    commits.append({
                        'hash': parts[0],
                        'date': parts[1],
                        'subject': parts[2],
                        'body': parts[3] if len(parts) > 3 else ''
                    })
        
        return commits
    except Exception as e:
        print(f"Erro ao obter commits: {e}")
        return []

def get_changed_files(commit_hash):
    """Obtém arquivos modificados em um commit."""
    try:
        result = subprocess.run(
            ["git", "show", "--name-status", "--pretty=format:", commit_hash],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return []
        
        files = []
        for line in result.stdout.strip().split('\n'):
            if line and '\t' in line:
                status, filepath = line.split('\t', 1)
                files.append({'status': status, 'file': filepath})
        
        return files
    except:
        return []

def categorize_changes(commits):
    """Categoriza mudanças dos commits em Added, Modified, Fixed, etc."""
    categories = {
        'added': [],
        'modified': [],
        'fixed': [],
        'removed': [],
        'improved': []
    }
    
    # Palavras-chave para categorização
    keywords = {
        'added': ['add', 'create', 'implement', 'new', 'introduce'],
        'modified': ['update', 'change', 'modify', 'refactor', 'adjust'],
        'fixed': ['fix', 'resolve', 'correct', 'repair', 'patch'],
        'removed': ['remove', 'delete', 'clean', 'drop'],
        'improved': ['improve', 'enhance', 'optimize', 'better']
    }
    
    for commit in commits:
        subject_lower = commit['subject'].lower()
        categorized = False
        
        # Tenta categorizar pelo assunto do commit
        for category, words in keywords.items():
            if any(word in subject_lower for word in words):
                categories[category].append(commit)
                categorized = True
                break
        
        # Se não categorizou, coloca em 'modified' como padrão
        if not categorized:
            categories['modified'].append(commit)
    
    return categories

def analyze_commit_context(commit):
    """Analisa o contexto de um commit para gerar descrição mais rica."""
    files = get_changed_files(commit['hash'])
    
    # Analisa tipos de arquivos modificados
    file_types = set()
    areas = set()
    
    for file_info in files:
        filepath = file_info['file']
        
        # Identifica tipo de arquivo
        if filepath.endswith('.py'):
            file_types.add('Python')
        elif filepath.endswith(('.js', '.ts', '.jsx', '.tsx')):
            file_types.add('JavaScript/TypeScript')
        elif filepath.endswith('.md'):
            file_types.add('Documentation')
        elif filepath.endswith(('.yml', '.yaml', '.json')):
            file_types.add('Configuration')
        
        # Identifica área do projeto
        if 'hooks/' in filepath:
            areas.add('Hooks')
        elif 'app/' in filepath:
            areas.add('Application')
        elif 'scripts/' in filepath:
            areas.add('Scripts')
        elif 'tests/' in filepath:
            areas.add('Tests')
    
    context = {
        'files_count': len(files),
        'file_types': list(file_types),
        'areas': list(areas),
        'files': files[:5]  # Primeiros 5 arquivos
    }
    
    return context

def generate_changelog_entry(categories, milestone_tokens):
    """Gera entrada de changelog no formato padrão."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Título da entrada
    entry = f"## [{date_str}] - Atualização Automática ({milestone_tokens:,} tokens)\n\n"
    
    # Adiciona seções por categoria se houver mudanças
    if any(categories.values()):
        
        # Added
        if categories['added']:
            entry += "### ✅ **Adicionado**\n\n"
            for commit in categories['added'][:5]:  # Limita a 5 por categoria
                context = analyze_commit_context(commit)
                entry += f"#### 🆕 **{commit['subject']}**\n"
                if context['areas']:
                    entry += f"- **Áreas**: {', '.join(context['areas'])}\n"
                if context['file_types']:
                    entry += f"- **Tipos de arquivo**: {', '.join(context['file_types'])}\n"
                if context['files']:
                    entry += f"- **Arquivos principais**:\n"
                    for file_info in context['files'][:3]:
                        entry += f"  - `{file_info['file']}`\n"
                entry += "\n"
        
        # Modified
        if categories['modified']:
            entry += "### 🔧 **Modificado**\n\n"
            for commit in categories['modified'][:5]:
                context = analyze_commit_context(commit)
                entry += f"#### 🔄 **{commit['subject']}**\n"
                if context['areas']:
                    entry += f"- **Áreas**: {', '.join(context['areas'])}\n"
                if context['files_count'] > 0:
                    entry += f"- **Arquivos modificados**: {context['files_count']}\n"
                entry += "\n"
        
        # Fixed
        if categories['fixed']:
            entry += "### 🐛 **Corrigido**\n\n"
            for commit in categories['fixed'][:5]:
                entry += f"#### ❌ **{commit['subject']}**\n"
                context = analyze_commit_context(commit)
                if commit['body']:
                    # Pega primeira linha do body como descrição
                    desc_lines = commit['body'].strip().split('\n')
                    if desc_lines and desc_lines[0]:
                        entry += f"- **Detalhes**: {desc_lines[0]}\n"
                entry += "\n"
        
        # Improved
        if categories['improved']:
            entry += "### 🛠️ **Melhorado**\n\n"
            for commit in categories['improved'][:3]:
                entry += f"- {commit['subject']}\n"
            entry += "\n"
        
        # Token milestone
        entry += f"### 📊 **Marco de Tokens**\n\n"
        entry += f"- Atingido: **{milestone_tokens:,} tokens**\n"
        entry += f"- Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        entry += "\n---\n\n"
    else:
        # Se não houver commits, adiciona apenas o milestone
        entry += f"### 📊 **Marco de Tokens**\n\n"
        entry += f"- Atingido: **{milestone_tokens:,} tokens** sem mudanças significativas no código\n"
        entry += "\n---\n\n"
    
    return entry

def update_changelog(milestone_tokens):
    """Atualiza o CHANGELOG.md com análise real das mudanças."""
    # Obtém última data do changelog
    last_date = get_last_changelog_date()
    
    # Obtém commits recentes
    if last_date:
        # Pega commits desde a última entrada
        commits = get_recent_commits(since_date=last_date)
    else:
        # Pega commits das últimas 24 horas
        commits = get_recent_commits()
    
    print(f"📊 Analisando {len(commits)} commits recentes...")
    
    # Categoriza mudanças
    categories = categorize_changes(commits)
    
    # Gera nova entrada
    new_entry = generate_changelog_entry(categories, milestone_tokens)
    
    # Lê conteúdo atual
    if CHANGELOG_FILE.exists():
        with open(CHANGELOG_FILE, 'r') as f:
            content = f.read()
    else:
        content = "# Changelog\n\nTodas as mudanças notáveis neste projeto serão documentadas neste arquivo.\n\n"
    
    # Remove a seção "Token Milestones" se existir
    if "## Token Milestones" in content:
        # Remove a seção inteira de Token Milestones
        lines = content.split('\n')
        new_lines = []
        skip = False
        
        for i, line in enumerate(lines):
            if line.strip() == "## Token Milestones":
                skip = True
                # Continua pulando até encontrar próxima seção ou fim
                continue
            elif skip and line.startswith("## ") and line.strip() != "## Token Milestones":
                skip = False
            
            if not skip:
                new_lines.append(line)
        
        content = '\n'.join(new_lines)
    
    # Encontra onde inserir (após o cabeçalho, antes da primeira entrada)
    lines = content.split('\n')
    insert_index = -1
    
    # Procura pelo fim do cabeçalho
    for i, line in enumerate(lines):
        if line.startswith('## [') and '] -' in line:
            insert_index = i
            break
    
    if insert_index == -1:
        # Se não encontrou entradas, adiciona após o cabeçalho
        for i, line in enumerate(lines):
            if line.strip() == '' and i > 5:  # Após linhas iniciais
                insert_index = i + 1
                break
    
    if insert_index != -1:
        # Insere nova entrada
        lines.insert(insert_index, new_entry.rstrip())
        content = '\n'.join(lines)
    else:
        # Adiciona ao final
        content += '\n' + new_entry
    
    # Salva arquivo atualizado
    with open(CHANGELOG_FILE, 'w') as f:
        f.write(content)
    
    return True

def main():
    # Este hook roda após o contador principal
    # Então só precisa verificar se deve atualizar o changelog
    
    # Carrega contagem atual
    count_data = load_token_count()
    current_total = count_data.get("total", 0)
    last_milestone = count_data.get("last_milestone", 0)
    
    # Verifica se atingiu novo milestone
    if should_update_changelog(current_total, last_milestone):
        current_milestone = (current_total // MILESTONE_INTERVAL) * MILESTONE_INTERVAL
        
        print(f"\n🎯 Milestone de {current_milestone:,} tokens atingido!")
        print(f"📝 Atualizando CHANGELOG.md com análise de mudanças...")
        
        try:
            # Atualiza changelog com análise real
            if update_changelog(current_milestone):
                print(f"✅ CHANGELOG.md atualizado com sucesso!")
                
                # Atualiza último milestone registrado
                count_data["last_milestone"] = current_milestone
                save_token_count(count_data)
            else:
                print(f"⚠️  Erro ao atualizar CHANGELOG.md")
        except Exception as e:
            print(f"❌ Erro durante atualização: {str(e)}")
            # Ainda assim marca o milestone para evitar loops
            count_data["last_milestone"] = current_milestone
            save_token_count(count_data)

if __name__ == "__main__":
    main()