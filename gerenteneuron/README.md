# GerenteNeuron

Chat unificado local para todas as IAs + gerente geral de projetos. Roda no navegador.

## Primeira vez

1. Rode `setup-crypto.py` para instalar a dependência de criptografia no ambiente virtual:
   ```
   python gerenteneuron/setup-crypto.py
   ```
2. Crie o cofre de credenciais:
   ```
   gerenteneuron/.venv/Scripts/python gerenteneuron/setup-vault.py
   ```
3. Adicione suas chaves de API ao cofre:
   ```
   gerenteneuron/.venv/Scripts/python gerenteneuron/mb-vault.py add OPENAI_API_KEY sk-...
   gerenteneuron/.venv/Scripts/python gerenteneuron/mb-vault.py add ANTHROPIC_API_KEY sk-ant-...
   gerenteneuron/.venv/Scripts/python gerenteneuron/mb-vault.py add GEMINI_API_KEY ...
   gerenteneuron/.venv/Scripts/python gerenteneuron/mb-vault.py add MOONSHOT_API_KEY ...
   ```
4. Execute `run.cmd` (Windows) ou `python gerenteneuron/app.py`.
5. O navegador abre e pede a senha mestre do cofre.

## Recuperação de senha

Se esquecer a senha mestre, use a chave de recuperação salva em `gerenteneuron/vault/recovery.key`:

```
gerenteneuron/.venv/Scripts/python gerenteneuron/mb-vault.py reset --recovery <chave>
```

No app, clique em "Esqueci a senha" na tela de login.

## Abas

### Chat IA

- Modo **Auto**: escolhe o modelo mais barato capaz de responder bem.
- Modo **Manual**: você escolhe o provedor/modelo.
- **Reforçar**: reenvia para um modelo maior.
- **👍/👎**: feedback para aprendizado de rotas.

### Gerente

- Recebe pedidos gerais e identifica projeto/skill.
- Projetos ficam em `projetos.json` (não versionado).

## Provedores suportados

- OpenAI (ChatGPT / GPT-5.6 Sol/Terra/Luna)
- Anthropic (Claude Opus/Sonnet)
- Google Gemini
- Moonshot/Kimi
- Ollama local

## Estratégia de roteamento

- Código/debug/refactor → Ollama local primeiro.
- Perguntas simples → modelo pago barato.
- Explanação/decisão → modelo pago equilibrado.
- Arquitetura/auditoria → modelo pago forte.

Detalhes: `referencias/260816_gerenteneuron-estrategias.md`.

## Aprendizado e qualidade

- Feedback salvo em `data/feedback.jsonl`.
- `/api/eval` gera estatísticas e sugestões.
- `aspirar.cmd` roda o `mb-aspirador.py` no código do app.

## Segurança

- `.env`, `projetos.json`, `data/`, `vault/` e `.venv/` estão no `.gitignore`.
- Credenciais ficam criptografadas no cofre local.
