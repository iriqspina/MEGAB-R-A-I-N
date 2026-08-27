# Instalar o megabrain em macOS (Claude Code + Codex)

**Para:** máquina de outra pessoa, macOS/Apple Silicon, agentes **Claude Code CLI**
e **Codex**. Conteúdo levado: **pacote público + `licoes-megabrain.md`**
(decisão de <USUARIO>, 260827). Identidade, `memoria/estado/` e `cerebro/` do
<USUARIO> **não** vão.

**Medido em 260827** contra `_github/export` (v7.5, HEAD `6b81798`, público
`11a2838`): preflight PODE COMEÇAR, `mb-estado.py` gera o JSON e
`mb-check-version.py --projeto` cria projeto do zero — nenhum passo depende de
`.cmd`.

## 0. Por que isso funciona (e o que não funciona)

1. `bin/*.py` é **stdlib pura**, sem caminho `C:\`/`S:\` chumbado, com shebang
   `#!/usr/bin/env python3`. Nada é compilado — o chip (M1…M5) é irrelevante.
2. A trava de arquivo já é cross-platform: `bin/mb_trava.py:165-190` usa
   `msvcrt` no Windows e `fcntl` no POSIX.
3. **Não funciona no mac, e é só a casca:**
   - `scripts/*.cmd` (9 botões) — batch do Windows. Tabela de equivalência na §5.
   - o comando `python` **não existe** no macOS: todo hook/atalho usa `python3`.
   - `bin/mb-obsidian.py` — registra vault por `%APPDATA%` e copia com `clip`
     (linhas 111 e 254). No mac abre o Obsidian pelo fallback `webbrowser`, mas
     o vault entra na mão (`Open folder as vault`).
4. O pacote público **não leva** `MEGABRAIN.md` nem `licoes-megabrain.md` — o
   `mb-check-version.py` avisa e pula. As lições entram no passo §2.4.

## 1. Pré-requisitos

```zsh
python3 --version        # precisa 3.10+ (o código usa `str | None`)
git --version            # se faltar: xcode-select --install
```

Se `python3` não existir ou for antigo: `brew install python@3.12` (ou
instalador do python.org). **Node só é necessário** se ele for usar o plugin
Cowork/Desktop — Claude Code CLI e Codex não precisam.

## 2. Central do amigo

```zsh
git clone https://github.com/iriqspina/MEGAB-R-A-I-N.git ~/megabrain
cd ~/megabrain
echo 'export MEGABRAIN_CENTRAL="$HOME/megabrain"' >> ~/.zshrc
source ~/.zshrc
```

2.1 **Aceite imediato** (os três têm que passar):

```zsh
python3 bin/mb-preflight.py --repo .      # espera: veredito: PODE COMEÇAR
python3 bin/mb-testar.py                  # espera: OK (219 testes em 260827)
python3 bin/mb-estado.py --sem-suite      # espera: escreve dados/estado.json
```

2.2 **Lições** — copiar o arquivo do <USUARIO> para a central dele:

```zsh
cp /caminho/do/pendrive/licoes-megabrain.md ~/megabrain/memoria/nucleo/
python3 bin/mb-indice-licoes.py --indexar # sem a flag ele só lê; o estado.json
                                          # só passa a contar depois de indexar
```

2.3 **Identidade é dele, não sua.** O perfil do <USUARIO> não vem no pacote e não
deve ser copiado. Ele cria o próprio e sincroniza:

```zsh
# ~/megabrain/minha-identidade.md começa com a linha: USUARIO: Nome Dele
python3 bin/mb-sync-memoria.py --source ~/megabrain/minha-identidade.md \
  --target claude --modo conteudo --dir ~/.claude
python3 bin/mb-sync-memoria.py --source ~/megabrain/minha-identidade.md \
  --target codex  --modo conteudo --dir ~/.codex
# opcional, só Claude Code: gera ~/.claude/output-styles/megabrain.md
python3 bin/mb-sync-memoria.py --source ~/megabrain/minha-identidade.md \
  --target claude-style --modo conteudo --dir ~/.claude
```

Alvos e arquivos (`bin/mb-sync-memoria.py:41`): `claude`→`CLAUDE.md` ·
`codex`/`kimi`→`AGENTS.md` · `gemini`→`GEMINI.md` ·
`claude-style`→`output-styles/megabrain.md`.

## 3. Claude Code CLI

3.1 **Skills** — copiar as do protocolo para `~/.claude/skills/`:

```zsh
mkdir -p ~/.claude/skills
for s in megabrain grelhar ingerir leigolanguage traycer; do
  cp -R ~/megabrain/motor/skills/$s ~/.claude/skills/
done
```

3.2 **Hooks** — em `~/.claude/settings.json`, com `python3` e caminho do mac.
**Não copiar o `settings.json` do <USUARIO>**: ele aponta para `S:\...` e chama
`python`; no mac falha em silêncio.

```json
{
  "hooks": {
    "UserPromptSubmit": [
      { "hooks": [
        { "type": "command", "command": "python3 \"$HOME/megabrain/bin/mb-contexto.py\" --agente claude", "timeout": 15 },
        { "type": "command", "command": "python3 \"$HOME/megabrain/bin/mb-observar.py\" --agente claude --evento prompt", "timeout": 10 }
      ] }
    ],
    "PostToolUse": [
      { "matcher": "Edit|Write|NotebookEdit",
        "hooks": [ { "type": "command", "command": "python3 \"$HOME/megabrain/bin/mb-observar.py\" --agente claude --evento arquivo", "timeout": 10 } ] }
    ],
    "Stop": [
      { "hooks": [ { "type": "command", "command": "python3 \"$HOME/megabrain/bin/mb-observar.py\" --agente claude --evento stop", "timeout": 15 } ] }
    ]
  }
}
```

3.3 **Aceite** — abrir o Claude Code, digitar `/megabrain`: a skill responde e o
primeiro prompt vem com o bloco `## Contexto megabrain (hook mb-contexto)`. Sem
esse bloco, o hook não rodou — conferir `python3` no PATH do shell de login.

## 3b. O plugin v1.7.0 é recusado na instalação (corrigido em 1.7.1)

O Cowork recusa o `.plugin` gerado a partir do repo público com
**"Plugin validation failed: Plugin description must be at most 500
characters"** — a `description` do `.claude-plugin/plugin.json` tem **521**.
Vale para qualquer clone: o export publicado (`11a2838`) carrega o manifesto
velho.

**Desbloqueio no mac sem esperar publicação** (corrige o clone e reempacota):

```zsh
cd ~/megabrain   # ou "~/Desktop/Projetos Claude/MEGABRAIN"
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("motor/plugin-megabrain-claude/.claude-plugin/plugin.json")
d = json.loads(p.read_text(encoding="utf-8"))
d["version"] = "1.7.1"
d["description"] = ("Protocolo de execução multi-agente para entregas: gates anti-slop, "
  "grelha de briefing sem teto de perguntas (/grelhar), Duplo Diamante para design, "
  "orçamento de contexto, handoff entre agentes e lições que acumulam entre sessões. "
  "Núcleo sempre-ativo por hook SessionStart, sem editar CLAUDE.md. Inclui /traycer: "
  "a pipeline do Traycer (epic, core flows, tech plan, tickets, execute) rodando sob os gates.")
assert len(d["description"]) <= 500, len(d["description"])
p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("ok:", len(d["description"]), "chars")
PY
python3 bin/mb-build-plugin-claude.py   # sai motor/dist/YYMMDD_megabrain-v1.7.1.plugin
```

Depois do `git pull` (quando a correção estiver publicada), o clone já vem com
1.7.1 e basta rodar o builder. A partir de 260827 o próprio builder reprova
description acima de 500 (`bin/mb-build-plugin-claude.py:47` +
`motor/tests/test_mb_build_plugin_claude.py`).

## 4. Codex

4.1 **Skills**:

```zsh
mkdir -p ~/.codex/skills
cp -R ~/megabrain/motor/skills/codex-megabrain ~/.codex/skills/
cp -R ~/megabrain/motor/skills/megabrain       ~/.codex/skills/
python3 ~/megabrain/bin/mb-build-plugin-codex.py --instalar-direta
python3 ~/megabrain/bin/mb-build-plugin-codex.py --check   # espera: em dia
```

4.2 **Sem hook de contexto.** A instalação Codex de referência (a do <USUARIO>,
260827) tem `~/.codex/skills/` e `AGENTS.md`, e **nenhum** `hooks.json`. No
Codex o Gate 0 é manual: primeira coisa da sessão é
`python3 bin/mb-estado.py --sem-suite` e ler `dados/estado.json`.

## 5. Os 9 botões `.cmd` → comando no mac

| Botão (Windows) | O que faz | Comando no mac |
| --- | --- | --- |
| `01_ABRIR-RELATORIO` | mede e abre o painel | `python3 bin/mb-estado.py --sem-suite && python3 bin/mb-relatorio-vivo.py && open 00_painel/RELATORIO.html` |
| `02_compreender-padroes` | varre padrões | `python3 bin/mb-compreensor.py` |
| `04_novo-projeto` | cria projeto no nível 1 | `python3 bin/mb-check-version.py --projeto ~/projetos/<nome>` |
| `06_sincronizar-identidade` | identidade → agentes | ver §2.3 (um `--target` por pasta; `--target all --dir ~` escreveria na home, errado) |
| `07_instalar-identidade` | idem, por agente | ver §2.3 |
| `08_refresh-plugin-kimi` | plugin Kimi | só se ele usar Kimi — fora deste escopo |
| `09_abrir-kimi-visual` | app local | `python3 motor/gerenteneuron/...` (não verificado no mac) |
| `10_publicar-e-fotografar` | gera pacote público | **não use** — publicação é da central do <USUARIO> |
| `11_enviar-pro-github` | push do público | **não use** — idem |

`04` foi testado em 260827: cria `MEGABRAIN/` (bin, dna, modelos, referencias,
skills) + `cerebro/` e avisa que `MEGABRAIN.md` não existe no pacote público.

## 6. Fronteiras que não são detalhe

1. A central dele é **dele**: `memoria/estado/` (ESTADO, HANDOFF, DECISOES)
   nasce vazia e é preenchida pelos projetos dele.
2. As 217 lições são de processo, mas **citam projetos e clientes do <USUARIO>**
   por nome. Levar foi decisão dele em 260827; não repassar adiante.
3. Se um dia os dois trabalharem no mesmo projeto, a trava é
   `python3 bin/mb-sync.py lock --agente <nome> --escopo <o quê>` — não é
   combinado por WhatsApp.
