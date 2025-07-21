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
            # Garante que campos necessários existem
            if "last_commit_milestone" not in data:
                data["last_commit_milestone"] = 0
            if "tokens_since_last_commit" not in data:
                data["tokens_since_last_commit"] = 0
            if "last_reset_at" not in data:
                data["last_reset_at"] = None
            if "total_before_reset" not in data:
                data["total_before_reset"] = None
            return data
    return {
        "total": 0, 
        "last_update": None, 
        "last_commit_milestone": 0,
        "tokens_since_last_commit": 0,
        "last_reset_at": None,
        "total_before_reset": None
    }

def save_token_count(data):
    """Salva contagem de tokens."""
    with open(TOKEN_COUNT_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def detect_and_adjust_reset(count_data):
    """Detecta se houve reset e ajusta last_commit_milestone se necessário."""
    current_total = count_data.get("total", 0)
    last_commit_milestone = count_data.get("last_commit_milestone", 0)
    
    # Detecta reset: total atual menor que último milestone de commit
    if current_total < last_commit_milestone:
        print(f"🔄 Reset detectado! Total ({current_total:,}) < Last Commit Milestone ({last_commit_milestone:,})")
        
        # Ajusta last_commit_milestone para o milestone mais próximo abaixo do total atual
        adjusted_milestone = (current_total // COMMIT_INTERVAL) * COMMIT_INTERVAL
        count_data["last_commit_milestone"] = adjusted_milestone
        
        # Marca que houve reset
        if count_data.get("last_reset_at") is None:
            count_data["last_reset_at"] = datetime.now().isoformat()
            count_data["total_before_reset"] = last_commit_milestone
        
        print(f"📍 Milestone ajustado para: {adjusted_milestone:,}")
        return True, adjusted_milestone
    
    return False, last_commit_milestone

def should_commit(count_data):
    """Verifica se deve fazer commit baseado em múltiplos critérios."""
    current_total = count_data.get("total", 0)
    last_commit_milestone = count_data.get("last_commit_milestone", 0)
    tokens_since_commit = count_data.get("tokens_since_last_commit", 0)
    
    # Critério 1: Milestone absoluto (comportamento original)
    current_milestone = (current_total // COMMIT_INTERVAL) * COMMIT_INTERVAL
    milestone_commit = current_milestone > last_commit_milestone and current_milestone > 0
    
    # Critério 2: Tokens incrementais (50k tokens desde último commit)
    incremental_commit = tokens_since_commit >= COMMIT_INTERVAL
    
    # Retorna True se qualquer critério for atendido
    if milestone_commit:
        print(f"📊 Commit por milestone: {current_milestone:,}")
        return True, current_milestone, "milestone"
    elif incremental_commit:
        print(f"📈 Commit por incremento: {tokens_since_commit:,} tokens desde último commit")
        # Calcula qual seria o milestone para este commit
        effective_milestone = last_commit_milestone + COMMIT_INTERVAL
        return True, effective_milestone, "incremental"
    
    return False, 0, None

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
            return False, None, None
        
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
                return True, None, None
            else:
                print(f"⚠️  Erro no git commit: {result.stderr}")
                return False, None, None
        
        # Pega o hash do commit criado
        commit_hash = None
        try:
            hash_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True
            )
            if hash_result.returncode == 0:
                commit_hash = hash_result.stdout.strip()[:7]  # Primeiros 7 caracteres
        except:
            pass
        
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
                return False, None, None
        
        print("✅ Commit e push realizados com sucesso!")
        return True, commit_message, commit_hash
        
    except Exception as e:
        print(f"❌ Erro durante operações git: {str(e)}")
        return False, None, None

def main():
    try:
        # Carrega contagem atual
        count_data = load_token_count()
        current_total = count_data.get("total", 0)
        last_commit_milestone = count_data.get("last_commit_milestone", 0)
        tokens_since_commit = count_data.get("tokens_since_last_commit", 0)
        
        # Debug info com emojis
        print(f"🤖 [AUTO-COMMIT] 📊 Total: {current_total:,} | 🏁 Último commit: {last_commit_milestone:,} | 📈 Desde commit: {tokens_since_commit:,}")
        
        # Detecta e ajusta reset se necessário
        reset_detected, adjusted_milestone = detect_and_adjust_reset(count_data)
        if reset_detected:
            save_token_count(count_data)
            last_commit_milestone = adjusted_milestone
        
        # Verifica se deve fazer commit
        should_commit_now, commit_milestone, commit_reason = should_commit(count_data)
        if should_commit_now:
            
            print(f"\n✨ {'='*60} ✨")
            if commit_reason == "milestone":
                print(f"🎯 Milestone de {commit_milestone:,} tokens atingido!")
            else:
                print(f"📈 Incremento de {tokens_since_commit:,} tokens atingido!")
            print(f"🔄 Iniciando auto-commit e push...")
            print(f"✨ {'='*60} ✨")
            
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
            commit_message = generate_commit_message(commit_milestone, changed_files)
            
            # Executa operações git
            success, commit_msg, commit_hash = perform_git_operations(commit_message)
            if success:
                # Atualiza último milestone de commit e adiciona informações detalhadas do commit
                commit_info = {
                    "milestone": commit_milestone,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "timestamp": datetime.now().isoformat(),
                    "message": commit_msg if commit_msg else commit_message,
                    "hash": commit_hash,
                    "files_changed": len(changed_files)
                }
                
                count_data["last_commit_milestone"] = commit_milestone
                count_data["last_commit_info"] = commit_info
                count_data["tokens_since_last_commit"] = 0  # Reseta contador incremental
                
                # Se foi um reset, limpa as informações de reset
                if reset_detected:
                    count_data["last_reset_at"] = None
                    count_data["total_before_reset"] = None
                
                # Mantém histórico dos últimos 5 commits
                if "commit_history" not in count_data:
                    count_data["commit_history"] = []
                
                count_data["commit_history"].insert(0, commit_info)
                count_data["commit_history"] = count_data["commit_history"][:5]  # Mantém apenas últimos 5
                
                save_token_count(count_data)
                
                print(f"\n📊 **Resumo do Commit:**")
                print(f"   🏷️  Hash: {commit_hash if commit_hash else 'N/A'}")
                print(f"   📅 Data: {commit_info['date']} às {commit_info['time']}")
                print(f"   📝 Arquivos modificados: {commit_info['files_changed']}")
                print(f"   🎯 Próximo auto-commit em {commit_milestone + COMMIT_INTERVAL:,} tokens ou após {COMMIT_INTERVAL:,} tokens incrementais")
            else:
                print("⚠️  Auto-commit falhou, será tentado novamente no próximo milestone")
        else:
            next_milestone = ((current_total // COMMIT_INTERVAL) + 1) * COMMIT_INTERVAL
            tokens_needed = next_milestone - current_total
            percentage = (current_total % COMMIT_INTERVAL) / COMMIT_INTERVAL * 100
            progress_bar = "█" * int(percentage / 5) + "░" * (20 - int(percentage / 5))
            
            print(f"\n💫 [AUTO-COMMIT] Status:")
            print(f"   📍 Progresso: [{progress_bar}] {percentage:.1f}%")
            print(f"   🎯 Próximo commit: {next_milestone:,} tokens")
            print(f"   ⏳ Faltam: {tokens_needed:,} tokens")
            
    except Exception as e:
        print(f"❌ Erro crítico no auto-commit: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()