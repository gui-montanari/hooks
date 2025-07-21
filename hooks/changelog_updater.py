#!/usr/bin/env python3
"""
Hook inteligente para atualizar CHANGELOG.md com análise profunda de mudanças.
Atualiza com frequência adaptativa baseada em múltiplos critérios.
"""

import json
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import re
from typing import Dict, List, Tuple, Optional, Any

# Configurações
TOKEN_COUNT_FILE = Path(__file__).parent.parent / ".token_count.json"
CHANGELOG_FILE = Path(__file__).parent.parent / "CHANGELOG.md"
MILESTONE_INTERVAL = 10000  # Atualiza a cada 10k tokens (mais frequente)
PROJECT_ROOT = Path(__file__).parent.parent
SIGNIFICANT_CHANGES_THRESHOLD = 5  # Atualiza após 5 mudanças significativas
MAX_TIME_WITHOUT_UPDATE = 24 * 3600  # 24 horas em segundos

# Padrões para ignorar commits automáticos
AUTO_COMMIT_PATTERNS = [
    r"🤖.*Auto-save at \d+,?\d* tokens",
    r"Auto-commit:.*tokens",
    r"Merge branch",
    r"Merge pull request",
    r"^\[skip[\s-]?ci\]",
    r"^\[ci[\s-]?skip\]"
]

# Palavras-chave para categorização avançada
CATEGORY_KEYWORDS = {
    'features': {
        'keywords': ['add', 'create', 'implement', 'new', 'introduce', 'feature'],
        'emoji': '🚀',
        'title': 'Features',
        'priority': 8
    },
    'performance': {
        'keywords': ['optimize', 'performance', 'speed', 'fast', 'improve performance', 'cache'],
        'emoji': '⚡',
        'title': 'Performance',
        'priority': 7
    },
    'fixes': {
        'keywords': ['fix', 'resolve', 'correct', 'repair', 'patch', 'bug', 'issue'],
        'emoji': '🐛',
        'title': 'Bug Fixes',
        'priority': 6
    },
    'security': {
        'keywords': ['security', 'vulnerability', 'secure', 'auth', 'permission', 'access'],
        'emoji': '🔒',
        'title': 'Security',
        'priority': 10
    },
    'breaking': {
        'keywords': ['breaking', 'major', 'incompatible', 'migration required'],
        'emoji': '💥',
        'title': 'Breaking Changes',
        'priority': 10
    },
    'refactoring': {
        'keywords': ['refactor', 'restructure', 'reorganize', 'cleanup', 'simplify'],
        'emoji': '♻️',
        'title': 'Refactoring',
        'priority': 4
    },
    'documentation': {
        'keywords': ['docs', 'documentation', 'readme', 'comment', 'docstring'],
        'emoji': '📚',
        'title': 'Documentation',
        'priority': 3
    },
    'devops': {
        'keywords': ['ci', 'cd', 'deploy', 'docker', 'workflow', 'pipeline', 'config'],
        'emoji': '🔧',
        'title': 'DevOps',
        'priority': 5
    },
    'tests': {
        'keywords': ['test', 'spec', 'coverage', 'unit test', 'integration test'],
        'emoji': '🧪',
        'title': 'Tests',
        'priority': 5
    }
}

def load_token_count() -> Dict[str, Any]:
    """Carrega contagem atual de tokens com campos do changelog."""
    if TOKEN_COUNT_FILE.exists():
        with open(TOKEN_COUNT_FILE, 'r') as f:
            data = json.load(f)
            
            # Garante que campos do changelog existem
            if "last_changelog_milestone" not in data:
                data["last_changelog_milestone"] = 0
            if "changelog_stats" not in data:
                data["changelog_stats"] = {
                    "last_update": None,
                    "significant_changes_since_update": 0,
                    "total_commits_analyzed": 0,
                    "last_significant_change": None
                }
            
            return data
    
    return {
        "total": 0,
        "last_update": None,
        "last_milestone": 0,
        "last_changelog_milestone": 0,
        "changelog_stats": {
            "last_update": None,
            "significant_changes_since_update": 0,
            "total_commits_analyzed": 0,
            "last_significant_change": None
        }
    }

def save_token_count(data: Dict[str, Any]) -> None:
    """Salva contagem de tokens."""
    with open(TOKEN_COUNT_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def is_auto_commit(commit: Dict[str, str]) -> bool:
    """Verifica se é um commit automático que deve ser ignorado."""
    subject = commit.get('subject', '')
    
    for pattern in AUTO_COMMIT_PATTERNS:
        if re.search(pattern, subject, re.IGNORECASE):
            return True
    
    return False

def get_commit_importance(commit: Dict[str, Any]) -> int:
    """Calcula a importância de um commit (0-10)."""
    subject_lower = commit['subject'].lower()
    body_lower = commit.get('body', '').lower()
    full_text = f"{subject_lower} {body_lower}"
    
    max_priority = 0
    
    # Verifica cada categoria
    for category, info in CATEGORY_KEYWORDS.items():
        if any(keyword in full_text for keyword in info['keywords']):
            max_priority = max(max_priority, info['priority'])
    
    # Boost para commits com muitos arquivos
    files = get_changed_files(commit['hash'])
    if len(files) > 10:
        max_priority = min(10, max_priority + 2)
    elif len(files) > 5:
        max_priority = min(10, max_priority + 1)
    
    return max_priority

def should_update_changelog(count_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Verifica se deve atualizar o changelog baseado em múltiplos critérios.
    Retorna (should_update, reason)
    """
    current_total = count_data.get("total", 0)
    last_changelog_milestone = count_data.get("last_changelog_milestone", 0)
    changelog_stats = count_data.get("changelog_stats", {})
    
    # Critério 1: Milestone de tokens
    current_milestone = (current_total // MILESTONE_INTERVAL) * MILESTONE_INTERVAL
    if current_milestone > last_changelog_milestone and current_milestone > 0:
        return True, f"token_milestone_{current_milestone}"
    
    # Critério 2: Número de mudanças significativas
    significant_changes = changelog_stats.get("significant_changes_since_update", 0)
    if significant_changes >= SIGNIFICANT_CHANGES_THRESHOLD:
        return True, f"significant_changes_{significant_changes}"
    
    # Critério 3: Tempo desde última atualização
    last_update = changelog_stats.get("last_update")
    if last_update:
        try:
            last_update_time = datetime.fromisoformat(last_update)
            time_since_update = (datetime.now() - last_update_time).total_seconds()
            
            if time_since_update > MAX_TIME_WITHOUT_UPDATE and significant_changes > 0:
                return True, f"time_elapsed_{int(time_since_update/3600)}h"
        except:
            pass
    
    # Critério 4: Mudança crítica (security ou breaking change)
    last_significant = changelog_stats.get("last_significant_change")
    if last_significant and last_significant.get("priority", 0) >= 10:
        return True, "critical_change"
    
    return False, ""

def get_recent_commits(since_date: Optional[str] = None, hours: int = 24) -> List[Dict[str, str]]:
    """Obtém commits recentes do git, filtrando automáticos."""
    try:
        if since_date:
            cmd = ["git", "log", f"--since={since_date}", "--pretty=format:%H|%ai|%s|%b", "--no-merges"]
        else:
            cmd = ["git", "log", f"--since={hours}.hours.ago", "--pretty=format:%H|%ai|%s|%b", "--no-merges"]
        
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        
        if result.returncode != 0:
            return []
        
        commits = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('|', 3)
                if len(parts) >= 3:
                    commit = {
                        'hash': parts[0],
                        'date': parts[1],
                        'subject': parts[2],
                        'body': parts[3] if len(parts) > 3 else ''
                    }
                    
                    # Filtra commits automáticos
                    if not is_auto_commit(commit):
                        commits.append(commit)
        
        return commits
    except Exception as e:
        print(f"Erro ao obter commits: {e}")
        return []

def get_changed_files(commit_hash: str) -> List[Dict[str, str]]:
    """Obtém arquivos modificados em um commit com estatísticas."""
    try:
        # Obtém lista de arquivos com status
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
        
        # Obtém estatísticas de linhas
        stat_result = subprocess.run(
            ["git", "show", "--stat", "--pretty=format:", commit_hash],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        
        # Parse estatísticas se disponível
        if stat_result.returncode == 0:
            lines = stat_result.stdout.strip().split('\n')
            for i, file_info in enumerate(files):
                for line in lines:
                    if file_info['file'] in line:
                        # Extrai +/- de linhas
                        match = re.search(r'(\d+)\s+insertion.*?(\d+)\s+deletion', line)
                        if match:
                            file_info['insertions'] = int(match.group(1))
                            file_info['deletions'] = int(match.group(2))
                        break
        
        return files
    except:
        return []

def categorize_commits_advanced(commits: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Categoriza commits com sistema avançado e scoring."""
    categories = {key: [] for key in CATEGORY_KEYWORDS.keys()}
    categories['other'] = []  # Para commits não categorizados
    
    for commit in commits:
        commit['importance'] = get_commit_importance(commit)
        commit['context'] = analyze_commit_context(commit)
        
        categorized = False
        subject_lower = commit['subject'].lower()
        body_lower = commit.get('body', '').lower()
        full_text = f"{subject_lower} {body_lower}"
        
        # Tenta categorizar por palavras-chave
        best_category = None
        best_priority = -1
        
        for category, info in CATEGORY_KEYWORDS.items():
            if any(keyword in full_text for keyword in info['keywords']):
                if info['priority'] > best_priority:
                    best_category = category
                    best_priority = info['priority']
        
        if best_category:
            categories[best_category].append(commit)
            categorized = True
        
        # Se não categorizou, analisa pelos arquivos modificados
        if not categorized:
            context = commit['context']
            if 'Tests' in context['areas']:
                categories['tests'].append(commit)
            elif 'Documentation' in context['file_types']:
                categories['documentation'].append(commit)
            else:
                categories['other'].append(commit)
    
    # Remove categorias vazias
    return {k: v for k, v in categories.items() if v}

def analyze_commit_context(commit: Dict[str, str]) -> Dict[str, Any]:
    """Analisa o contexto de um commit para gerar descrição mais rica."""
    files = get_changed_files(commit['hash'])
    
    file_types = set()
    areas = set()
    total_insertions = 0
    total_deletions = 0
    
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
        elif filepath.endswith('.sql'):
            file_types.add('Database')
        elif filepath.endswith(('.html', '.css', '.scss')):
            file_types.add('Frontend')
        
        # Identifica área do projeto
        if 'hooks/' in filepath:
            areas.add('Hooks')
        elif 'app/' in filepath:
            areas.add('Application')
        elif 'scripts/' in filepath:
            areas.add('Scripts')
        elif 'tests/' in filepath or 'test_' in filepath:
            areas.add('Tests')
        elif 'docs/' in filepath:
            areas.add('Documentation')
        elif '.github/' in filepath:
            areas.add('CI/CD')
        elif 'alembic/' in filepath or 'migrations/' in filepath:
            areas.add('Database Migrations')
        
        # Soma estatísticas
        total_insertions += file_info.get('insertions', 0)
        total_deletions += file_info.get('deletions', 0)
    
    return {
        'files_count': len(files),
        'file_types': list(file_types),
        'areas': list(areas),
        'files': files[:5],  # Primeiros 5 arquivos
        'insertions': total_insertions,
        'deletions': total_deletions,
        'net_changes': total_insertions - total_deletions
    }

def get_commit_statistics(commits: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Gera estatísticas dos commits."""
    if not commits:
        return {}
    
    total_insertions = 0
    total_deletions = 0
    affected_files = set()
    authors = set()
    
    for commit in commits:
        context = commit.get('context', {})
        total_insertions += context.get('insertions', 0)
        total_deletions += context.get('deletions', 0)
        
        for file_info in context.get('files', []):
            affected_files.add(file_info['file'])
    
    # Obtém período de tempo
    dates = [datetime.fromisoformat(c['date'].replace(' +', '+')) for c in commits]
    if dates:
        period_start = min(dates)
        period_end = max(dates)
    else:
        period_start = period_end = datetime.now()
    
    return {
        'total_commits': len(commits),
        'total_insertions': total_insertions,
        'total_deletions': total_deletions,
        'net_changes': total_insertions - total_deletions,
        'affected_files': len(affected_files),
        'period_start': period_start,
        'period_end': period_end,
        'duration_hours': int((period_end - period_start).total_seconds() / 3600)
    }

def generate_progress_bar(percentage: float, width: int = 20) -> str:
    """Gera uma barra de progresso ASCII."""
    filled = int(width * percentage / 100)
    bar = '█' * filled + '░' * (width - filled)
    return f"[{bar}] {percentage:.1f}%"

def generate_changelog_entry_rich(categories: Dict[str, List[Dict[str, Any]]], 
                                 milestone_info: str,
                                 statistics: Dict[str, Any]) -> str:
    """Gera entrada de changelog com formato rico e estatísticas."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H:%M")
    
    # Calcula versão (incrementa minor para features, patch para fixes)
    has_features = bool(categories.get('features'))
    has_breaking = bool(categories.get('breaking'))
    version_bump = "major" if has_breaking else "minor" if has_features else "patch"
    
    # Cabeçalho
    entry = f"## [{date_str} - {time_str}] - {milestone_info}\n\n"
    
    # Resumo Executivo
    if statistics:
        entry += "### 📊 **Resumo Executivo**\n"
        entry += f"- **Período**: {statistics['period_start'].strftime('%d/%m %H:%M')} - "
        entry += f"{statistics['period_end'].strftime('%d/%m %H:%M')}\n"
        entry += f"- **Commits Significativos**: {statistics['total_commits']}\n"
        entry += f"- **Arquivos Impactados**: {statistics['affected_files']}\n"
        entry += f"- **Linhas Modificadas**: +{statistics['total_insertions']:,} / -{statistics['total_deletions']:,}\n"
        entry += f"- **Mudança Líquida**: {'+' if statistics['net_changes'] >= 0 else ''}{statistics['net_changes']:,} linhas\n"
        entry += "\n"
    
    # Destaques principais
    highlights = []
    if categories.get('breaking'):
        highlights.append("⚠️ **Breaking Changes** que requerem atenção")
    if categories.get('security'):
        highlights.append("🔒 **Melhorias de Segurança** implementadas")
    if categories.get('features'):
        highlights.append(f"🚀 **{len(categories['features'])} novas features** adicionadas")
    if categories.get('performance'):
        highlights.append("⚡ **Otimizações de Performance** aplicadas")
    
    if highlights:
        entry += "### 🎯 **Destaques**\n"
        for highlight in highlights:
            entry += f"- {highlight}\n"
        entry += "\n"
    
    # Categorias com detalhes
    for category_key, commits in categories.items():
        if not commits or category_key == 'other':
            continue
        
        info = CATEGORY_KEYWORDS.get(category_key, {
            'emoji': '📝',
            'title': category_key.title()
        })
        
        entry += f"### {info['emoji']} **{info['title']}**\n\n"
        
        # Ordena por importância
        commits_sorted = sorted(commits, key=lambda x: x.get('importance', 0), reverse=True)
        
        for commit in commits_sorted[:5]:  # Top 5 por categoria
            context = commit['context']
            
            entry += f"#### {commit['subject']}\n"
            
            # Detalhes do commit
            if context['areas']:
                entry += f"- **Áreas**: {', '.join(context['areas'])}\n"
            
            if context['file_types']:
                entry += f"- **Tipos**: {', '.join(context['file_types'])}\n"
            
            if context['net_changes'] != 0:
                entry += f"- **Impacto**: {'+' if context['net_changes'] > 0 else ''}{context['net_changes']} linhas\n"
            
            # Arquivos principais (máximo 3)
            if context['files']:
                entry += f"- **Arquivos**:\n"
                for file_info in context['files'][:3]:
                    status_emoji = '🆕' if file_info['status'] == 'A' else '✏️' if file_info['status'] == 'M' else '🗑️'
                    entry += f"  - {status_emoji} `{file_info['file']}`\n"
            
            # Hash do commit para referência
            entry += f"- **Commit**: [{commit['hash'][:7]}]\n"
            
            entry += "\n"
    
    # Outras mudanças (resumo)
    if categories.get('other'):
        entry += "### 📝 **Outras Mudanças**\n"
        for commit in categories['other'][:3]:
            entry += f"- {commit['subject']}\n"
        if len(categories['other']) > 3:
            entry += f"- _{len(categories['other']) - 3} outras mudanças menores_\n"
        entry += "\n"
    
    # Estatísticas visuais
    entry += "### 📈 **Estatísticas**\n\n"
    
    # Gráfico de atividade por área
    area_stats = {}
    total_commits_by_area = 0
    
    for commits in categories.values():
        for commit in commits:
            for area in commit['context']['areas']:
                area_stats[area] = area_stats.get(area, 0) + 1
                total_commits_by_area += 1
    
    if area_stats:
        entry += "```\nCommits por Área:\n"
        for area, count in sorted(area_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_commits_by_area) * 100
            bar = generate_progress_bar(percentage, 12)
            entry += f"{area:15} {bar} {percentage:5.1f}%\n"
        entry += "```\n\n"
    
    # Informações do milestone
    entry += f"### 🏁 **Marco de Desenvolvimento**\n\n"
    if 'token' in milestone_info:
        tokens = int(re.search(r'\d+', milestone_info).group())
        entry += f"- **Tokens Processados**: {tokens:,}\n"
    entry += f"- **Data/Hora**: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
    entry += f"- **Tipo de Atualização**: {milestone_info.replace('_', ' ').title()}\n"
    
    entry += "\n---\n\n"
    
    return entry

def update_changelog_smart(count_data: Dict[str, Any], reason: str) -> bool:
    """Atualiza o CHANGELOG.md com análise inteligente."""
    # Obtém última data do changelog
    last_changelog_date = get_last_changelog_date()
    
    # Obtém commits recentes
    commits = []
    
    # Se temos histórico de commits do auto_commit, usa isso também
    commit_history = count_data.get('commit_history', [])
    
    if last_changelog_date:
        commits = get_recent_commits(since_date=last_changelog_date)
    else:
        commits = get_recent_commits(hours=48)  # Últimas 48h se não houver referência
    
    print(f"📊 Analisando {len(commits)} commits significativos...")
    
    # Se não houver commits significativos, verifica se deve criar entrada mesmo assim
    if not commits and 'token_milestone' not in reason:
        print("ℹ️  Sem mudanças significativas para documentar.")
        return True
    
    # Categoriza mudanças
    categories = categorize_commits_advanced(commits)
    
    # Gera estatísticas
    statistics = get_commit_statistics(commits)
    
    # Gera nova entrada
    new_entry = generate_changelog_entry_rich(categories, reason, statistics)
    
    # Lê conteúdo atual
    if CHANGELOG_FILE.exists():
        with open(CHANGELOG_FILE, 'r') as f:
            content = f.read()
    else:
        content = """# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/spec/v2.0.0.html).

"""
    
    # Encontra onde inserir
    lines = content.split('\n')
    insert_index = -1
    
    for i, line in enumerate(lines):
        if line.startswith('## [') and '] -' in line:
            insert_index = i
            break
    
    if insert_index == -1:
        # Procura após o cabeçalho
        for i, line in enumerate(lines):
            if line.strip() == '' and i > 5:
                insert_index = i + 1
                break
    
    if insert_index != -1:
        lines.insert(insert_index, new_entry.rstrip())
        content = '\n'.join(lines)
    else:
        content += '\n' + new_entry
    
    # Salva arquivo
    with open(CHANGELOG_FILE, 'w') as f:
        f.write(content)
    
    # Atualiza estatísticas
    count_data['changelog_stats']['last_update'] = datetime.now().isoformat()
    count_data['changelog_stats']['significant_changes_since_update'] = 0
    count_data['changelog_stats']['total_commits_analyzed'] += len(commits)
    
    # Se foi por milestone de tokens, atualiza
    if 'token_milestone' in reason:
        milestone = int(reason.split('_')[-1])
        count_data['last_changelog_milestone'] = milestone
    
    return True

def get_last_changelog_date() -> Optional[str]:
    """Obtém a data da última entrada no changelog."""
    if not CHANGELOG_FILE.exists():
        return None
    
    with open(CHANGELOG_FILE, 'r') as f:
        content = f.read()
    
    # Procura por datas no formato [YYYY-MM-DD]
    date_pattern = r'\[(\d{4}-\d{2}-\d{2})'
    matches = re.findall(date_pattern, content)
    
    if matches:
        return matches[0]
    return None

def main():
    """Função principal do hook."""
    try:
        # Carrega dados
        count_data = load_token_count()
        
        # Analisa commits recentes para atualizar contador de mudanças significativas
        recent_commits = get_recent_commits(hours=4)  # Últimas 4 horas
        
        significant_count = 0
        for commit in recent_commits:
            importance = get_commit_importance(commit)
            if importance >= 5:  # Considera significativo se importância >= 5
                significant_count += 1
                
                # Atualiza última mudança significativa se for crítica
                if importance >= 9:
                    count_data['changelog_stats']['last_significant_change'] = {
                        'commit': commit['hash'],
                        'subject': commit['subject'],
                        'priority': importance,
                        'date': commit['date']
                    }
        
        # Incrementa contador de mudanças significativas
        count_data['changelog_stats']['significant_changes_since_update'] += significant_count
        
        # Verifica se deve atualizar
        should_update, reason = should_update_changelog(count_data)
        
        if should_update:
            print(f"\n📝 Atualizando CHANGELOG.md - Motivo: {reason}")
            print(f"🎯 Mudanças significativas acumuladas: {count_data['changelog_stats']['significant_changes_since_update']}")
            
            if update_changelog_smart(count_data, reason):
                print("✅ CHANGELOG.md atualizado com sucesso!")
                
                # Salva dados atualizados
                save_token_count(count_data)
            else:
                print("⚠️  Erro ao atualizar CHANGELOG.md")
        else:
            # Ainda assim salva o contador de mudanças
            save_token_count(count_data)
            
            # Mostra status
            tokens_until_update = ((count_data['total'] // MILESTONE_INTERVAL) + 1) * MILESTONE_INTERVAL - count_data['total']
            changes_until_update = SIGNIFICANT_CHANGES_THRESHOLD - count_data['changelog_stats']['significant_changes_since_update']
            
            print(f"\n📊 [CHANGELOG] Status:")
            print(f"   📍 Próxima atualização em: {tokens_until_update:,} tokens")
            print(f"   🔄 Mudanças significativas: {count_data['changelog_stats']['significant_changes_since_update']}/{SIGNIFICANT_CHANGES_THRESHOLD}")
            
    except Exception as e:
        print(f"❌ Erro no changelog updater: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()