# Test Automation System

Sistema completo de geração e execução automatizada de testes para o HermesPanel.

## Visão Geral

O sistema é composto por dois componentes principais:

1. **Test Generator** - Gera testes automaticamente quando código é criado/modificado
2. **Test Runner & Tracker** - Executa testes e rastreia resultados ao longo do tempo

## Test Generator

### Como Funciona

- Monitora modificações em arquivos Python no diretório `app/`
- Detecta automaticamente:
  - **Endpoints FastAPI** - Gera testes de API
  - **Services** - Gera testes de serviço
  - **Models** - Gera testes de modelo (SQLAlchemy/Pydantic)
- Cria arquivos de teste na estrutura `tests/` espelhando a estrutura do app

### Ativação

O Test Generator é ativado automaticamente através do hook PostToolUse quando arquivos são modificados.

### Exemplo de Uso

Quando você cria um novo endpoint:

```python
# app/aiagente/routes/agent_routes.py
@router.post("/agents")
async def create_agent(agent: AgentCreate):
    ...
```

O sistema automaticamente gera:

```python
# tests/aiagente/routes/test_agent_routes.py
def test_create_agent_success():
    ...
def test_create_agent_unauthorized():
    ...
```

## Test Runner & Tracker

### Comandos Disponíveis

```bash
# Executar todos os testes
python3 hooks/test_runner_tracker.py

# Executar testes de um módulo específico
python3 hooks/test_runner_tracker.py --module aiagente

# Executar apenas testes que falharam
python3 hooks/test_runner_tracker.py --failed

# Executar apenas arquivos não testados
python3 hooks/test_runner_tracker.py --not-tested

# Executar um arquivo específico
python3 hooks/test_runner_tracker.py --file tests/auth/test_services.py

# Ver status dos testes
python3 hooks/test_runner_tracker.py status

# Analisar falhas
python3 hooks/test_runner_tracker.py analyze
```

### Relatórios Gerados

1. **test_results.json** - Resultados detalhados para análise do Claude
2. **test_status.md** - Dashboard visual para humanos

### Rastreamento de Histórico

O sistema mantém histórico de 30 execuções e identifica:
- Testes flaky (falham intermitentemente)
- Regressões recentes
- Tendências de cobertura

## Estrutura de Diretórios

```
hooks/test_automation/
├── analyzers/          # Analisadores de código (AST)
├── generators/         # Geradores de teste
├── trackers/          # Rastreamento de resultados
├── reporters/         # Geração de relatórios
├── templates/         # Templates de teste
├── runner.py          # Executor principal
└── utils/            # Utilitários

.claude/test_tracking/
├── test_results.json  # Últimos resultados
├── test_status.md     # Dashboard visual
└── history/          # Histórico de execuções
```

## Configuração

Configurações em `hooks/test_automation_config.json`:

```json
{
  "test_generator": {
    "enabled": true,
    "auto_generate": true,
    "test_framework": "pytest"
  },
  "test_runner": {
    "coverage": {
      "minimum": 80
    },
    "tracking": {
      "history_size": 30,
      "identify_flaky_threshold": 0.7
    }
  }
}
```

## Exemplos de Uso pelo Claude

### Quando criar novo código:
```
Claude: Vou criar um novo endpoint para buscar agentes. O Test Generator criará automaticamente os testes.
```

### Para verificar status:
```
User: Qual o status dos testes?
Claude: Vou executar o test runner para verificar...
[executa: python3 hooks/test_runner_tracker.py status]
```

### Para corrigir falhas:
```
Claude: Vejo 3 testes falhando. Vou analisar o test_results.json para entender os erros...
```

## Manutenção

- Logs em `logs/test_automation/`
- Limpar histórico antigo: remover arquivos em `.claude/test_tracking/history/`
- Atualizar templates de teste em `templates/`