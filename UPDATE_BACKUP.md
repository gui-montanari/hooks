# Instruções para Atualizar o Backup

Para atualizar manualmente os arquivos de backup, execute os seguintes comandos:

## Atualizar hooks
```bash
cp -r ~/projects/aiagent/hermespaneladm/hooks/* ./hooks/
```

## Atualizar configurações do Claude
```bash
cp ~/projects/aiagent/hermespaneladm/.claude/settings.json ./.claude/
```

## Atualizar tudo de uma vez
```bash
cp -r ~/projects/aiagent/hermespaneladm/hooks/* ./hooks/ && cp ~/projects/aiagent/hermespaneladm/.claude/settings.json ./.claude/
```

## Atualizar o repositório no GitHub
Após atualizar os arquivos localmente, execute:

```bash
# Adicionar todas as mudanças
git add .

# Fazer commit com mensagem descritiva
git commit -m "Update: backup de hooks e configurações"

# Enviar para o GitHub
git push origin main
```

## Script completo para atualizar backup e GitHub
```bash
# Atualizar arquivos
cp -r ~/projects/aiagent/hermespaneladm/hooks/* ./hooks/ && cp ~/projects/aiagent/hermespaneladm/.claude/settings.json ./.claude/

# Atualizar git
git add .
git commit -m "Update: backup de hooks e configurações - $(date +'%Y-%m-%d %H:%M:%S')"
git push origin main
```