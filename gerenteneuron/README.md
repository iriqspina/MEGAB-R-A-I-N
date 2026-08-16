# GerenteNeuron

Chat unificado local para todas as IAs + gerente geral de projetos. Roda no navegador, sem dependências externas.

## Como usar

1. Copie `.env.example` para `.env` e preencha as chaves das APIs que você usa.
2. Execute `run.cmd` (Windows) ou `python app.py` no terminal.
3. O navegador abre automaticamente em `http://127.0.0.1:8787`.

## Abas

### Chat IA

- Modo **Auto**: o GerenteNeuron escolhe o modelo mais barato capaz de responder bem.
- Modo **Manual**: você escolhe o provedor e modelo.
- **Reforçar**: depois de uma resposta, clique para reenviar a mesma mensagem para um modelo maior.
- **👍/👎**: feedback que alimenta o aprendizado de rotas.

### Gerente

- Você manda pedidos gerais como "como está o portfólio?" ou "atualiza o financeiro".
- O GerenteNeuron identifica o projeto, a intenção e diz qual skill invocar.
- Projetos ficam em `projetos.json` (não versionado); use `projetos.json.example` como base.

## Provedores suportados

- OpenAI (ChatGPT / GPT-5.6 Sol/Terra/Luna)
- Anthropic (Claude Opus/Sonnet)
- Google Gemini
- Moonshot/Kimi
- Ollama local (Qwen e outros)
- Mock local (para testes sem API key)

## Estratégia de roteamento

- **Código/debug/refactor** → Ollama local primeiro (economia de tokens).
- **Perguntas simples** → modelo pago barato.
- **Explanação/decisão moderada** → modelo pago equilibrado.
- **Arquitetura/auditoria/decisão crítica** → modelo pago forte.

Detalhes: `referencias/260816_gerenteneuron-estrategias.md`.

## Aprendizado e feedback

- Interações são salvas em `data/feedback.jsonl`.
- Endpoint `/api/eval` mostra estatísticas e sugere ajustes no roteador.
- Use `aspirar.cmd` para rodar o `mb-aspirador.py` no código do GerenteNeuron.

## Segurança

- `.env`, `projetos.json`, `data/` estão no `.gitignore` e nunca sobem para o Git.
- Credenciais ficam apenas no seu computador.
