#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mb-relatorio-projeto.py — gera o "relatório de projeto": um único HTML que
concentra contexto (específico do projeto + geral do megabrain), estado/
handoff, situação viva, próximas ações e dados pendentes.

É o IRMÃO do relatório DNA (bin/mb-relatorio-dna.py):
  - Relatório DNA    -> descreve o PROTOCOLO (genérico, vive em MEGABRAIN/dna/).
  - Relatório de projeto -> descreve a INSTÂNCIA (um projeto específico, ex.:
    Financeiro da Silva, TLOU, Rodada). Vive na raiz do projeto (RELATORIO.html).

Os dois são "direcionados ao usuário e às IAs": frontend humano (dashboard
navegável) + backend IA (JSON-LD, <meta> tags, seção "Para a IA").

Regra de ouro que este script existe para cumprir: **gerado nunca se edita**.
Quando algo mudar, edite o(s) .md fonte e rode este script de novo — nunca
edite o HTML de saída na mão. Os .md fonte não mudam de lugar; este script só
os LÊ como referência para montar o relatório (handoff incluso: ESTADO.md,
HANDOFF.md e DECISOES.md são lidos, nunca movidos).

Uso mínimo:
    python bin/mb-relatorio-projeto.py --projeto "./meu-projeto" --plano "03_plano/PLANO.md"

Uso completo (referência: Financeiro da Silva):
    python bin/mb-relatorio-projeto.py \
      --projeto "<PROJETOS_ROOT>/Financeiro da Silva" \
      --titulo "Financeiro da Silva" \
      --plano "03_plano/PLANO.md" \
      --extra "02_contas_e_assinaturas/ASSINATURAS.md" \
      --extra "04_referencias/taxas-pix-no-credito_2026-08.md" \
      --skill "skills/financeirodasilva/SKILL.md" \
      --tldr "uma frase resumindo a situação agora"

Fontes lidas (todas opcionais, exceto --plano):
    CONTEXT.md                          (auto — contexto específico do domínio)
    ESTADO.md / HANDOFF.md / DECISOES.md (auto, se existirem — handoff/estado
                                          concentrado no relatório SEM mover
                                          os arquivos; se não existirem, o
                                          relatório assume que --plano já
                                          concentra estado+decisões, comum em
                                          projeto nível 1-2)
    --plano PATH        arquivo "vivo" principal (situação, estratégia) — obrigatório
    --extra PATH (N×)   arquivos adicionais; cada um vira uma seção própria
    todos os .md do projeto (padrão)  descobertos e renderizados automaticamente;
                          use --sem-todos-md só quando houver motivo para omitir
                          documentação de domínio. MEGABRAIN/, .git/, caches e
                          dependências nunca entram por acidente.
    --skill PATH         SKILL.md do router do projeto — extrai "Próximos passos"
    --tldr TEXTO          uma frase; se omitido, usa o 1º parágrafo do --plano
    --megabrain-central PATH  para puxar um resumo do contexto GERAL (MEGABRAIN.md
                          da central); se não encontrar, usa um resumo genérico embutido
"""

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
from urllib.parse import urlparse
from pathlib import Path

import mb_utils as u

u.utf8_console()

DEFAULT_OUT_NAME = "RELATORIO.html"

RESOLUCAO_TITULOS_PADRAO = [
    "resolução", "resolucao", "plano de ação", "plano de acao",
    "estratégia", "estrategia", "alternativas", "caminhos pra resolver",
    "caminhos para resolver", "o que fazer",
]

# heading dedicado a UM plano de ação óbvio e sequencial — diferente de
# "resolução" (que pode ter várias alternativas concorrentes), isto aqui é
# "faça isto, depois isto". Vira um card em destaque logo abaixo do TL;DR.
ACAO_IMEDIATA_TITULOS_PADRAO = [
    "ação imediata", "acao imediata", "o que fazer agora",
    "próximo passo agora", "proximo passo agora", "faça isto",
    "faca isto", "plano de ação imediato", "plano de acao imediato",
]

GENERIC_MEGABRAIN_RESUMO = (
    "Protocolo de execução multi-agente e anti-slop: estado -> grelhar -> spec -> "
    "tickets -> implementar -> validar -> publicar -> registrar, com gates de "
    "entrega (enquadrar, orçar contexto, gerar, auditar, reparar, verificar, "
    "passar o bastão, aprender) sobre cada peça não-trivial."
)


# --------------------------------------------------------------------------
# Leitura de arquivos
# --------------------------------------------------------------------------

def ler(path: Path) -> str:
    if not path or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def primeiro_paragrafo(texto: str) -> str:
    for bloco in re.split(r"\n\s*\n", texto.strip()):
        linha = bloco.strip().lstrip("#").strip()
        if linha and not linha.startswith("|"):
            # remove marcações simples pra virar frase corrida
            linha = re.sub(r"\*\*(.+?)\*\*", r"\1", linha)
            linha = re.sub(r"`(.+?)`", r"\1", linha)
            return linha
    return ""


def descobrir_markdowns(projeto: Path, ignorar_relativos: set[str]) -> list[tuple[str, str]]:
    """Lê toda a documentação Markdown que pertence à instância do projeto.

    O relatório é o ponto único de leitura para humano e IA. Portanto a
    descoberta é padrão, não uma lista manual fácil de esquecer. A cópia do
    protocolo e diretórios técnicos continuam fora: eles são infraestrutura,
    não informação específica da instância que o relatório descreve.
    """
    diretorios_ignorados = {".git", "megabrain", "node_modules", "__pycache__", ".mb-aspirador"}
    encontrados = []
    for caminho in sorted(projeto.rglob("*.md"), key=lambda item: str(item).casefold()):
        relativo = caminho.relative_to(projeto).as_posix()
        partes = {parte.casefold() for parte in caminho.relative_to(projeto).parts}
        if partes & diretorios_ignorados or relativo.casefold() in ignorar_relativos:
            continue
        texto = ler(caminho)
        if texto:
            encontrados.append((relativo, texto))
    return encontrados


def id_extra(relativo: str) -> str:
    """Cria id estável mesmo quando duas pastas têm README.md."""
    base = Path(relativo).with_suffix("").as_posix().casefold()
    return "extra-" + re.sub(r"[^a-z0-9]+", "-", base).strip("-")


# --------------------------------------------------------------------------
# Conversor markdown -> HTML (subconjunto suficiente para os .md do projeto)
# --------------------------------------------------------------------------

def _inline(texto: str) -> str:
    texto = html.escape(texto)
    texto = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", texto)
    texto = re.sub(r"`([^`]+?)`", r"<code>\1</code>", texto)
    texto = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', texto)
    return texto


def markdown_para_html(texto: str, pendencias: list, fonte_nome: str) -> str:
    """Converte um subconjunto de markdown (headers, tabelas, listas,
    checkboxes, negrito, código, links, citação, hr) em HTML. Também coleta
    linhas '- [ ]' / '- [x]' em `pendencias` (lista compartilhada), marcadas
    com a fonte."""
    linhas = texto.replace("\r\n", "\n").split("\n")
    out = []
    i = 0
    n = len(linhas)
    in_ul = False
    in_ol = False

    def fechar_lista():
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    def consumir_continuacao(j):
        """A partir do índice j, junta linhas indentadas de continuação de um
        item de lista (texto que só quebrou por largura, não item novo) até
        achar linha vazia, heading, tabela, citação, hr ou novo item de
        lista. Devolve (texto_extra, novo_j)."""
        partes = []
        while j < n:
            bruta = linhas[j]
            s2 = bruta.strip()
            if not s2:
                break
            if not bruta[:1].isspace():
                break  # sem indentação -> não é continuação, é parágrafo novo
            if re.match(r"^(#{1,4}\s|[-*]\s|\d+\.\s|\||>|-{3,}\s*$)", s2):
                break  # item de lista novo (ou aninhado) / heading / tabela / hr
            partes.append(s2)
            j += 1
        return (" " + " ".join(partes) if partes else ""), j

    while i < n:
        linha = linhas[i]
        s = linha.strip()

        # tabela: linha com '|' seguida de linha separadora '---|---'
        if s.startswith("|") and i + 1 < n and re.match(r"^\|?[\s:|-]+\|?$", linhas[i + 1].strip()):
            fechar_lista()
            cabecalho = [c.strip() for c in s.strip("|").split("|")]
            out.append('<div class="tbl-wrap"><table><thead><tr>')
            for c in cabecalho:
                out.append(f"<th>{_inline(c)}</th>")
            out.append("</tr></thead><tbody>")
            i += 2
            while i < n and linhas[i].strip().startswith("|"):
                celulas = [c.strip() for c in linhas[i].strip().strip("|").split("|")]
                out.append("<tr>")
                for c in celulas:
                    out.append(f"<td>{_inline(c)}</td>")
                out.append("</tr>")
                i += 1
            out.append("</tbody></table></div>")
            continue

        # headings
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            fechar_lista()
            nivel = min(len(m.group(1)) + 2, 6)  # relatório começa em h2
            out.append(f"<h{nivel}>{_inline(m.group(2))}</h{nivel}>")
            i += 1
            continue

        # hr (mas não confundir com separador de tabela, já tratado acima)
        if re.match(r"^-{3,}\s*$", s):
            fechar_lista()
            out.append("<hr>")
            i += 1
            continue

        # checkbox
        m = re.match(r"^[-*]\s+\[([ xX])\]\s+(.*)$", s)
        if m:
            if not in_ul:
                out.append('<ul class="chk">')
                in_ul = True
            feito = m.group(2 - 1) if False else m.group(1).lower() == "x"
            i += 1
            extra, i = consumir_continuacao(i)
            texto_item = m.group(2) + extra
            pendencias.append({"texto": texto_item, "feito": feito, "fonte": fonte_nome})
            marca = "☑" if feito else "☐"
            cls = "done" if feito else "open"
            out.append(f'<li class="{cls}"><span class="mk">{marca}</span> {_inline(texto_item)}</li>')
            continue

        # lista simples
        m = re.match(r"^[-*]\s+(.*)$", s)
        if m:
            if in_ol:  # não aninha ul dentro de ol — fecha o outro tipo antes
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            i += 1
            extra, i = consumir_continuacao(i)
            out.append(f"<li>{_inline(m.group(1) + extra)}</li>")
            continue

        # lista numerada ("1. texto")
        m = re.match(r"^\d+\.\s+(.*)$", s)
        if m:
            if in_ul:  # não aninha ol dentro de ul — fecha o outro tipo antes
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            i += 1
            extra, i = consumir_continuacao(i)
            out.append(f"<li>{_inline(m.group(1) + extra)}</li>")
            continue

        # citação
        if s.startswith(">"):
            fechar_lista()
            out.append(f"<blockquote>{_inline(s.lstrip('> ').strip())}</blockquote>")
            i += 1
            continue

        # linha em branco
        if not s:
            fechar_lista()
            i += 1
            continue

        # parágrafo (junta linhas seguidas até próxima linha especial/vazia)
        fechar_lista()
        buf = [s]
        i += 1
        while i < n and linhas[i].strip() and not re.match(
            r"^(#{1,4}\s|[-*]\s|\d+\.\s|\||>|-{3,}\s*$)", linhas[i].strip()
        ):
            buf.append(linhas[i].strip())
            i += 1
        out.append(f"<p>{_inline(' '.join(buf))}</p>")

    fechar_lista()
    return "\n".join(out)


def extrair_secoes_resolucao(texto: str, fonte_nome: str, titulos_candidatos) -> list:
    """Varre um markdown por headings (##/###) cujo texto bate com alguma
    palavra-chave de 'resolução' (plano de ação, estratégia, alternativas...)
    e devolve blocos [(titulo, corpo_markdown, fonte)] — cada bloco vai até o
    próximo heading de nível igual ou menor. Não move nada do arquivo fonte,
    só copia o trecho pro relatório em destaque."""
    linhas = texto.replace("\r\n", "\n").split("\n")
    candidatos_norm = [c.lower() for c in titulos_candidatos]
    blocos = []
    i = 0
    n = len(linhas)
    while i < n:
        m = re.match(r"^(#{2,4})\s+(.*)$", linhas[i].strip())  # nunca casar o H1 (título do doc)
        if m:
            nivel = len(m.group(1))
            titulo = m.group(2).strip()
            titulo_norm = titulo.lower()
            if any(c in titulo_norm for c in candidatos_norm):
                corpo = []
                j = i + 1
                while j < n:
                    m2 = re.match(r"^(#{1,4})\s+", linhas[j].strip())
                    if m2 and len(m2.group(1)) <= nivel:
                        break
                    corpo.append(linhas[j])
                    j += 1
                blocos.append((titulo, "\n".join(corpo).strip(), fonte_nome))
                i = j
                continue
        i += 1
    return blocos


# --------------------------------------------------------------------------
# CSS / JS (mesma linguagem visual já usada nos relatórios do <USUARIO>)
# --------------------------------------------------------------------------

def css(tema: str = "padrao") -> str:
    base = """
:root{--ink:#0E1B1F;--ink2:#4A6169;--ink3:#7C99A1;--edge:#DCE7EA;--surf:#fff;--bg:#EAF1F3;
  --ok:#1F7A4C;--warn:#B8791F;--bad:#B34A31;--acc:#0B6C7A;--m:ui-monospace,"SF Mono",Consolas,monospace}
*{box-sizing:border-box;margin:0}
body{background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;
  padding:40px 22px 80px}
.wrap{max-width:960px;margin:0 auto}
h1{font-size:26px;letter-spacing:-.03em}
.sub{font-family:var(--m);font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);margin-top:6px}
.tldr{margin:26px 0;padding:20px 22px;border-radius:18px;background:var(--surf);border-left:8px solid var(--ok);
  box-shadow:0 10px 30px rgba(11,60,70,.08);font-size:18px;line-height:1.45}
.tldr.atencao{border-left-color:var(--warn)} .tldr.ruim{border-left-color:var(--bad)}
.hero-acao{margin:0 0 30px;padding:22px 26px 26px;border-radius:20px;background:#0E1B1F;color:#EAF1F3;
  box-shadow:0 14px 34px rgba(11,60,70,.18)}
.hero-acao h2{color:#7dd3fc;font-size:13px;letter-spacing:.14em;margin:0 0 4px}
.hero-acao .section-file{color:#7C99A1}
.hero-acao ol{counter-reset:acao;list-style:none;margin:12px 0 0;padding:0}
.hero-acao ol>li{counter-increment:acao;position:relative;padding:10px 0 10px 42px;
  border-bottom:1px solid rgba(255,255,255,.1);font-size:16px;line-height:1.45}
.hero-acao ol>li:last-child{border-bottom:0}
.hero-acao ol>li::before{content:counter(acao);position:absolute;left:0;top:9px;width:28px;height:28px;
  border-radius:999px;background:#7dd3fc;color:#0E1B1F;font-family:var(--m);font-weight:700;font-size:13px;
  display:flex;align-items:center;justify-content:center}
.hero-acao strong{color:#fff}
.hero-acao code{background:rgba(255,255,255,.1);color:#7dd3fc}
.hero-acao p{color:#DCE7EA}
.acoes-rapidas{display:flex;gap:8px;flex-wrap:wrap;margin-top:18px}
.acao-btn{display:inline-flex;align-items:center;min-height:38px;padding:8px 14px;border-radius:999px;
  background:#7dd3fc;color:#0E1B1F;font-family:var(--m);font-size:11px;font-weight:700;
  letter-spacing:.05em;text-transform:uppercase;text-decoration:none}
.acao-btn:hover{background:#fff;color:#0E1B1F}
nav{position:sticky;top:0;z-index:40;background:rgba(234,241,243,.92);backdrop-filter:blur(6px);
  display:flex;gap:6px;flex-wrap:wrap;padding:10px 0;margin:0 0 8px}
nav a{font-family:var(--m);font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink2);
  background:var(--surf);border:1px solid var(--edge);border-radius:999px;padding:6px 12px;text-decoration:none}
nav a:hover{color:var(--acc);border-color:var(--acc)}
h2{font-size:12px;font-family:var(--m);letter-spacing:.16em;text-transform:uppercase;color:var(--ink3);
  margin:34px 0 12px;scroll-margin-top:52px}
h3{font-size:15px;color:var(--acc);margin:18px 0 8px}
h4{font-size:13px;color:var(--ink2);margin:14px 0 6px}
p{margin:8px 0;color:var(--ink2)}
.tbl-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;background:var(--surf);border-radius:16px;overflow:hidden;
  box-shadow:0 8px 24px rgba(11,60,70,.06);margin:10px 0}
th{text-align:left;font-family:var(--m);font-size:11px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--ink3);font-weight:500;vertical-align:top;padding:12px 16px;border-bottom:1px solid var(--edge)}
td{padding:12px 16px;border-bottom:1px solid var(--edge);vertical-align:top}
tr:last-child td{border-bottom:0}
ul,ol{margin:8px 0 8px 20px;color:var(--ink2)} li{margin:4px 0}
ul.chk{list-style:none;margin-left:0}
ul.chk li{display:flex;gap:8px;align-items:flex-start}
ul.chk li.done{color:var(--ink3);text-decoration:line-through}
ul.chk .mk{font-family:var(--m)}
blockquote{border-left:3px solid var(--edge);padding:4px 14px;color:var(--ink3);margin:10px 0}
code{font-family:var(--m);font-size:13px;color:var(--acc);background:#F4F8F9;padding:1px 5px;border-radius:5px}
a{color:var(--acc)}
hr{border:0;border-top:1px solid var(--edge);margin:18px 0}
.card-ai{background:#0E1B1F;color:#DCE7EA;border-radius:16px;padding:18px 22px;margin:10px 0}
.card-ai code{background:rgba(255,255,255,.08);color:#7dd3fc}
.pend{display:flex;gap:8px;align-items:flex-start;padding:8px 0;border-bottom:1px solid var(--edge)}
.pend:last-child{border-bottom:0}
.pend .src{font-family:var(--m);font-size:10px;color:var(--ink3);white-space:nowrap}
.section-file{font-family:var(--m);font-size:11px;color:var(--ink3);margin:-6px 0 10px}
.di{background:var(--surf);border-radius:16px;padding:6px 22px;box-shadow:0 8px 24px rgba(11,60,70,.06)}
.di div{padding:14px 0;border-bottom:1px solid var(--edge)} .di div:last-child{border-bottom:0}
.cp{font-family:var(--m);font-size:10px;letter-spacing:.08em;text-transform:uppercase;cursor:pointer;
  border:1px solid var(--edge);background:#F4F8F9;color:var(--acc);border-radius:999px;padding:4px 12px;margin-left:10px}
.cp:hover{background:#E2EDEF}
footer{margin-top:40px;color:var(--ink2);font-size:14px;line-height:1.7}
footer code{background:var(--surf);padding:3px 8px;border-radius:7px}
details{background:var(--surf);border-radius:14px;padding:2px 18px;margin:10px 0;box-shadow:0 6px 18px rgba(11,60,70,.05)}
summary{cursor:pointer;font-family:var(--m);font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--acc);padding:12px 0}
"""
    return base + (css_megabrain() if tema == "megabrain" else "")


def css_megabrain() -> str:
    """Tema editorial do relatório institucional MEGABRAIN/MIMDE.

    Mantém o HTML semântico genérico do relatório de projeto, mas aplica a
    mesma leitura operacional: rail de navegação, sinal, hierarquia curta e
    superfícies planas. O tema é opt-in para não mudar relatórios existentes.
    """
    return """
:root{--paper:#f2efe7;--paper-high:#fffdf8;--ink:#171716;--ink2:#55544f;--ink3:#68665f;
  --edge:#cec9bc;--acc:#a63025;--bg:#f2efe7;--ok:#23613e;--warn:#7b5111;--bad:#a63025;
  --m:ui-monospace,"SFMono-Regular",Consolas,"Liberation Mono",monospace}
body{padding:0;background:var(--paper);font:16px/1.55 Arial,Helvetica,sans-serif}
.wrap{max-width:none;min-height:100svh;margin:0 0 0 15rem;padding:4.5rem clamp(1rem,4vw,3rem) 5rem;
  background:var(--paper);border-left:1px solid #000}
.wrap>h1{max-width:15ch;margin:0 0 .35rem;font-size:clamp(2.6rem,6vw,5.4rem);line-height:.92;letter-spacing:-.075em}
.sub{margin:0 0 2rem;color:var(--ink3);font-size:.67rem;letter-spacing:.1em}
.tldr{max-width:82rem;margin:0 0 1.5rem;padding:1.2rem 1.45rem;border:1px solid var(--edge);border-left:8px solid var(--warn);
  border-radius:0;box-shadow:0 16px 34px rgb(23 23 22 / 8%);background:var(--paper-high);font-size:clamp(1rem,1.6vw,1.2rem)}
.hero-acao{max-width:82rem;margin:0 0 2rem;padding:1.4rem;border-radius:0;background:var(--ink);box-shadow:none}
.hero-acao h2{margin:0 0 .4rem;color:#ffb5aa;font-size:.72rem}.hero-acao .section-file{color:#bdb8ae}
.acoes-rapidas{margin-top:1rem}.acao-btn{border-radius:0;background:var(--paper-high);color:var(--ink)}
nav{position:fixed;z-index:40;inset:0 auto 0 0;display:flex;flex-direction:column;flex-wrap:nowrap;gap:0;
  width:15rem;margin:0;padding:8.8rem 1rem 1.4rem;background:var(--ink);border:0;border-right:1px solid #000;
  overflow-y:auto;backdrop-filter:none}
nav::before{content:"CURRÍCULO\\A Acompanhamento do projeto";position:absolute;inset:1.45rem 1.5rem auto;
  padding-bottom:1.35rem;border-bottom:1px solid rgb(255 255 255 / 18%);white-space:pre-line;color:var(--paper-high);
  font:800 1.45rem/.98 Arial,Helvetica,sans-serif;letter-spacing:-.06em}
nav::after{content:"Local · relatório vivo\\A Fontes Markdown consolidadas";margin-top:auto;padding-top:1.5rem;white-space:pre-line;
  color:#8f8a82;font:.62rem/1.55 var(--m)}
nav a{display:grid;grid-template-columns:2rem 1fr;align-items:center;min-height:2.55rem;padding:0;border:0;border-radius:0;
  background:transparent;color:#c9c4bb;font:.68rem/1.2 var(--m);letter-spacing:.06em;text-decoration:none}
nav a::before{content:"→";color:#77736c}nav a:hover{padding-left:.35rem;background:var(--paper-high);color:var(--ink)}
nav a:hover::before{color:var(--acc)}
section{max-width:82rem;margin:1px 0 0;padding:1.4rem 1.5rem;border:1px solid var(--edge);background:var(--paper-high)}
section:first-of-type{margin-top:0}h2{margin:0 0 1rem;color:var(--ink);font:800 clamp(1.3rem,3vw,2.25rem)/1 Arial,Helvetica,sans-serif;
  letter-spacing:-.055em;text-transform:none;scroll-margin-top:1rem}h3{color:var(--acc)}
p{color:var(--ink2)}.section-file{margin:-.55rem 0 1rem;color:var(--ink3)}
table,.di,details{border-radius:0;box-shadow:none;border:1px solid var(--edge)}.card-ai{border-radius:0;background:var(--ink)}
.cp{border-radius:0;color:var(--ink);background:var(--paper);border-color:var(--edge)}code{border-radius:0;color:var(--acc);background:#f3eee5}
footer{max-width:82rem;padding:1.4rem;border:1px solid var(--edge);border-top:0;background:var(--paper-high)}
@media(max-width:62rem){.wrap{margin:0;padding:4.6rem 1rem 3rem;border-left:0}nav{inset:0 0 auto;display:flex;flex-direction:row;
  width:100%;height:3.75rem;padding:.55rem .7rem;overflow-x:auto;overflow-y:hidden}nav::before,nav::after{display:none}nav a{display:flex;min-width:max-content;padding:0 .6rem;color:#c9c4bb}.wrap>h1{font-size:clamp(2.4rem,12vw,4.5rem)}}
"""


def js() -> str:
    return """
function cp(btn,t){
  var txt='"'+t+'"';
  var ok=function(){var o=btn.textContent;btn.textContent='copiado \u2713';setTimeout(function(){btn.textContent=o;},1400);};
  function legacy(){
    var ta=document.createElement('textarea');ta.value=txt;ta.style.position='fixed';ta.style.opacity='0';
    document.body.appendChild(ta);ta.select();
    try{document.execCommand('copy');ok();}catch(e){btn.textContent=t;}
    document.body.removeChild(ta);
  }
  if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(txt).then(ok,legacy);}else{legacy();}
}
"""


# --------------------------------------------------------------------------
# Montagem do relatório
# --------------------------------------------------------------------------

def secao(id_, titulo, corpo_html, arquivo_fonte=None):
    tag = f'<div class="section-file">fonte: <code>{html.escape(arquivo_fonte)}</code></div>' if arquivo_fonte else ""
    return f'<section id="{id_}"><h2>{html.escape(titulo)}</h2>{tag}{corpo_html}</section>'


def parse_acoes(acoes_brutas: list[str]) -> list[tuple[str, str, bool]]:
    """Valida ações passadas como ``Rótulo|URL``.

    Só aceita links HTTPS externos ou âncoras internas do próprio relatório.
    Assim, o relatório pode ter botões úteis sem virar um vetor de javascript,
    data URL ou execução local do sistema operacional.
    """
    acoes = []
    for bruta in acoes_brutas:
        rotulo, separador, href = bruta.partition("|")
        rotulo = rotulo.strip()
        href = href.strip()
        if not separador or not rotulo or not href:
            print(f"AVISO: --acao ignorada (use Rótulo|URL): {bruta}")
            continue
        interna = href.startswith("#") and re.fullmatch(r"#[A-Za-z0-9_-]+", href)
        destino = urlparse(href)
        externa = destino.scheme == "https" and bool(destino.netloc)
        if not (interna or externa):
            print(f"AVISO: --acao ignorada (use HTTPS ou #ancora): {bruta}")
            continue
        acoes.append((rotulo, href, externa))
    return acoes


def gerar(args, data_iso: str) -> str:
    projeto = Path(args.projeto).resolve()
    pendencias = []
    acoes = parse_acoes(args.acao or [])

    # --- contexto específico ---
    context_path = projeto / (args.context or "CONTEXT.md")
    context_txt = ler(context_path)

    # --- contexto geral (MEGABRAIN central, se acessível) ---
    resumo_geral = GENERIC_MEGABRAIN_RESUMO
    central_link = None
    if args.megabrain_central:
        central = Path(args.megabrain_central)
        mb_md = ler(central / "MEGABRAIN.md")
        if mb_md:
            resumo_geral = primeiro_paragrafo(mb_md) or resumo_geral
            central_link = str(central)

    # --- estado / handoff (opcional) ---
    estado_txt = ler(projeto / "ESTADO.md")
    handoff_txt = ler(projeto / "HANDOFF.md")
    decisoes_txt = ler(projeto / "DECISOES.md")
    tem_handoff_dedicado = bool(estado_txt or handoff_txt or decisoes_txt)

    # --- plano vivo (obrigatório) ---
    plano_rel = args.plano
    plano_path = projeto / plano_rel
    plano_txt = ler(plano_path)
    if not plano_txt:
        print(f"AVISO: --plano não encontrado ou vazio: {plano_path}")

    # --- extras declarados ---
    extras = []
    for rel in (args.extra or []):
        p = projeto / rel
        t = ler(p)
        if t:
            extras.append((rel, t))
        else:
            print(f"AVISO: --extra não encontrado ou vazio: {p}")

    # --- skill router (próximos passos) ---
    skill_txt = ""
    skill_rel = args.skill
    if skill_rel:
        skill_txt = ler(projeto / skill_rel)

    # --- demais fontes Markdown da instância ---
    # O padrão precisa ser abrangente: documento criado depois não pode ficar
    # invisível só porque alguém esqueceu de acrescentar outro --extra.
    ignorar_auto = {
        str(args.context or "CONTEXT.md").replace("\\", "/").casefold(),
        str(plano_rel).replace("\\", "/").casefold(),
        "estado.md", "handoff.md", "decisoes.md",
        *(rel.replace("\\", "/").casefold() for rel, _ in extras),
    }
    if skill_rel:
        ignorar_auto.add(skill_rel.replace("\\", "/").casefold())
    markdowns_auto = [] if args.sem_todos_md else descobrir_markdowns(projeto, ignorar_auto)

    # --- tldr ---
    tldr = args.tldr or primeiro_paragrafo(plano_txt) or "sem TL;DR definido — passe --tldr ou verifique o --plano"
    tldr_classe = args.tldr_classe if args.tldr_classe in ("ok", "atencao", "ruim") else "atencao"

    # --- render das seções (markdown -> html), coletando pendências ---
    html_context = markdown_para_html(context_txt, pendencias, str(args.context or "CONTEXT.md")) if context_txt else ""
    html_plano = markdown_para_html(plano_txt, pendencias, plano_rel) if plano_txt else "<p>(vazio)</p>"
    html_estado = markdown_para_html(estado_txt, pendencias, "ESTADO.md") if estado_txt else ""
    html_handoff = markdown_para_html(handoff_txt, pendencias, "HANDOFF.md") if handoff_txt else ""
    html_decisoes = markdown_para_html(decisoes_txt, pendencias, "DECISOES.md") if decisoes_txt else ""
    html_extras = [(rel, markdown_para_html(t, pendencias, rel)) for rel, t in extras]
    html_markdowns_auto = [
        (rel, markdown_para_html(t, pendencias, rel)) for rel, t in markdowns_auto
    ]

    # próximos passos: tenta achar a tabela "Próximos passos" dentro do skill_txt inteiro
    html_skill = ""
    if skill_txt:
        html_skill = markdown_para_html(skill_txt, [], skill_rel)  # não conta pendência do próprio router

    pendentes = [p for p in pendencias if not p["feito"]]
    feitas = [p for p in pendencias if p["feito"]]

    # --- resolução: alternativas pra resolver a situação pendente (não é     ---
    # --- "caminhos" de arquivo — é o que fazer). Varre plano + extras.       ---
    resolucao_blocos = []
    if not args.sem_resolucao:
        titulos = list(RESOLUCAO_TITULOS_PADRAO) + list(args.resolucao_titulo or [])
        if plano_txt:
            resolucao_blocos += extrair_secoes_resolucao(plano_txt, plano_rel, titulos)
        for rel, t in extras:
            resolucao_blocos += extrair_secoes_resolucao(t, rel, titulos)
        for rel, t in markdowns_auto:
            resolucao_blocos += extrair_secoes_resolucao(t, rel, titulos)

    # --- ação imediata: UM heading dedicado no --plano vira card em         ---
    # --- destaque logo abaixo do TL;DR — sequência óbvia, não alternativas. ---
    acao_imediata_html = ""
    acao_imediata_fonte = None
    if not args.sem_acao_imediata and plano_txt:
        titulos_acao = list(ACAO_IMEDIATA_TITULOS_PADRAO) + list(args.acao_imediata_titulo or [])
        acao_blocos = extrair_secoes_resolucao(plano_txt, plano_rel, titulos_acao)
        if acao_blocos:
            _, corpo_md, fonte = acao_blocos[0]  # só o primeiro — um card, não vários
            acao_imediata_html = markdown_para_html(corpo_md, [], fonte)
            acao_imediata_fonte = fonte

    # --- seções HTML ---
    secoes = []

    secoes.append(secao("contexto", "Contexto específico do projeto", html_context or "<p>sem CONTEXT.md</p>",
                         str(args.context or "CONTEXT.md")) if html_context else "")

    secoes.append(f"""
    <section id="geral"><h2>Contexto geral (megabrain)</h2>
      <p>{html.escape(resumo_geral)}</p>
      {'<p class="section-file">fonte: <code>' + html.escape(central_link) + '/MEGABRAIN.md</code></p>' if central_link else '<p class="section-file">resumo genérico embutido — passe --megabrain-central para puxar da fonte real</p>'}
    </section>""")

    if tem_handoff_dedicado:
        corpo = (html_estado + html_handoff + html_decisoes) or "<p>sem conteúdo</p>"
        secoes.append(secao("handoff", "Estado e handoff", corpo, None))
    else:
        secoes.append(f"""
        <section id="handoff"><h2>Estado e handoff</h2>
          <p>Este projeto não tem <code>ESTADO.md</code>/<code>HANDOFF.md</code>/<code>DECISOES.md</code>
          dedicados (nível 1-2 de adoção) — <code>{html.escape(plano_rel)}</code> concentra situação,
          decisões e diário. Ver seção "Situação viva" abaixo.</p>
        </section>""")

    if resolucao_blocos:
        partes = []
        for titulo, corpo_md, fonte in resolucao_blocos:
            corpo_html = markdown_para_html(corpo_md, [], fonte)  # não conta pendência 2x
            partes.append(
                f'<h3>{_inline(titulo)}</h3>'
                f'<div class="section-file">fonte: <code>{html.escape(fonte)}</code></div>'
                f'{corpo_html}'
            )
        secoes.append(secao(
            "resolucao", "Resolução — alternativas pra resolver agora",
            "".join(partes) + '<p class="section-file">também aparece por inteiro em "Situação viva" — '
            "aqui é só o recorte em destaque.</p>",
            None,
        ))

    secoes.append(secao("situacao", "Situação viva", html_plano, plano_rel))

    for rel, h in html_extras:
        titulo = Path(rel).stem.replace("_", " ").replace("-", " ").strip().capitalize()
        secoes.append(secao(id_extra(rel), titulo, h, rel))

    for rel, h in html_markdowns_auto:
        titulo = Path(rel).stem.replace("_", " ").replace("-", " ").strip().capitalize()
        secoes.append(secao(id_extra(rel), titulo, h, rel))

    if html_skill:
        secoes.append(secao("proximos", "Próximas ações (router)", html_skill, skill_rel))

    if pendencias:
        linhas_pend = []
        for p in pendentes:
            linhas_pend.append(
                f'<div class="pend"><span class="mk">\u2610</span>'
                f'<span>{_inline(p["texto"])}<div class="src">{html.escape(p["fonte"])}</div></span></div>'
            )
        bloco_feitas = ""
        if feitas:
            itens = "".join(
                f'<div class="pend"><span class="mk">\u2611</span>'
                f'<span>{_inline(f["texto"])}<div class="src">{html.escape(f["fonte"])}</div></span></div>'
                for f in feitas
            )
            bloco_feitas = f"<details><summary>{len(feitas)} já resolvidas</summary>{itens}</details>"
        corpo = ("".join(linhas_pend) or "<p>nenhuma pendência em aberto — bom sinal.</p>") + bloco_feitas
        secoes.append(secao("pendencias", f"Dados pendentes ({len(pendentes)} em aberto)", corpo, None))

    # Fontes lidas, sem duplicar entradas que já ganharam seção especializada.
    fontes = []
    fontes_vistas = set()

    def adicionar_fonte(nome, caminho):
        chave = str(caminho).casefold()
        if chave not in fontes_vistas:
            fontes.append((nome, str(caminho)))
            fontes_vistas.add(chave)

    if context_txt:
        adicionar_fonte("CONTEXT.md", context_path)
    if plano_txt:
        adicionar_fonte(plano_rel, plano_path)
    for rel, _ in extras:
        adicionar_fonte(rel, projeto / rel)
    for rel, _ in markdowns_auto:
        adicionar_fonte(rel, projeto / rel)
    if skill_txt:
        adicionar_fonte(skill_rel, projeto / skill_rel)
    if estado_txt:
        adicionar_fonte("ESTADO.md", projeto / "ESTADO.md")
    if handoff_txt:
        adicionar_fonte("HANDOFF.md", projeto / "HANDOFF.md")
    if decisoes_txt:
        adicionar_fonte("DECISOES.md", projeto / "DECISOES.md")
    linhas_fontes = "".join(
        f'<tr><th>{html.escape(nome)}</th><td><button class="cp" onclick="cp(this,{html.escape(json.dumps(caminho), quote=True)})">copiar caminho</button>'
        f'<span class="section-file" style="margin:0 0 0 10px;display:inline">{html.escape(caminho)}</span></td></tr>'
        for nome, caminho in fontes
    )
    secoes.append(f"""
    <section id="fontes"><h2>Fontes deste relatório (não editar o HTML — editar aqui e regerar)</h2>
      <p class="section-file">"Fontes" = caminho de arquivo. Pra rotas de decisão financeira, ver a seção
      "Resolução" acima.</p>
      <div class="tbl-wrap"><table><tbody>{linhas_fontes}</tbody></table></div>
    </section>""")

    # --- JSON-LD / meta pra IA ---
    json_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "Report",
        "name": f"{args.titulo} — relatório de projeto",
        "dateCreated": data_iso,
        "abstract": tldr,
        "about": {"@type": "Thing", "name": args.titulo},
        "isPartOf": {"@type": "SoftwareApplication", "name": "megabrain"},
        "pendencias_abertas": [p["texto"] for p in pendentes],
        "acoes_rapidas": [{"nome": rotulo, "url": href} for rotulo, href, _ in acoes],
        "fontes_markdown": [nome for nome, _ in fontes],
    }, ensure_ascii=False, indent=2)

    nav_ids = []
    if acao_imediata_html or acoes:
        nav_ids.append("acao")
    if html_context:
        nav_ids.append("contexto")
    nav_ids.append("geral")
    nav_ids.append("handoff")
    if resolucao_blocos:
        nav_ids.append("resolucao")
    nav_ids.append("situacao")
    for rel, _ in html_extras:
        nav_ids.append(id_extra(rel))
    for rel, _ in html_markdowns_auto:
        nav_ids.append(id_extra(rel))
    if html_skill:
        nav_ids.append("proximos")
    if pendencias:
        nav_ids.append("pendencias")
    nav_ids.append("fontes")
    nav_html = "".join(f'<a href="#{i}">{i.replace("extra-", "")}</a>' for i in nav_ids)

    ai_box = f"""
    <section id="ia"><h2>Para a IA</h2>
      <div class="card-ai">
        <p><strong>Este HTML é o relatório de projeto</strong> — a instância aplicada de
        <code>{html.escape(args.titulo)}</code>. Leia-o inteiro antes de vasculhar os .md
        soltos: ele já concentra contexto específico, contexto geral do megabrain,
        estado/handoff, situação viva, pendências e toda documentação Markdown da
        instância (exceto infraestrutura ignorada). Se precisar do detalhe bruto de uma
        fonte, o caminho absoluto está na seção "Fontes" acima — nunca edite este HTML,
        edite a fonte e rode <code>bin/mb-relatorio-projeto.py</code> de novo.</p>
        <p><strong>TL;DR:</strong> {html.escape(tldr)}</p>
        <p><strong>Pendências em aberto:</strong> {len(pendentes)}</p>
      </div>
      <details><summary>Metadados estruturados (JSON-LD)</summary><pre><code>{html.escape(json_ld)}</code></pre></details>
    </section>"""

    botoes_acao = []
    for rotulo, href, externa in acoes:
        destino = ' target="_blank" rel="noopener noreferrer"' if externa else ''
        botoes_acao.append(
            f'<a class="acao-btn" href="{html.escape(href, quote=True)}"{destino}>'
            f'{html.escape(rotulo)}</a>'
        )
    acoes_html = "".join(botoes_acao)

    acao_imediata_box = ""
    if acao_imediata_html or acoes_html:
        fonte_tag = (f'<div class="section-file">fonte: <code>{html.escape(acao_imediata_fonte)}</code>'
                     f' — editar lá, nunca aqui</div>') if acao_imediata_fonte else ""
        acao_imediata_box = f"""
    <section id="acao" class="hero-acao"><h2>👉 Ação imediata — o que fazer agora</h2>
      {fonte_tag}
      {acao_imediata_html}
      {'<div class="acoes-rapidas">' + acoes_html + '</div>' if acoes_html else ''}
    </section>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(args.titulo)} · relatório de projeto</title>
<meta name="generator" content="mb-relatorio-projeto.py">
<meta name="megabrain:tipo" content="relatorio-de-projeto">
<meta name="megabrain:projeto" content="{html.escape(args.titulo)}">
<meta name="megabrain:timestamp" content="{html.escape(data_iso)}">
<meta name="megabrain:tldr" content="{html.escape(tldr)}">
<meta name="megabrain:pendencias-abertas" content="{len(pendentes)}">
<meta name="description" content="Relatório de projeto — contexto, estado, situação e próximas ações concentrados num único arquivo, para humano e IA.">
<script type="application/ld+json">{json_ld}</script>
<style>{css(args.tema)}</style></head><body><div class="wrap">
<h1>{html.escape(args.titulo)} · relatório de projeto</h1>
<div class="sub">gerado em {html.escape(data_iso[:16].replace('T', ' '))} · bin/mb-relatorio-projeto.py · irmão do relatório DNA</div>
<div class="tldr {tldr_classe}">{_inline(tldr)}</div>
{acao_imediata_box}
<nav>{nav_html}</nav>
{''.join(secoes)}
{ai_box}
<footer>
<p><b>Como este arquivo se atualiza:</b> nunca se edita o HTML. Edite as fontes listadas
acima e rode <code>python bin/mb-relatorio-projeto.py</code> de novo (mesmos argumentos).
Por padrão, todo <code>.md</code> da instância entra automaticamente; infraestrutura em
<code>MEGABRAIN/</code>, <code>.git/</code>, caches e dependências fica fora.
Se o "gerado em" lá em cima está velho, o retrato está velho.</p>
<p>Template reaplicável a qualquer projeto megabrain — ver
<code>MEGABRAIN.md</code> seção "Relatório de projeto".</p>
</footer>
</div>
<script>{js()}</script>
</body></html>
"""


def main():
    ap = argparse.ArgumentParser(description="Gerador do relatório de projeto (irmão do relatório DNA)")
    ap.add_argument("--projeto", required=True, help="raiz do projeto")
    ap.add_argument("--titulo", required=True, help="nome do projeto (aparece no título)")
    ap.add_argument("--plano", required=True, help="caminho (relativo à raiz) do arquivo vivo principal")
    ap.add_argument("--context", default="CONTEXT.md", help="caminho relativo do glossário (default CONTEXT.md)")
    ap.add_argument("--extra", action="append", default=[], help="arquivo .md extra (repetível)")
    ap.add_argument("--sem-todos-md", action="store_true",
                    help="não descobre os demais .md do projeto (o padrão é incluí-los todos)")
    ap.add_argument("--skill", default=None, help="SKILL.md do router do projeto (opcional)")
    ap.add_argument("--tldr", default=None, help="uma frase; default: 1º parágrafo do --plano")
    ap.add_argument("--tldr-classe", default="atencao", choices=["ok", "atencao", "ruim"])
    ap.add_argument("--tema", default="padrao", choices=["padrao", "megabrain"],
                    help="linguagem visual do HTML; 'megabrain' usa o console editorial")
    ap.add_argument("--megabrain-central", default=None, help="pasta central do megabrain, para puxar o contexto geral real")
    ap.add_argument("--saida", default=None, help="caminho do HTML de saída (default: RELATORIO.html na raiz do projeto)")
    ap.add_argument("--sem-resolucao", action="store_true", help="desliga a extração automática da seção Resolução")
    ap.add_argument("--resolucao-titulo", action="append", default=[],
                     help="palavra-chave extra (além das padrão) pra achar heading de resolução no --plano/--extra (repetível)")
    ap.add_argument("--sem-acao-imediata", action="store_true",
                     help="desliga o card 'Ação imediata' em destaque abaixo do TL;DR")
    ap.add_argument("--acao-imediata-titulo", action="append", default=[],
                     help="palavra-chave extra pra achar o heading de ação imediata no --plano (repetível)")
    ap.add_argument("--acao", action="append", default=[], metavar="ROTULO|URL",
                    help="botão HTTPS ou âncora interna (repetível; ex.: 'Abrir LinkedIn|https://linkedin.com')")
    args = ap.parse_args()

    projeto = Path(args.projeto)
    if not projeto.is_dir():
        print(f"ERRO: projeto não encontrado: {projeto}")
        sys.exit(1)

    saida = Path(args.saida).resolve() if args.saida else projeto / DEFAULT_OUT_NAME
    data_iso = dt.datetime.now().isoformat()

    html_out = gerar(args, data_iso)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(html_out, encoding="utf-8")
    print(f"Relatório de projeto gerado: {saida}")


if __name__ == "__main__":
    main()
