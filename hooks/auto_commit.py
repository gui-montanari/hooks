#!/usr/bin/env python3
"""
Hook para fazer commit e push automático a cada 50k tokens.
"""

import json
import sys
import subprocess
from datetime import datetime
from pathlib import Path
import os

# Configurações
TOKEN_COUNT_FILE = Path(__file__).parent.parent / ".token_count.json"
COMMIT_INTERVAL = 50000  # Commit a cada 50k tokens
PROJECT_ROOT = Path(__file__).parent.parent

def load_token_count():
    """Carrega contagem atual de tokens."""
    if TOKEN_COUNT_FILE.exists():
        with open(TOKEN_COUNT_FILE, 'r') as f:
            data = json.load(f)
            # Garante que last_commit_milestone existe
            if "last_commit_milestone" not in data:
                data["last_commit_milestone"] = 0
            return data
    return {"total": 0, "last_update": None, "last_commit_milestone": 0}

def save_token_count(data):
    """Salva contagem de tokens."""
    with open(TOKEN_COUNT_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def should_commit(current_total, last_commit_milestone):
    """Verifica se deve fazer commit."""
    current_milestone = (current_total // COMMIT_INTERVAL) * COMMIT_INTERVAL
    return current_milestone > last_commit_milestone and current_milestone > 0

def get_recent_changes():
    """Obtém resumo das mudanças recentes."""
    try:
        # Pega arquivos modificados
        result = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        changed_files = result.stdout.strip().split('\n') if result.stdout else []
        
        # Pega arquivos staged
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        staged_files = result.stdout.strip().split('\n') if result.stdout else []
        
        # Pega arquivos untracked
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        untracked_files = result.stdout.strip().split('\n') if result.stdout else []
        
        all_files = list(set(changed_files + staged_files + untracked_files))
        all_files = [f for f in all_files if f]  # Remove strings vazias
        
        return all_files
    except:
        return []

def generate_commit_message(milestone_tokens, changed_files):
    """Gera mensagem de commit baseada nas mudanças."""
    # Analisa tipos de arquivos modificados
    file_types = set()
    areas = set()
    
    for file in changed_files:
        if not file:
            continue
            
        # Identifica tipo de arquivo
        if file.endswith('.py'):
            file_types.add('Python')
        elif file.endswith(('.js', '.ts', '.jsx', '.tsx')):
            file_types.add('JavaScript/TypeScript')
        elif file.endswith(('.html', '.css', '.scss')):
            file_types.add('Frontend')
        elif file.endswith('.sql'):
            file_types.add('Database')
        elif file.endswith(('.md', '.txt')):
            file_types.add('Documentation')
        elif file.endswith(('.json', '.yml', '.yaml')):
            file_types.add('Configuration')
        
        # Identifica área do projeto
        if 'app/' in file:
            areas.add('Application')
        elif 'scripts/' in file:
            areas.add('Scripts')
        elif 'tests/' in file or 'test_' in file:
            areas.add('Tests')
        elif 'docs/' in file or 'documentation/' in file:
            areas.add('Documentation')
        elif 'architecture/' in file:
            areas.add('Architecture')
    
    # Monta mensagem de commit
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    if not changed_files:
        message = f"🤖 Auto-commit: {milestone_tokens:,} tokens milestone"
    else:
        # Título do commit
        if len(areas) == 1:
            area = list(areas)[0]
            message = f"🤖 {area}: Auto-save at {milestone_tokens:,} tokens"
        elif len(areas) > 1:
            message = f"🤖 Multi-area update: Auto-save at {milestone_tokens:,} tokens"
        else:
            message = f"🤖 Project update: Auto-save at {milestone_tokens:,} tokens"
        
        # Corpo do commit
        body_parts = []
        
        if file_types:
            body_parts.append(f"File types: {', '.join(sorted(file_types))}")
        
        if areas:
            body_parts.append(f"Areas affected: {', '.join(sorted(areas))}")
        
        body_parts.append(f"Files changed: {len(changed_files)}")
        body_parts.append(f"Timestamp: {date_str}")
        
        # Lista alguns arquivos se não forem muitos
        if len(changed_files) <= 5:
            body_parts.append("\nFiles:")
            for file in changed_files[:5]:
                if file:
                    body_parts.append(f"  - {file}")
        
        message = message + "\n\n" + "\n".join(body_parts)
    
    return message

def perform_git_operations(commit_message):
    """Executa operações git: add, commit e push."""
    try:
        # Git add all
        print("📁 Adicionando arquivos ao git...")
        result = subprocess.run(
            ["git", "add", "-A"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"⚠️  Erro no git add: {result.stderr}")
            return False, None
        
        # Git commit
        print("💾 Fazendo commit...")
        result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            if "nothing to commit" in result.stdout:
                print("ℹ️  Nada para commitar")
                return True, None
            else:
                print(f"⚠️  Erro no git commit: {result.stderr}")
                return False, None
        
        # Git push
        print("🚀 Fazendo push para o GitHub...")
        result = subprocess.run(
            ["git", "push"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"⚠️  Erro no git push: {result.stderr}")
            # Tenta push com upstream
            result = subprocess.run(
                ["git", "push", "--set-upstream", "origin", "main"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"⚠️  Erro no git push com upstream: {result.stderr}")
                return False, None
        
        print("✅ Commit e push realizados com sucesso!")
        return True, commit_message
        
    except Exception as e:
        print(f"❌ Erro durante operações git: {str(e)}")
        return False, None

def main():
    try:
        # Carrega contagem atual
        count_data = load_token_count()
        current_total = count_data.get("total", 0)
        last_commit_milestone = count_data.get("last_commit_milestone", 0)
        
        # Debug info
        print(f"[AUTO-COMMIT] Total tokens: {current_total:,}, Last commit milestone: {last_commit_milestone:,}")
        
        # Verifica se deve fazer commit
        if should_commit(current_total, last_commit_milestone):
            current_milestone = (current_total // COMMIT_INTERVAL) * COMMIT_INTERVAL
            
            print(f"\n🎯 Milestone de {current_milestone:,} tokens atingido!")
            print(f"🔄 Iniciando auto-commit e push...")
            
            # Verifica se estamos em um repositório git
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--git-dir"],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    print("❌ Erro: Não estamos em um repositório git!")
                    return
            except Exception as e:
                print(f"❌ Erro ao verificar repositório git: {e}")
                return
            
            # Obtém mudanças recentes
            changed_files = get_recent_changes()
            print(f"📝 Arquivos modificados: {len(changed_files)}")
            
            # Gera mensagem de commit
            commit_message = generate_commit_message(current_milestone, changed_files)
            
            # Executa operações git
            success, commit_msg = perform_git_operations(commit_message)
            if success:
                # Atualiza último milestone de commit e adiciona informações do commit
                count_data["last_commit_milestone"] = current_milestone
                count_data["last_commit_date"] = datetime.now().isoformat()
                count_data["last_commit_message"] = commit_msg if commit_msg else commit_message
                save_token_count(count_data)
                print(f"📊 Próximo auto-commit em {current_milestone + COMMIT_INTERVAL:,} tokens")
            else:
                print("⚠️  Auto-commit falhou, será tentado novamente no próximo milestone")
        else:
            next_milestone = ((current_total // COMMIT_INTERVAL) + 1) * COMMIT_INTERVAL
            tokens_needed = next_milestone - current_total
            print(f"[AUTO-COMMIT] Próximo commit em {next_milestone:,} tokens (faltam {tokens_needed:,})")
            
    except Exception as e:
        print(f"❌ Erro crítico no auto-commit: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()