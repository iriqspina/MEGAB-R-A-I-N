# HANDOFF — GerenteNeuron

**Data:** 2026-08-16  
**Commit:** `6aacfac` em `_github-repo-local/`  
**Responsável:** Kimi Code  
**Próximo responsável:** outra IA (Claude/Gemini/Kimi) para refinar

---

## O que está entregue

1. **Cofre criptografado local** (`gerenteneuron/vault/`)
   - Módulo `vault.py`: Fernet + PBKDF2, senha mestre, chave de recuperação.
   - CLI `mb-vault.py`: add/get/rm/list/reset.
   - Scripts `setup-crypto.py`, `setup-vault.py`, `unlock-vault.py`.
   - Recuperação de senha via `vault/recovery.key` + endpoint `/api/vault/reset`.

2. **App web unificado** (`app.py`)
   - Chat multi-IA com roteamento local-first.
   - Modo auto (escolhe modelo pelo custo/capacidade) e manual.
   - Botão "Reforçar" para reenviar a um modelo maior.
   - Feedback 👍/👎 salvo em `data/feedback.jsonl`.
   - Aba Gerente: interpreta pedidos gerais e sugere skill/projeto.

3. **Provedores configurados**
   - OpenAI, Anthropic, Gemini, Moonshot/Kimi, Ollama local, Mock.
   - Credenciais vêm do cofre; fallback para `.env` ainda existe em `config.py`.

4. **Infraestrutura megabrain**
   - `aspirar.cmd` aciona `mb-aspirador.py`.
   - `.gitignore` protege `.venv/`, `vault/`, `data/`, `projetos.json`, `.env`.

---

## O que ainda falta (próxima IA)

1. **Testar respostas reais**
   - Criar cofre real na central (`S:\projetos multi i.a\MEGA B R A I N\gerenteneuron\`).
   - Adicionar API keys verdadeiras de cada provedor.
   - Verificar se cada provedor responde e se o roteamento escolhe bem.

2. **Roteamento por preço real**
   - Hoje o roteador usa classe fixa (`quick`/`standard`/`deep`) + prioridade local.
   - Implementar tabela de preços por token e cálculo de custo estimado.

3. **Gerente de projetos ativo**
   - `gerente.py` interpreta intenção, mas ainda não invoca skills automaticamente.
   - Conectar com `/megabrain:rodar`, `/portfolio`, `/rodada`, `/tlou`, etc.

4. **Experiência de primeiro uso**
   - `setup-crypto.py` e `setup-vault.py` exigem path correto; simplificar.
   - Criar instalador único (`instalar.cmd`) que cria `.venv`, instala cryptography e gera cofre.

5. **Atalho de desktop**
   - Usuário pediu atalho para "chegar no site". Criar `.cmd` na área de trabalho que roda `gerenteneuron/run.cmd` e abre o navegador.

---

## Decisões tomadas nesta rodada

- **Fonte da verdade:** central `S:\projetos multi i.a\MEGA B R A I N`; export limpo em `260810_github-export/`; repo local em `_github-repo-local/`.
- **Commit local feito**, push remoto só com autorização explícita do usuário.
- **Dados locais excluídos do repo** (`.venv`, `data/`, `projetos.json`). Eles continuam existindo na central, mas não sobem.
- **Export estava sem `vault.py`:** mantive o `vault.py` do repo local, que é o módulo usado por `app.py` e `mb-vault.py`.
- **`.env.example` ficou como fallback:** o cofre é o método principal, mas `config.py` ainda lê `.env` se existir.

---

## Como rodar agora

1. Abrir terminal na central:
   ```
   cd "S:\projetos multi i.a\MEGA B R A I N\gerenteneuron"
   ```
2. Instalar criptografia (se ainda não tiver):
   ```
   python setup-crypto.py
   ```
3. Criar cofre:
   ```
   .venv\Scripts\python setup-vault.py
   ```
4. Adicionar chaves:
   ```
   .venv\Scripts\python mb-vault.py add OPENAI_API_KEY sk-...
   .venv\Scripts\python mb-vault.py add ANTHROPIC_API_KEY sk-ant-...
   .venv\Scripts\python mb-vault.py add GEMINI_API_KEY ...
   .venv\Scripts\python mb-vault.py add MOONSHOT_API_KEY ...
   ```
5. Rodar:
   ```
   run.cmd
   ```
6. Navegador abre em `http://127.0.0.1:8787`. Digitar senha mestre.

---

## Observações para próxima IA

- Não apague `vault.py` do repo; `app.py` e `mb-vault.py` dependem dele.
- Antes de alterar, rode `git pull` no `_github-repo-local/`.
- Leia `ESTADO.md` e este `HANDOFF.md` na central antes de continuar.
- Sincronize alterações da central para `260810_github-export/` antes de commitar.
- Teste o cofre com senha falsa antes de pedir API keys reais ao usuário.

---

## Próximo passo sugerido

Refinar a instalação e o roteamento: criar um instalador único, testar cada provedor com chaves reais e melhorar a heurística de escolha de modelo com base em preço/tarefa.
