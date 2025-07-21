# Estrutura de Hooks do Projeto

## 📁 Organização Correta

### 1. Registro de Hooks (onde/quando executar)
**Arquivo**: `.claude/settings.json`
- Apenas define QUANDO e ONDE os hooks são executados
- Não contém configurações internas dos hooks

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 hooks/migration_guardian.py"
          }
        ]
      }
    ]
  }
}
```

### 2. Configurações dos Hooks (como funcionam)
**Local**: Arquivos separados para cada hook

```
hooks/
├── migration_guardian.py           # Script do hook
├── migration_guardian_config.json  # Configurações específicas
├── migration_guardian/            # Módulos do hook
│   ├── detectors/
│   ├── analyzers/
│   └── ...
└── outros_hooks/
```

## 🎯 Princípios

1. **Separação de Responsabilidades**:
   - `settings.json` = Orquestração de hooks
   - `*_config.json` = Comportamento interno

2. **Cada Hook é Independente**:
   - Tem suas próprias configurações
   - Não polui o settings.json global

3. **Facilita Manutenção**:
   - Adicionar/remover hooks é simples
   - Configurações são autocontidas

## ✅ Exemplo Correto

```
.claude/
└── settings.json          # SÓ registro de hooks

hooks/
├── migration_guardian.py
├── migration_guardian_config.json
├── test_generator.py
├── test_generator_config.json
└── ...
```

## ❌ Evitar

- Misturar configurações de hooks no settings.json
- Criar arquivos desnecessários como .claude/hooks.json
- Hardcodar configurações sem possibilidade de customização