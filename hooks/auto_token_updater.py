#!/usr/bin/env python3
"""
Hook automático para atualizar contador de tokens após cada resposta do Claude.
Este hook é executado automaticamente pelo Claude CLI após cada resposta.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Configurações
TOKEN_COUNT_FILE = Path(__file__).parent.parent / ".token_count.json"
MAX_TOKENS = 100000
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "token_updater_debug.log"
MAX_LOG_ENTRIES = 10

def load_token_count():
    """Carrega contagem atual de tokens."""
    if TOKEN_COUNT_FILE.exists():
        try:
            with open(TOKEN_COUNT_FILE, 'r') as f:
                data = json.load(f)
                if "last_milestone" not in data:
                    data["last_milestone"] = 0
                return data
        except:
            return {"total": 0, "last_update": None, "last_milestone": 0}
    return {"total": 0, "last_update": None, "last_milestone": 0}

def load_log_entries():
    """Carrega entradas de log existentes."""
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, 'r') as f:
                content = f.read()
                # Divide por separador e remove entradas vazias
                entries = [e.strip() for e in content.split("-" * 50) if e.strip()]
                return entries
        except:
            return []
    return []

def save_log_entries(entries):
    """Salva entradas de log mantendo apenas as MAX_LOG_ENTRIES mais recentes."""
    # Garante que o diretório de logs existe
    LOG_DIR.mkdir(exist_ok=True)
    
    # Mantém apenas as MAX_LOG_ENTRIES mais recentes
    entries = entries[:MAX_LOG_ENTRIES]
    
    # Salva no arquivo
    with open(LOG_FILE, 'w') as f:
        for i, entry in enumerate(entries):
            f.write(entry)
            if i < len(entries) - 1:
                f.write("\n" + "-" * 50 + "\n")

def add_log_entry(entry):
    """Adiciona uma nova entrada de log no início (mais recente primeiro)."""
    entries = load_log_entries()
    entries.insert(0, entry)  # Adiciona no início
    save_log_entries(entries)

def save_token_count(data):
    """Salva contagem de tokens."""
    with open(TOKEN_COUNT_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def count_tokens_from_transcript(transcript_path, log_content=None):
    """Conta tokens reais do arquivo de transcrição."""
    try:
        if transcript_path and Path(transcript_path).exists():
            with open(transcript_path, 'r') as f:
                lines = f.readlines()
                
                # Procura por linhas com dados de uso de tokens
                for line in reversed(lines):
                    try:
                        entry = json.loads(line)
                        # Procura por mensagens do assistant que contenham dados de uso
                        if (entry.get('type') == 'assistant' and 
                            'message' in entry and 
                            'usage' in entry.get('message', {})):
                            usage = entry['message']['usage']
                            # Soma todos os tipos de tokens
                            input_tokens = usage.get('input_tokens', 0)
                            output_tokens = usage.get('output_tokens', 0)
                            cache_creation = usage.get('cache_creation_input_tokens', 0)
                            cache_read = usage.get('cache_read_input_tokens', 0)
                            total = input_tokens + output_tokens + cache_creation + cache_read
                            
                            if log_content is not None and total > 0:
                                log_content.append("Tokens reais encontrados:")
                                log_content.append(f"  - input_tokens: {input_tokens}")
                                log_content.append(f"  - output_tokens: {output_tokens}")
                                log_content.append(f"  - cache_creation_input_tokens: {cache_creation}")
                                log_content.append(f"  - cache_read_input_tokens: {cache_read}")
                                log_content.append(f"  - TOTAL: {total}")
                            
                            if total > 0:
                                return total
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        # Log de erro mais específico
        if log_content is not None:
            log_content.append(f"Erro ao ler transcript: {str(e)}")
    return None

def estimate_tokens_from_response(response_data, log_content=None):
    """Estima tokens usados baseado na resposta."""
    # Primeiro tenta obter tokens reais do transcript
    if isinstance(response_data, dict):
        transcript_path = response_data.get("transcript_path")
        real_tokens = count_tokens_from_transcript(transcript_path, log_content)
        if real_tokens is not None:
            return real_tokens
    
    # Se não conseguir tokens reais, estima
    try:
        if isinstance(response_data, dict):
            # Estima baseado no tamanho da resposta
            response_text = str(response_data.get("response", ""))
            user_text = str(response_data.get("prompt", ""))
            
            # Estimativa: ~4 caracteres por token
            response_tokens = len(response_text) // 4
            prompt_tokens = len(user_text) // 4
            
            # Adiciona overhead do sistema
            system_overhead = 200
            
            total = prompt_tokens + response_tokens + system_overhead
            
            # Retorna estimativa sem mínimo fixo
            return total
        else:
            # Fallback para estimativa padrão
            return 250
    except:
        return 250

def main():
    """Processa hook após resposta do Claude."""
    # Lista para coletar conteúdo do log
    log_content = []
    enable_logging = True  # Habilita logging por padrão
    
    try:
        # Lê dados do hook do stdin
        hook_data = json.load(sys.stdin)
        
        # Log para debug
        if enable_logging:
            log_content.append(f"[{datetime.now().isoformat()}] Hook acionado!")
            log_content.append(f"Dados recebidos: {json.dumps(hook_data, indent=2)}")
    except Exception as e:
        # Se não conseguir ler, usa estimativa padrão
        hook_data = {}
        if enable_logging:
            log_content.append(f"[{datetime.now().isoformat()}] Erro ao ler stdin: {str(e)}")
    
    # Carrega contagem atual
    count_data = load_token_count()
    old_total = count_data["total"]
    
    # Estima tokens usados
    tokens_used = estimate_tokens_from_response(hook_data, log_content if enable_logging else None)
    
    # Log da estimativa
    if enable_logging:
        log_content.append(f"Tokens estimados: {tokens_used}")
        log_content.append(f"Total anterior: {old_total}")
    
    # Atualiza contagem
    count_data["total"] += tokens_used
    count_data["last_update"] = datetime.now().isoformat()
    
    # Reseta se atingir 100k
    if count_data["total"] >= MAX_TOKENS:
        print(f"\n🔄 Resetando contador de tokens (atingiu {MAX_TOKENS:,})")
        count_data["total"] = tokens_used
        count_data["last_milestone"] = 0
    
    # Verifica milestones
    current_milestone = (count_data["total"] // 10000) * 10000
    old_milestone = (old_total // 10000) * 10000
    
    if current_milestone > old_milestone and current_milestone > 0:
        print(f"\n🎉 Milestone atingido: {current_milestone:,} tokens!")
        count_data["last_milestone"] = current_milestone
    
    # Salva
    save_token_count(count_data)
    
    # Log final
    if enable_logging:
        log_content.append(f"Novo total: {count_data['total']}")
        log_content.append(f"Arquivo salvo: {TOKEN_COUNT_FILE}")
        
        # Salva log como uma única entrada
        if log_content:
            add_log_entry("\n".join(log_content))
    
    # Sempre mostra o status atual
    progress = count_data["total"] / MAX_TOKENS * 100
    print(f"\n📊 Tokens: {count_data['total']:,} / {MAX_TOKENS:,} ({progress:.1f}%)")
    
    # Mostra próximo milestone se aplicável
    if current_milestone < MAX_TOKENS:
        next_milestone = current_milestone + 10000
        if next_milestone <= MAX_TOKENS:
            tokens_needed = next_milestone - count_data["total"]
            print(f"📍 Próximo milestone: {next_milestone:,} (faltam {tokens_needed:,})")

if __name__ == "__main__":
    main()