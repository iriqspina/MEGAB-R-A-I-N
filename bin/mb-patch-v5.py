#!/usr/bin/env python3
"""
mb-patch-v5.py — aplica os patches da v4.9 para a v5.0 na SKILL.md do megabrain.

Cada patch e uma substituicao unica e verificada: se o texto de origem nao
aparecer exatamente uma vez, o script para e diz qual patch falhou. E o
oposto de reescrever o arquivo inteiro - o diff fica auditavel.

Uso:  python bin/mb-patch-v5.py --raiz .  [--conferir]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import mb_utils as u

u.utf8_console()

PATCHES: list[tuple[str, str, str]] = []


def patch(nome: str, antes: str, depois: str) -> None:
    PATCHES.append((nome, antes, depois))


# ---------------------------------------------------------------- P1 gatilhos
patch(
    "P1 · front-matter com gatilhos reais",
    'description: Protocolo de execução multi-agente — gates de entrega anti-slop, Duplo Diamante para projetos de design, roteamento de arquitetura (skill vs script vs subagente), e camada de projeto (fases macro, regras de ouro). Use ao iniciar entrega complexa, passar trabalho de um agente para o outro, ou definir como dois agentes de IA colaboram no mesmo projeto sem pisar um no outro.',
    'description: Protocolo de execução multi-agente — gates de entrega anti-slop, Duplo Diamante para projetos de design, roteamento de arquitetura (skill vs script vs subagente) e camada de projeto (fases macro, regras de ouro). Use quando o usuário digitar /megabrain ou /metaprotocolo, escrever "megabrain" ou "metaclaude", pedir para "rodar no modo completo" ou "caprichar", abrir ou retomar um projeto com ESTADO.md/HANDOFF.md, passar trabalho de um agente para o outro, iniciar entrega complexa (proposta, deck, peça de cliente, relatório, código), pedir para revisar um prompt/brief/workflow, ou perguntar como evitar respostas genéricas de IA.',
)

# ---------------------------------------------------------------- P2 TL;DR
patch(
    "P2 · TL;DR bate com a numeração real dos gates",
    """## TL;DR

`assumir → enquadrar → orçar contexto → gerar → auditar → reparar (1×) → verificar → passar o bastão → registrar`

Os dois gates que ninguém pula: **4 (auditar)** separa entrega de slop. **7
(bastão)** é o que impede o outro agente de começar do zero.

---
""",
    """## TL;DR

`0 assumir → 1 enquadrar → 2 orçar contexto → 3 gerar → 4 auditar (+1 reparo) → 5 verificar e amarrar pontas → 6 passar o bastão → 7 registrar`

Os dois que ninguém pula: **4 (auditar)** separa entrega de slop; **6
(bastão)** impede o outro agente de começar do zero.

## Modo leve × modo completo

Escolha antes de começar e diga qual escolheu — protocolo rodado por reflexo
custa contexto e não melhora nada.

| | Quando | Gates |
|---|---|---|
| **Leve** | resposta única, rascunho interno, exploração, nada sai da conversa | 1 · 4 · 5 |
| **Completo** | vai para cliente, para produção, para o repo, ou outro agente continua | 0 a 7 |
| **Nenhum** | pergunta rápida, papo, dúvida factual | — |

Subir de leve para completo no meio é permitido e barato. Descer não: se o
material já saiu, ele já saiu.

---
""",
)

# ---------------------------------------------------------------- P3 conclusao
patch(
    "P3 · /conclusao-megabrain deixa de ser dependência fantasma",
    """1. **Esgote execução autônoma antes de qualquer pedido ao usuário.** Rode
   `/conclusao-megabrain` e tente resolver sozinho o que falta (automação local,
   ferramentas já logadas, documentação segura de acesso). Só peça ao usuário
   o que realmente depender dele — e peça agrupado, de uma vez só.""",
    """1. **Esgote execução autônoma antes de qualquer pedido ao usuário.** Se a
   skill `/conclusao-megabrain` estiver instalada nesta máquina, rode. Se não
   estiver — ela não faz parte deste pacote —, faça o equivalente na mão:
   liste o que falta, resolva sozinho tudo que for automação local ou
   ferramenta já logada, e leve ao usuário só o que depende dele, agrupado
   numa pergunta só.""",
)

# ---------------------------------------------------------------- P4 gate 5
patch(
    "P4 · Gate 5 volta a conferir o arquivo que rodou, não o que está no repo",
    """## 5. Gate VERIFICAR

- Arquivo abre no app de destino? Formato correto? Convenção de nome
  consistente?
- Links/caminhos existem?
- Números conferem (recalcule, não copie)?
- Datas conferidas contra hoje?
- Contradiz algo já registrado em `DECISOES.md`?

Alto risco (cliente, dinheiro, prazo público): delegue a verificação a um
subagente — ou **ao outro modelo** — passando **só o artefato e a rubrica**,
sem o histórico. Contexto zero é a característica útil, não a limitação.

Rubricas prontas: `referencias/260810_evaluation-gates.md`

---

## 5b. Gate AMARRAR PONTAS

Antes de uma aprovação humana, envio externo, fechamento semanal ou handoff,""",
    """## 5. Gate VERIFICAR

- Arquivo abre no app de destino? Formato correto? Convenção de nome
  consistente com o resto do projeto?
- Links e caminhos existem? **Teste o caminho, não confie na citação.**
- Números conferem (recalcule, não copie)?
- Datas conferidas contra hoje?
- Contradiz algo já registrado em `DECISOES.md`?

**Se o que você auditou é um protocolo, skill, plugin ou script versionado:**
confira o arquivo que o agente **realmente carregou** — tamanho, data e hash —
contra a fonte no repositório. Repo limpo não prova protocolo funcionando; a
cópia instalada pode ter meses de deriva. Este gate existe porque essa falha
já aconteceu com o próprio megabrain.

Alto risco (cliente, dinheiro, prazo público): delegue a verificação a um
subagente — ou **ao outro modelo** — passando **só o artefato e a rubrica**,
sem o histórico. Contexto zero é a característica útil, não a limitação.

Rubricas prontas: `referencias/260810_evaluation-gates.md`

### 5.1 Amarrar pontas — antes de qualquer coisa sair

Antes de uma aprovação humana, envio externo, fechamento semanal ou handoff,""",
)

# ---------------------------------------------------------------- P5 gate 7
patch(
    "P5 · Gate 7 grava direto quando há autorização permanente",
    """Ao fim de tarefa não-trivial, **proponha a entrada já escrita** e peça só
confirmação.""",
    """Ao fim de tarefa não-trivial, escreva a entrada. Se o dono desta instalação
já deu autorização permanente para registrar lições, **grave direto** — não
pergunte "quer que eu registre?", porque a pergunta custa mais que a linha.
Sem autorização declarada, apresente a entrada pronta e peça só o "ok".""",
)

# ---------------------------------------------------------------- P6 erros
patch(
    "P6 · lista de erros ganha a deriva entre cópia instalada e repo",
    """10. **`DECISOES.md` reescrito.** É append-only. Reescrever apaga o registro
    de por que a alternativa foi descartada.""",
    """10. **`DECISOES.md` reescrito.** É append-only. Reescrever apaga o registro
    de por que a alternativa foi descartada.
11. **Auditar o repo e achar que auditou o protocolo.** A cópia que o agente
    carregou pode ser outra, mais velha, com caminhos mortos. Confira hash e
    data antes de julgar — ver Gate 5.
12. **Duas cópias do mesmo arquivo tratadas como duas fontes.** Duplicata
    byte a byte hoje é fork silencioso na primeira edição. Uma fonte, o
    resto é cópia gerada.""",
)

# ---------------------------------------------------------------- P7 referências
patch(
    "P7 · painel entra na tabela de referências",
    "| `260815_pipeline-governanca-aprendizado.md` | Cliente, dinheiro, aprovações, Amarrador, Contraditor, Teammates, momentum ou aprendizado entre projetos |",
    """| `260815_pipeline-governanca-aprendizado.md` | Cliente, dinheiro, aprovações, Amarrador, Contraditor, Teammates, momentum ou aprendizado entre projetos |

Painel de leitura e atalhos (todos os arquivos acima, com hash e botões de
comando): `PAINEL-MEGABRAIN.html`, gerado por `bin/mb-painel.py`. Serve o
humano, não o agente — o agente continua lendo os `.md` sob demanda.""",
)

# ---------------------------------------------------------------- P8 título
patch(
    "P8 · cabeçalho declara versão e o que ele é",
    """# megabrain — protocolo operacional

Protocolo multi-agente e agnóstico de modelo""",
    """# megabrain — protocolo operacional

**v5.0 · 2026-08-16.** Base: v4.9 do repositório. Mudou: numeração de gates
consistente com o TL;DR, modo leve/completo explícito, Gate 5 confere a cópia
que rodou, Gate 7 grava sob autorização permanente, `5b` virou `5.1`.

Protocolo multi-agente e agnóstico de modelo""",
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default=".", help="raiz do megabrain")
    ap.add_argument("--conferir", action="store_true", help="só verifica, não escreve")
    args = ap.parse_args()

    raiz = Path(args.raiz).resolve()
    alvos = [raiz / "SKILL.md", raiz / "skills" / "megabrain" / "SKILL.md"]
    alvos = [a for a in alvos if a.exists()]
    if not alvos:
        print("nenhuma SKILL.md encontrada em", raiz)
        return 1

    falhas = 0
    for alvo in alvos:
        texto = alvo.read_text(encoding="utf-8")
        for nome, antes, depois in PATCHES:
            n = texto.count(antes)
            if n == 1:
                texto = texto.replace(antes, depois, 1)
                print(f"  ok    {nome}")
            elif texto.count(depois) >= 1:
                print(f"  ja    {nome} (já aplicado)")
            else:
                print(f"  FALHA {nome} — trecho de origem apareceu {n}x")
                falhas += 1
        if not args.conferir and not falhas:
            alvo.write_text(texto, encoding="utf-8")
            print(f"escrito: {alvo}")
        print()

    if falhas:
        print(f"{falhas} patch(es) não aplicaram. Nada foi escrito nesses arquivos.")
        return 1

    versao = raiz / "VERSAO.txt"
    if not args.conferir and versao.exists():
        versao.write_text(
            "2026-08-16 · v5.0 — numeração de gates consistente, modo leve/completo,\n"
            "Gate 5 confere a cópia instalada, painel de leitura e atalhos.\n\n"
            "Histórico completo: ver repositório privado da pasta central.\n",
            encoding="utf-8",
        )
        print("VERSAO.txt atualizado para v5.0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
