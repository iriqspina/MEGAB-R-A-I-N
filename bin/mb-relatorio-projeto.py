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
import subprocess
import sys
from urllib.parse import urlparse
from pathlib import Path

import mb_utils as u
import mb_pop_tema

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
    # 260824: ~~riscado~~ — a regra de ouro 11 manda riscar o achado derrubado
    texto = re.sub(r"~~(.+?)~~", r"<del>\1</del>", texto)
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
# CSS / JS — marca POP v1.2 (motor/modelos/relatorios/PADRAO.md, 260915)
# --------------------------------------------------------------------------
# Padrão único de relatório: fundo escuro #101014 com auroras violeta/azul
# fixas, glow no topo, cartões de vidro raio 10px, h1 display 800 com halo,
# estados menta/azul/âmbar/coral SEMPRE com glifo além da cor, números
# tabulares. Tokens iguais aos da pele legado (260914_pop/260915_pele-pop-
# legado.css), então a pele que os wrappers ainda injetam por cima não briga.
# Strings em raw (r"") porque o CSS usa escapes próprios (\A, \2713) — em
# string Python normal "\A" é escape inválido (SyntaxWarning).
# `tema` só escolhe o layout (pílulas ou trilho lateral); a pele é uma só.

def css(tema: str = "padrao") -> str:
    base = r"""
:root{--bg:#101014;--surf:rgb(255 255 255/.055);--surf2:rgb(255 255 255/.035);
  --edge:rgb(255 255 255/.08);--edge2:rgb(255 255 255/.14);
  --ink:#eceef4;--ink2:#b9bdc9;--ink3:#8f94a3;--hi:#f5f6fb;
  --ok:#7fc79c;--info:#8cc0dd;--warn:#d9b467;--bad:#e39288;
  --acc:#8cc0dd;--acc-dim:rgb(140 192 221/.14);--violeta:124 92 255;--r:10px;
  --m:ui-monospace,"Cascadia Mono","SF Mono",Consolas,monospace;
  --s:"Segoe UI",system-ui,-apple-system,sans-serif;
  --vidro:blur(14px) saturate(1.25)}
*{box-sizing:border-box;margin:0}
html{scroll-behavior:smooth}
body{min-height:100vh;padding:0;color:var(--ink);font:16px/1.6 var(--s);font-variant-numeric:tabular-nums;
  -webkit-font-smoothing:antialiased;overflow-x:hidden;
  background:radial-gradient(70rem 24rem at 50% -8rem,rgb(var(--violeta)/.42),transparent 70%),
    radial-gradient(60vw 55vh at 100% 0%,rgb(var(--violeta)/.5),transparent 70%),
    radial-gradient(55vw 50vh at 0% 100%,rgb(56 150 255/.35),transparent 70%),var(--bg);
  background-attachment:fixed}
/* glow no topo: filete de luz fixo */
body::before{content:"";position:fixed;z-index:70;inset:0 0 auto;height:2px;pointer-events:none;
  background:linear-gradient(90deg,transparent,rgb(140 192 221/.85) 30%,rgb(var(--violeta)/.95) 70%,transparent);
  box-shadow:0 0 22px 3px rgb(var(--violeta)/.55)}
.wrap{max-width:1180px;margin:0 auto;padding:3.2rem clamp(1rem,3vw,2rem) 5rem}

/* cabeçalho ---------------------------------------------------------- */
.wrap>h1{max-width:22ch;margin:0 0 .5rem;color:var(--hi);font:800 clamp(2.1rem,4.4vw,3.6rem)/1 var(--s);
  letter-spacing:-.04em;text-shadow:0 0 32px rgb(56 150 255/.35),0 0 2px rgb(140 192 221/.25)}
.sub{margin:0 0 1.6rem;color:var(--ink3);font-family:var(--m);font-size:.68rem;letter-spacing:.13em;text-transform:uppercase}

/* vidro -------------------------------------------------------------- */
.tldr,.hero-acao,section,table,details,.card-ai,.di,footer,.versao-mb{background:var(--surf);
  border:1px solid var(--edge2);border-radius:var(--r);box-shadow:0 10px 30px rgb(0 0 0/.25);
  -webkit-backdrop-filter:var(--vidro);backdrop-filter:var(--vidro);color:var(--ink)}

/* TL;DR — estado com glifo, nunca só cor ----------------------------- */
.tldr{margin:0 0 1.2rem;padding:1.1rem 1.35rem;border-left:4px solid var(--ok);
  font-size:clamp(1rem,1.35vw,1.14rem);line-height:1.5;color:var(--ink)}
.tldr::before{content:"\2713";display:inline-grid;place-items:center;width:1.5em;height:1.5em;margin-right:.6em;
  border-radius:50%;background:var(--ok);color:var(--bg);font-weight:800;font-size:.85em;vertical-align:.1em}
.tldr.atencao{border-left-color:var(--warn)} .tldr.atencao::before{content:"\25B2";background:var(--warn);border-radius:3px}
.tldr.ruim{border-left-color:var(--bad)} .tldr.ruim::before{content:"\2715";background:var(--bad);border-radius:3px}

/* ação imediata — o painel mais forte, com glow no topo --------------- */
.hero-acao{position:relative;margin:0 0 2rem;padding:1.3rem 1.5rem 1.5rem;border-top:1px solid rgb(140 192 221/.55);
  background:linear-gradient(180deg,rgb(var(--violeta)/.14),var(--surf) 60%);
  box-shadow:0 -1px 0 rgb(140 192 221/.55),0 -18px 40px -12px rgb(var(--violeta)/.55),0 12px 34px rgb(0 0 0/.3)}
.hero-acao h2{margin:0 0 .2rem;color:var(--info);font:700 .72rem/1.3 var(--m);letter-spacing:.15em;text-transform:uppercase}
.hero-acao .section-file{margin:0;color:var(--ink3)}
.hero-acao ol{counter-reset:acao;list-style:none;margin:1rem 0 0;padding:0}
.hero-acao ol>li{counter-increment:acao;position:relative;padding:.62rem 0 .62rem 2.6rem;color:var(--ink);
  border-bottom:1px solid var(--edge);font-size:1rem;line-height:1.45}
.hero-acao ol>li:last-child{border-bottom:0}
.hero-acao ol>li::before{content:counter(acao);position:absolute;left:0;top:.55rem;width:1.7rem;height:1.7rem;
  display:flex;align-items:center;justify-content:center;border-radius:8px;border:1px solid rgb(140 192 221/.5);
  background:var(--acc-dim);color:var(--info);font:700 .75rem var(--m)}
.hero-acao p{color:var(--ink2)} .hero-acao strong{color:var(--hi)}
.acoes-rapidas{display:flex;gap:8px;flex-wrap:wrap;margin-top:1.1rem}
.acao-btn,.cp{display:inline-flex;align-items:center;gap:.4rem;border-radius:var(--r);border:1px solid rgb(140 192 221/.5);
  background:rgb(140 192 221/.12);color:var(--info);font-family:var(--m);font-weight:700;letter-spacing:.08em;
  text-transform:uppercase;text-decoration:none;cursor:pointer;
  transition:transform .15s ease,background .15s ease,box-shadow .15s ease}
.acao-btn{min-height:2.3rem;padding:.4rem .95rem;font-size:.66rem}
.acao-btn::before{content:"\2197";font-size:.9em}
.acao-btn[href^="#"]::before{content:"\2193"}
.cp{padding:.28rem .7rem;margin-left:10px;font-size:.6rem}
.cp::before{content:"\29C9"}
.acao-btn:hover,.cp:hover{transform:translateY(-1px);background:rgb(140 192 221/.22);color:var(--hi);
  border-color:var(--info);box-shadow:0 6px 16px rgb(56 150 255/.25);text-decoration:none}
.acao-btn:active,.cp:active{transform:translateY(1px);box-shadow:none}

/* navegação (layout padrão: pílulas grudadas no topo) ----------------- */
nav{position:sticky;top:0;z-index:40;display:flex;gap:6px;flex-wrap:wrap;margin:0 0 12px;padding:10px 12px;
  background:rgb(16 16 20/.62);border:1px solid var(--edge2);border-radius:var(--r);
  -webkit-backdrop-filter:var(--vidro);backdrop-filter:var(--vidro)}
nav a{display:inline-flex;align-items:center;gap:.35rem;padding:6px 12px;border:1px solid var(--edge);border-radius:var(--r);
  color:var(--ink2);font:.66rem/1.2 var(--m);letter-spacing:.08em;text-transform:uppercase;text-decoration:none;
  transition:transform .15s ease,background .15s ease}
nav a::before{content:"\00B7";color:var(--ink3)}
nav a:hover{color:var(--hi);background:rgb(255 255 255/.07);border-color:var(--edge2);transform:translateY(-1px);text-decoration:none}
nav a:hover::before{content:"\203A";color:var(--info)}

/* seções -------------------------------------------------------------- */
section{margin:0 0 12px;padding:1.4rem 1.55rem;scroll-margin-top:4rem}
h2{margin:0 0 .9rem;color:var(--hi);font:800 clamp(1.15rem,2vw,1.55rem)/1.2 var(--s);letter-spacing:-.03em;scroll-margin-top:4rem}
section>h2:first-child::before{content:"\25A0";margin-right:.5rem;color:var(--info);font-size:.6em;vertical-align:.25em}
section.hero-acao>h2::before{content:none}
h3{margin:1.6rem 0 .55rem;padding-top:.85rem;border-top:1px solid var(--edge);color:var(--info);font-size:1.1rem;font-weight:700;letter-spacing:-.015em}
section>h3:first-of-type{margin-top:.5rem;padding-top:0;border-top:0}
h4{margin:1.4rem 0 .45rem;color:var(--ink);font-size:1.02rem;font-weight:700}
h5{margin:1.1rem 0 .3rem;color:var(--info);font-family:var(--m);font-size:.7rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase}
h6{margin:.9rem 0 .25rem;color:var(--ink3);font-size:.82rem;font-weight:600}
p{margin:8px 0;color:var(--ink2)}
ul,ol{margin:8px 0 8px 20px;color:var(--ink2)} li{margin:4px 0;color:var(--ink2)}
strong,b{color:var(--ink)}
a{color:var(--info);text-underline-offset:.18em} a:hover{color:#bfe0f2}
.section-file{margin:-.55rem 0 1rem;color:var(--ink3);font-family:var(--m);font-size:.64rem}

/* tabelas ------------------------------------------------------------- */
.tbl-wrap{overflow-x:auto}
table{width:100%;border-collapse:separate;border-spacing:0;overflow:hidden;margin:10px 0;background:var(--surf2);box-shadow:none}
th{text-align:left;vertical-align:top;padding:.7rem .9rem;border-bottom:1px solid var(--edge2);color:var(--ink3);
  font-family:var(--m);font-size:.62rem;font-weight:500;letter-spacing:.11em;text-transform:uppercase}
td{vertical-align:top;padding:.7rem .9rem;border-bottom:1px solid var(--edge);color:var(--ink2);font-size:.93rem}
tr:last-child td,tr:last-child th{border-bottom:0}

/* checklists e pendências: glifo + cor -------------------------------- */
ul.chk{list-style:none;margin-left:0}
ul.chk li{display:flex;gap:8px;align-items:flex-start}
ul.chk .mk,.pend .mk{font-family:var(--m);font-weight:700}
ul.chk li.open .mk,.pend .mk{color:var(--warn)}
ul.chk li.done{color:var(--ink3);text-decoration:line-through}
ul.chk li.done .mk,details .pend .mk{color:var(--ok)}
.pend{display:flex;gap:10px;align-items:flex-start;padding:9px 0;border-bottom:1px solid var(--edge)}
.pend:last-child{border-bottom:0}
.pend .src{font-family:var(--m);font-size:.62rem;color:var(--ink3);white-space:nowrap}

/* blocos diversos ------------------------------------------------------ */
blockquote{margin:10px 0;padding:4px 14px;border-left:3px solid rgb(var(--violeta)/.55);color:var(--ink3)}
code{font-family:var(--m);font-size:.84em;padding:.1em .38em;border-radius:5px;background:rgb(140 192 221/.12);color:var(--info)}
pre{margin:.6rem 0;padding:.8rem 1rem;overflow:auto;border:1px solid var(--edge);border-radius:var(--r);background:rgb(0 0 0/.28);color:var(--ink2)}
pre code{background:transparent;padding:0}
del{color:var(--ink3);text-decoration-color:var(--bad)}
hr{border:0;border-top:1px solid var(--edge);margin:18px 0}
.card-ai{margin:10px 0;padding:1rem 1.3rem;border-left:3px solid var(--info);color:var(--ink2)}
.card-ai>p:first-child::before{content:"\24D8  ";color:var(--info);font-weight:800}
.di{padding:.2rem 1.1rem} .di div{padding:14px 0;border-bottom:1px solid var(--edge)} .di div:last-child{border-bottom:0}
details{margin:10px 0;padding:0 1.1rem;background:var(--surf2);box-shadow:none}
summary{padding:.8rem 0;cursor:pointer;list-style:none;color:var(--info);font-family:var(--m);font-size:.66rem;
  font-weight:700;letter-spacing:.1em;text-transform:uppercase}
summary::-webkit-details-marker{display:none}
summary::before{content:"\25B8  "} details[open]>summary::before{content:"\25BE  "}
footer{margin-top:1.5rem;padding:1.4rem 1.55rem;color:var(--ink3);font-size:.88rem;line-height:1.7}
footer p{color:var(--ink3)}
:focus-visible{outline:3px solid rgb(var(--violeta));outline-offset:2px;border-radius:6px}

/* toast: todo clique responde ----------------------------------------- */
#toasts{position:fixed;z-index:100;bottom:1.1rem;left:50%;transform:translateX(-50%);display:flex;flex-direction:column;
  gap:.45rem;align-items:center;max-width:min(92vw,34rem);pointer-events:none}
.toast{display:flex;align-items:center;gap:.55rem;padding:.62rem 1rem;border-radius:var(--r);border:1px solid var(--ok);
  background:rgb(22 22 30/.92);color:var(--hi);font-size:.86rem;font-weight:600;box-shadow:0 12px 34px rgb(0 0 0/.55);
  -webkit-backdrop-filter:var(--vidro);backdrop-filter:var(--vidro)}
.toast .t-ico{flex:0 0 auto;color:var(--ok)}
.toast.err{border-color:var(--bad)} .toast.err .t-ico{color:var(--bad)}
.toast small{display:block;color:var(--ink3);font-weight:500;word-break:break-all}
.toast.saindo{opacity:0;transform:translateY(8px);transition:opacity .25s ease,transform .25s ease}

@media(max-width:62rem){.wrap>h1{max-width:none;font-size:clamp(1.9rem,8vw,2.8rem)}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}
  html{scroll-behavior:auto}}
@media print{
  :root{--bg:#fff;--surf:#fff;--surf2:#fff;--edge:#ccc;--edge2:#999;--ink:#000;--ink2:#333;--ink3:#666;--hi:#000;
    --info:#06626f;--acc:#06626f;--acc-dim:#eef6f8}
  body{background:#fff} body::before,nav,#toasts{display:none}
  .wrap>h1{text-shadow:none}
  .tldr,.hero-acao,section,table,details,.card-ai,.di,footer,.versao-mb{box-shadow:none;backdrop-filter:none;-webkit-backdrop-filter:none}
  section,footer,.hero-acao,.tldr,table,.di,details{break-inside:avoid}
}
"""
    if tema == "megabrain":
        return base + css_megabrain()
    if tema == "console":
        return base + css_console()
    return base


def _css_trilho(topo: str, rodape: str) -> str:
    """Layout de trilho lateral fixo (temas console e megabrain).

    `topo`/`rodape` são o texto do trilho em sintaxe de `content` CSS — já
    escapados (\\A = quebra de linha), por isso a montagem aqui é em raw.
    """
    return r"""
/* trilho lateral --------------------------------------------------------- */
.wrap{max-width:none;min-height:100svh;margin:0 0 0 15.5rem;padding:3.6rem clamp(1.1rem,3.4vw,3.2rem) 5rem}
.wrap>*:not(nav){max-width:76rem}
nav{position:fixed;z-index:40;inset:0 auto 0 0;flex-direction:column;flex-wrap:nowrap;gap:2px;width:15.5rem;
  margin:0;padding:6.2rem .8rem 1.2rem;border:0;border-right:1px solid var(--edge2);border-radius:0;overflow-y:auto;
  background:rgb(16 16 20/.62)}
nav::before{content:"__TOPO__";position:absolute;inset:1.5rem 1.1rem auto;padding-bottom:1.1rem;
  border-bottom:1px solid var(--edge2);white-space:pre-line;color:var(--hi);font:800 1rem/1.25 var(--s);letter-spacing:-.02em}
nav::after{content:"__RODAPE__";margin-top:auto;padding-top:1.3rem;border-top:1px solid var(--edge);
  white-space:pre-line;color:var(--ink3);font:.6rem/1.6 var(--m)}
nav a{display:grid;grid-template-columns:1.15rem 1fr;align-items:start;padding:.42rem .5rem;border-color:transparent;
  letter-spacing:.05em;text-transform:none;font-size:.68rem;line-height:1.35;overflow-wrap:anywhere}
@media(max-width:62rem){
  .wrap{margin:0;padding:4.6rem 1rem 3rem}
  nav{inset:0 0 auto;flex-direction:row;width:100%;height:3.5rem;padding:.5rem .6rem;border-right:0;
    border-bottom:1px solid var(--edge2);overflow-x:auto;overflow-y:hidden}
  nav::before,nav::after{display:none}
  nav a{display:flex;min-width:max-content;padding:0 .65rem}
}
""".replace("__TOPO__", topo).replace("__RODAPE__", rodape)


def css_console() -> str:
    """Trilho do tema console (padrão do modo legado desde 260824)."""
    return _css_trilho(r"megabrain\A relatório vivo", r"fonte: markdown do projeto\A o HTML nunca se edita")


def css_megabrain() -> str:
    """Trilho do tema megabrain (opt-in; usado pelo relatório do Currículo)."""
    return _css_trilho(r"CURRÍCULO\A Acompanhamento do projeto", r"Local · relatório vivo\A Fontes Markdown consolidadas")


def js() -> str:
    # Convenção POP: data-copia (clipboard com fallback + toast), data-diz
    # (toast), <a> real navega E avisa. Toast monta nó com textContent —
    # conteúdo do gerador nunca vira HTML.
    return r"""
var fila=document.getElementById('toasts');
function toast(msg,sub,err){
  if(!fila)return;
  var t=document.createElement('div');t.className='toast'+(err?' err':'');
  var ico=document.createElement('span');ico.className='t-ico';ico.textContent=err?'⚠':'✓';
  var box=document.createElement('span');box.textContent=msg;
  if(sub){var s=document.createElement('small');s.textContent=sub;box.appendChild(s);}
  t.appendChild(ico);t.appendChild(box);fila.appendChild(t);
  while(fila.children.length>3)fila.removeChild(fila.firstChild);
  setTimeout(function(){t.classList.add('saindo');setTimeout(function(){t.remove();},280);},3400);
}
function fallback(txt){
  var ta=document.createElement('textarea');ta.value=txt;ta.setAttribute('readonly','');
  ta.style.position='fixed';ta.style.opacity='0';document.body.appendChild(ta);ta.select();
  var ok=false;try{ok=document.execCommand('copy');}catch(e){}
  ta.remove();return ok;
}
function copia(txt,diz,btn){
  var origem=document.activeElement;
  var feito=function(ok){
    toast(ok?(diz||'Copiado'):'Não deu pra copiar',ok?txt:'copia na mão: '+txt,!ok);
    if(ok&&btn&&btn.tagName==='BUTTON'){var o=btn.textContent;btn.textContent='copiado ✓';
      setTimeout(function(){btn.textContent=o;},1400);}
    if(origem&&origem.focus){try{origem.focus({preventScroll:true});}catch(e){}}
  };
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(txt).then(function(){feito(true);},function(){feito(fallback(txt));});
  }else{feito(fallback(txt));}
}
/* compatibilidade: HTML antigo chamava cp(this,'caminho') e copiava entre aspas */
function cp(btn,t){copia('"'+t+'"','Caminho copiado',btn);}
document.addEventListener('click',function(e){
  var c=e.target.closest('[data-copia]');
  if(c){e.preventDefault();copia(c.getAttribute('data-copia'),c.getAttribute('data-diz'),c);return;}
  var d=e.target.closest('[data-diz]');
  if(d){toast(d.getAttribute('data-diz'));return;}
  var a=e.target.closest('a[href]');
  if(a){var h=a.getAttribute('href');
    if(h.charAt(0)==='#'){toast('Indo para: '+(a.textContent.trim()||h));}
    else{toast('Abrindo: '+(a.textContent.trim()||h),h);}}
});
document.addEventListener('keydown',function(e){
  if(e.key!=='Enter'&&e.key!==' ')return;
  var t=e.target.closest?e.target.closest('[role="button"]'):null;
  if(t&&t.tagName!=='BUTTON'&&t.tagName!=='A'&&t.tagName!=='SUMMARY'){e.preventDefault();t.click();}
});
document.querySelectorAll('details').forEach(function(det){det.addEventListener('toggle',function(){
  var s=det.querySelector('summary');toast((det.open?'Aberto: ':'Fechado: ')+(s?s.textContent.trim():''));
});});
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


def localizar_central(arg_central, projeto: Path):
    """--megabrain-central > MEGABRAIN_CENTRAL > a pasta-mãe deste script, se
    ela for uma central de verdade (tem VERSAO.txt e bin/) e não a cópia
    MEGABRAIN/ do próprio projeto."""
    candidatos = []
    if arg_central:
        candidatos.append(Path(arg_central))
    env = os.environ.get("MEGABRAIN_CENTRAL")
    if env:
        candidatos.append(Path(env))
    candidatos.append(Path(__file__).resolve().parent.parent)
    copia = (projeto / "MEGABRAIN").resolve()
    for c in candidatos:
        try:
            c = c.resolve()
        except OSError:
            continue
        if c == copia:
            continue
        if (u.achar(c, "VERSAO.txt")).is_file() and (c / "bin").is_dir():
            return c
    return None


def _primeira_linha(path: Path) -> str:
    try:
        for linha in path.read_text(encoding="utf-8").splitlines():
            if linha.strip():
                return linha.strip()
    except (OSError, UnicodeDecodeError):
        pass
    return ""


def _versao_curta(linha: str) -> str:
    m = re.match(r"(\d{4}-\d{2}-\d{2})\s*·\s*v([\d.]+)", linha)
    return f"v{m.group(2)} ({m.group(1)})" if m else (linha[:40] or "—")


def _git_head(pasta: Path):
    import subprocess
    for cand in (pasta, pasta / "_github/repo-local"):
        if not (cand / ".git").exists():
            continue
        try:
            r = subprocess.run(["git", "--no-optional-locks", "-C", str(cand), "log", "-1", "--format=%h|%cd", "--date=format:%Y-%m-%d"],
                               capture_output=True, text=True, timeout=8, check=False)
        except (OSError, subprocess.SubprocessError):
            return None, None
        if r.returncode == 0 and "|" in r.stdout:
            h, d = r.stdout.strip().split("|", 1)
            return h, d
    return None, None


def versao_megabrain(projeto: Path, central) -> dict:
    """v6.1 (260821): o que o projeto PUXOU (MEGABRAIN/VERSAO.txt + .mb-origem.json)
    contra o que a central TEM agora (VERSAO.txt + HEAD do git)."""
    mb = projeto / "MEGABRAIN"
    puxada_linha = _primeira_linha(u.achar(mb, "VERSAO.txt")) if mb.is_dir() else ""
    origem = {}
    if (mb / ".mb-origem.json").is_file():
        try:
            origem = json.loads((mb / ".mb-origem.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            origem = {}
    atual_linha = _primeira_linha(u.achar(central, "VERSAO.txt")) if central else ""
    head, head_data = _git_head(central) if central else (None, None)
    if not mb.is_dir():
        estado = "sem-copia"
    elif not central:
        estado = "central-desconhecida"
    elif puxada_linha == atual_linha:
        estado = "atual"
    else:
        estado = "desatualizado"
    return {
        "puxada": _versao_curta(puxada_linha) if puxada_linha else "—",
        "puxada_linha": puxada_linha,
        "puxada_commit": (origem.get("commit_central") or "")[:7],
        "puxada_em": (origem.get("sincronizado_em") or "")[:16].replace("T", " "),
        "atual": _versao_curta(atual_linha) if atual_linha else "—",
        "atual_linha": atual_linha,
        "atual_commit": head or "",
        "atual_commit_data": head_data or "",
        "central": str(central) if central else "",
        "estado": estado,
    }


def bloco_versao_html(v: dict) -> str:
    rotulo = {
        "atual": ("ok", "na versão atual"),
        "desatualizado": ("ruim", "DESATUALIZADO — sincronize o MEGABRAIN/ deste projeto"),
        "sem-copia": ("atencao", "projeto sem MEGABRAIN/ (nível 1) — nada puxado"),
        "central-desconhecida": ("atencao", "central não localizada — passe --megabrain-central"),
    }[v["estado"]]
    cls, txt = rotulo
    puxada_det = " · ".join(x for x in (
        f"commit {v['puxada_commit']}" if v["puxada_commit"] else "",
        f"puxado em {v['puxada_em']}" if v["puxada_em"] else "",
    ) if x) or "sem .mb-origem.json (cópia anterior à v6.1)"
    atual_det = " · ".join(x for x in (
        f"git {v['atual_commit']}" if v["atual_commit"] else "",
        v["atual_commit_data"],
    ) if x) or (v["central"] and "central sem git") or "—"
    return f"""
<div class="versao-mb versao-mb--{cls}">
  <div><span class="k">megabrain que este projeto puxou</span><span class="v">{html.escape(v['puxada'])}</span><span class="d">{html.escape(puxada_det)}</span></div>
  <div><span class="k">megabrain atual (central)</span><span class="v">{html.escape(v['atual'])}</span><span class="d">{html.escape(atual_det)}</span></div>
  <div><span class="k">estado</span><span class="v estado">{html.escape(txt)}</span><span class="d">{html.escape(v['central'] or '')}</span></div>
</div>"""


VERSAO_CSS = r"""
/* faixa de versão — vidro POP, estado com glifo além da cor */
.versao-mb{display:grid;grid-template-columns:repeat(auto-fit,minmax(14rem,1fr));gap:0;margin:0 0 1.2rem;overflow:hidden}
.versao-mb>div{display:flex;flex-direction:column;gap:3px;padding:.85rem 1.05rem;border-right:1px solid var(--edge)}
.versao-mb>div:last-child{border-right:0}
.versao-mb .k{color:var(--ink3);font-family:var(--m);font-size:.6rem;letter-spacing:.12em;text-transform:uppercase}
.versao-mb .v{color:var(--hi);font-family:var(--m);font-size:1.05rem;font-weight:800;letter-spacing:-.01em}
.versao-mb .d{color:var(--ink3);font-family:var(--m);font-size:.64rem;word-break:break-all}
.versao-mb--ok{border-color:rgb(127 199 156/.5)} .versao-mb--ok .estado{color:var(--ok)}
.versao-mb--ok .estado::before{content:"\2713  "}
.versao-mb--atencao{border-color:rgb(217 180 103/.5)} .versao-mb--atencao .estado{color:var(--warn)}
.versao-mb--atencao .estado::before{content:"\25B2  "}
.versao-mb--ruim{border-color:rgb(227 146 136/.55)} .versao-mb--ruim .estado{color:var(--bad)}
.versao-mb--ruim .estado::before{content:"\2715  "}
@media(max-width:62rem){.versao-mb>div{border-right:0;border-bottom:1px solid var(--edge)}}
"""


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
    central = localizar_central(args.megabrain_central, projeto)
    if central:
        mb_md = ler(u.achar(central, "MEGABRAIN.md"))
        if mb_md:
            resumo_geral = primeiro_paragrafo(mb_md) or resumo_geral
            central_link = str(central)

    # --- v6.1: versão do megabrain que ESTE projeto puxou × a atual da central ---
    versao_info = versao_megabrain(projeto, central)

    # --- estado / handoff (opcional) ---
    estado_txt = ler(u.achar(projeto, "ESTADO.md"))
    handoff_txt = ler(u.achar(projeto, "HANDOFF.md"))
    decisoes_txt = ler(u.achar(projeto, "DECISOES.md"))
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
        adicionar_fonte("ESTADO.md", u.achar(projeto, "ESTADO.md"))
    if handoff_txt:
        adicionar_fonte("HANDOFF.md", u.achar(projeto, "HANDOFF.md"))
    if decisoes_txt:
        adicionar_fonte("DECISOES.md", u.achar(projeto, "DECISOES.md"))
    linhas_fontes = "".join(
        f'<tr><th>{html.escape(nome)}</th><td><button type="button" class="cp" data-copia="{html.escape(chr(34) + caminho + chr(34), quote=True)}" data-diz="Caminho copiado">copiar caminho</button>'
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
        "isPartOf": {"@type": "SoftwareApplication", "name": "megabrain",
                     "softwareVersion": versao_info["atual"]},
        "megabrain_puxado": {"versao": versao_info["puxada"], "commit": versao_info["puxada_commit"],
                             "em": versao_info["puxada_em"]},
        "megabrain_atual": {"versao": versao_info["atual"], "commit": versao_info["atual_commit"],
                            "estado": versao_info["estado"]},
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

    tela = getattr(args, "tema_tela", None)
    html_attr = ' data-tema="claro"' if tela == "claro" else ""
    return f"""<!DOCTYPE html>
<html lang="pt-BR"{html_attr}><head>
{mb_pop_tema.JS_TEMA_HEAD}<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(args.titulo)} · relatório de projeto</title>
<meta name="generator" content="mb-relatorio-projeto.py">
<meta name="megabrain:tipo" content="relatorio-de-projeto">
<meta name="megabrain:projeto" content="{html.escape(args.titulo)}">
<meta name="megabrain:timestamp" content="{html.escape(data_iso)}">
<meta name="megabrain:tldr" content="{html.escape(tldr)}">
<meta name="megabrain:pendencias-abertas" content="{len(pendentes)}">
<meta name="megabrain:versao-puxada" content="{html.escape(versao_info['puxada'])}">
<meta name="megabrain:versao-atual" content="{html.escape(versao_info['atual'])}">
<meta name="megabrain:versao-estado" content="{html.escape(versao_info['estado'])}">
<meta name="description" content="Relatório de projeto — contexto, estado, situação e próximas ações concentrados num único arquivo, para humano e IA.">
<script type="application/ld+json">{json_ld}</script>
<style>{css(args.tema)}{mb_pop_tema.CSS_TEMA}{VERSAO_CSS}</style></head><body><div class="wrap">
<div class="tema-linha">{mb_pop_tema.HTML_TEMA_CONTROLE}</div>
<h1>{html.escape(args.titulo)} · relatório de projeto</h1>
<div class="sub">gerado em {html.escape(data_iso[:16].replace('T', ' '))} · bin/mb-relatorio-projeto.py · irmão do relatório DNA</div>
{bloco_versao_html(versao_info)}
<div class="tldr {tldr_classe}">{_inline(tldr)}</div>
{acao_imediata_box}
<nav aria-label="seções do relatório">{nav_html}</nav>
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
<div id="toasts" aria-live="polite"></div>
<script>{js()}</script>
{mb_pop_tema.html_interacoes()}
</body></html>
"""


def main():
    """APOSENTADO na v6.6 (260822) — existe UM relatório por instância.

    Este arquivo continua sendo a casa do conversor de markdown, importado por
    mb-relatorio-vivo.py; o que saiu foi a geração de uma SEGUNDA página. Rodar
    direto agora delega, para não quebrar .cmd e docs que apontavam pra cá.
    """
    print("mb-relatorio-projeto.py foi fundido no relatório vivo na v6.6.")
    print("O relatório é um só: bin/mb-relatorio-vivo.py (grava RELATORIO.html).")
    vivo = Path(__file__).resolve().parent / "mb-relatorio-vivo.py"
    if not vivo.is_file():
        print("ERRO: bin/mb-relatorio-vivo.py não encontrado.")
        raise SystemExit(1)

    # 260825 (decisão 260825ab): a delegação chamava o vivo SEM ARGUMENTO e
    # ignorava --projeto e --saida — quem pedia o relatório de um projeto
    # recebia o da CENTRAL, sem erro. Ficou assim desde a v6.6 e só apareceu
    # hoje, quando a cópia magra tirou o script de dentro dos projetos e os
    # wrappers passaram a chamar a central: o do Financeiro da Silva morreu
    # com FileNotFoundError num arquivo que nunca foi escrito.
    # Quem passa --projeto/--saida quer a página agregada daquele projeto —
    # isso é o modo legado, que continua existindo e sabe fazer.
    argv = sys.argv[1:]
    if any(a.startswith("--projeto") or a.startswith("--saida") for a in argv):
        print("argumentos de projeto detectados → modo legado (página agregada "
              "daquele projeto), em vez de delegar pro relatório da central.\n")
        return _main_legado()

    print("Delegando...\n")
    raise SystemExit(subprocess.call([sys.executable, str(vivo)]))
    raise SystemExit(1)


def _main_legado():
    ap = argparse.ArgumentParser(description="[legado] gerador da página agregada de .md")
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
    ap.add_argument("--tema-tela", dest="tema_tela", default=None, choices=["claro", "escuro"],
                    help="tema inicial claro/escuro do HTML gerado (default: escuro — o navegador do leitor pode lembrar a preferência). O --tema de cima escolhe o esqueleto e continua igual.")
    ap.add_argument("--tema", default="console", choices=["console", "padrao", "megabrain"],
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
