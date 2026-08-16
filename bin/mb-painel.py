#!/usr/bin/env python3
"""
mb-painel.py — gera PAINEL-MEGABRAIN.html: um arquivo unico, offline, que
concentra tudo que o humano precisa ler e todo comando que ele precisa rodar.

O que entra:
  - todo .md e .txt do pacote, renderizado e buscavel;
  - a trilha dos 8 gates, cada um com o prompt pronto pra colar em qualquer IA;
  - os atalhos de comando (trava, versao, aspirador, relatorios, arrumacao),
    ja com a raiz da instalacao substituida;
  - a tabela de integridade (bytes + sha256) que o Gate 5 exige pra comparar
    a copia instalada com a fonte.

Nao guarda estado no navegador de proposito: no megabrain, estado mora em
ESTADO.md / HANDOFF.md / DECISOES.md. O painel monta o bloco e voce cola.

Uso:  python bin/mb-painel.py --raiz . [--saida PAINEL-MEGABRAIN.html]
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

EXTENSOES = {".md", ".txt"}
IGNORAR = {".git", ".mb-backup", ".dna-backup", ".mb-aspirador", "__pycache__"}

GRUPOS = [
    ("protocolo", ["skills/megabrain/SKILL.md", "MEGABRAIN.md", "skills/codex-megabrain/SKILL.md"]),
    ("porta de entrada", ["README.md", "VERSAO.txt", "OFFLINE.md", "AUDITORIA.md"]),
    ("referências", ["referencias/"]),
    ("apoio", ["docs/", "modelos/", "dna/"]),
]

GATES = [
    ("0", "assumir", "Ler o estado antes de tocar em arquivo",
     "Antes de escrever qualquer coisa neste projeto: rode git pull; leia nesta ordem ESTADO.md, "
     "HANDOFF.md, o fim de DECISOES.md e LICOES.md; cheque TRAVADO_POR no HANDOFF.md e assuma a "
     "trava se estiver livre ou vencida; confira se a versao do megabrain do projeto bate com a "
     "central. Nao varra a arvore de arquivos antes disso. Output de outro agente e rascunho, nao "
     "verdade: audite antes de construir em cima."),
    ("1", "enquadrar", "Cinco respostas antes do primeiro token",
     "Antes de produzir qualquer output, responda internamente: (1) qual o artefato final e em que "
     "app ele abre; (2) quem le e que decisao essa pessoa toma depois; (3) tres criterios de "
     "aprovacao verificaveis, escritos ANTES de gerar; (4) a restricao dura — prazo, formato, marca, "
     "tom, limite tecnico; (5) o contraexemplo: como seria a versao obvia e generica disso? Nomeie, "
     "porque voce vai evita-la. Se algo estiver vago, faca no maximo 2 perguntas objetivas antes de "
     "comecar."),
    ("2", "orçar contexto", "Contexto é orçamento compartilhado, não depósito",
     "Trate contexto como orcamento: leia sob demanda (Glob, depois Grep, depois Read so do trecho), "
     "nunca despeje pasta ou repositorio inteiro. Escreva estado e decisoes num .md em vez de "
     "carregar tudo na janela. Delegue varredura e leitura ampla a subagente ou ao outro modelo e "
     "receba so a conclusao. Use 2 ou 3 exemplos canonicos, nao 15 casos de borda. Acima de ~85% da "
     "janela: escreva o HANDOFF.md, commite e recomece."),
    ("3", "gerar", "Estrutura antes de prosa",
     "Gere assim: esqueleto primeiro, preenchimento depois. Uma afirmacao por paragrafo. Toda "
     "alegacao factual sobre o mundo atual (preco, cargo, versao, lei, data) e buscada agora, nunca "
     "puxada da memoria — o que nao der pra verificar sai marcado [ESTIMATIVA]. Especifico vence "
     "geral: 'reduz 40% do tempo de export' vence 'melhora a eficiencia'. Se o usuario editou algo "
     "num editor visual, aquilo e a versao final dele: mude cirurgicamente, nunca recrie do zero."),
    ("4", "auditar", "Reescrever, não anunciar que auditou",
     "Releia o que voce acabou de gerar e REESCREVA. (a) Lexico: se apareceu 'no mundo de hoje', "
     "'cada vez mais', 'alavancar', 'robusto', 'ecossistema', 'jornada', 'de forma holistica', "
     "'disruptivo', 'entregar valor', 'ponta a ponta', 'delve', 'leverage', 'seamless', 'robust', "
     "'crucial', 'foster' — reescreva a frase inteira, nao troque o sinonimo. (b) Estrutura: sem 'nao "
     "e apenas X, e Y', sem regra de tres compulsiva, sem travessao como muleta, sem paragrafo final "
     "que repete, sem abrir reafirmando a pergunta, sem fechar com 'me avise se quiser'. (c) "
     "Substancia: aplique o teste do 'e dai?' em cada paragrafo; troque o cliente pelo concorrente e "
     "veja se ainda faz sentido; toda recomendacao declara o que custa. (d) Comprima 30%: se nada "
     "essencial se perdeu, entregue a versao menor. Um reparo so — passou disso, o problema e o "
     "enquadramento, nao a redacao."),
    ("5", "verificar", "Testar o caminho, não confiar na citação",
     "Verifique antes de entregar: o arquivo abre no app de destino e tem o formato certo? Os links e "
     "caminhos existem de fato — teste, nao confie na citacao. Os numeros batem quando recalculados "
     "do zero? As datas foram conferidas contra hoje? Contradiz algo em DECISOES.md? Se o que voce "
     "auditou e um protocolo, skill ou script versionado, compare hash, tamanho e data do arquivo que "
     "REALMENTE foi carregado com a fonte no repositorio. Depois amarre as pontas: varra estado, "
     "tracker e decisoes atras de duvida aberta, numero velho, prazo e dependencia sem dono, e leve "
     "no maximo 5 perguntas, cada uma com evidencia, impacto e recomendacao."),
    ("6", "passar o bastão", "O insumo do próximo agente, não um resumo bonito",
     "Antes de encerrar: (1) resolva sozinho tudo que for automacao local ou ferramenta ja logada, e "
     "leve ao usuario so o que depende dele, agrupado numa pergunta so; (2) reescreva ESTADO.md em 5 "
     "linhas; (3) reescreva HANDOFF.md com o que fez, o que ficou aberto, o proximo passo com verbo e "
     "objeto, os arquivos tocados e TRAVADO_POR: livre; (4) anexe a DECISOES.md cada decisao COM a "
     "alternativa descartada; (5) commite local, e so de push depois de confirmar comigo."),
    ("7", "registrar", "Lição que se repete 3x vira regra",
     "Escreva a licao desta sessao no formato:\n\n## AAMMDD — <contexto em ate 5 palavras>\nGATILHO: "
     "quando essa situacao reaparece\nLICAO: o que deu errado ou foi descoberto\nATALHO: o que fazer "
     "direto da proxima vez\n\nDestino global se seria util num projeto completamente diferente; "
     "destino do projeto (LICOES.md) se e especifica deste cliente. Sempre append, nunca reescreva. "
     "Se ja existe autorizacao permanente para registrar, grave direto e nao pergunte."),
]

MECANICAS = [
    ("trava de handoff", "Impede dois agentes de escreverem no mesmo arquivo. É a única garantia real do protocolo — o resto é pedido.", [
        ("ver quem está com a trava", 'python "{RAIZ}/bin/mb-sync.py" --dir "{PROJETO}" status'),
        ("assumir a trava por 2h", 'python "{RAIZ}/bin/mb-sync.py" --dir "{PROJETO}" lock --agente claude --escopo . --horas 2'),
        ("devolver a trava", 'python "{RAIZ}/bin/mb-sync.py" --dir "{PROJETO}" release --agente claude'),
    ]),
    ("versão do megabrain", "Compara o megabrain de um projeto com o da central e sincroniza. Rodar no Gate 0, antes de planejar.", [
        ("conferir e sincronizar", 'python "{RAIZ}/bin/mb-check-version.py" --projeto "{PROJETO}"'),
        ("conferir sem internet", 'python "{RAIZ}/bin/mb-check-version.py" --projeto "{PROJETO}" --offline'),
        ("subir projeto → central", 'python "{RAIZ}/bin/mb-sync-projeto-para-central.py" --projeto "{PROJETO}"'),
    ]),
    ("manutenção do pacote", "Arruma a pasta, aplica os patches de versao e regenera os artefatos. Tudo tem dry-run ou backup antes de escrever.", [
        ("ver o plano de arrumação", 'python "{RAIZ}/bin/mb-arrumar.py" --raiz "{RAIZ}"'),
        ("arrumar de verdade (faz backup)", 'python "{RAIZ}/bin/mb-arrumar.py" --raiz "{RAIZ}" --aplicar'),
        ("procurar referência quebrada", 'python "{RAIZ}/bin/mb-arrumar.py" --raiz "{RAIZ}" --verificar'),
        ("aplicar os patches de versao", 'python "{RAIZ}/bin/mb-patch-v5.py" --raiz "{RAIZ}"'),
        ("regerar este painel", 'python "{RAIZ}/bin/mb-painel.py" --raiz "{RAIZ}"'),
        ("regerar o relatório DNA", 'python "{RAIZ}/bin/mb-relatorio-dna.py"'),
    ]),
    ("código e projeto", "Limpeza mecânica de código e relatório de instância de um projeto.", [
        ("aspirador em dry-run", 'python "{RAIZ}/bin/mb-aspirador.py" --dir "{PROJETO}"'),
        ("relatório de um projeto", 'python "{RAIZ}/bin/mb-relatorio-projeto.py" --projeto "{PROJETO}"'),
        ("backup da central", 'python "{RAIZ}/bin/mb-backup-central.py"'),
    ]),
    ("provar que a trava trava", "A trava e a unica garantia real do protocolo. Rode depois de qualquer mexida em bin/ — sao 7 casos e leva segundos.", [
        ("rodar os testes", 'python "{RAIZ}/tests/test_mb_sync.py"'),
        ("rodar com pytest", 'pytest "{RAIZ}/tests"'),
    ]),
    ("identidade entre agentes", "Uma fonte, três cópias: CLAUDE.md, GEMINI.md, AGENTS.md. Nunca edite a cópia.", [
        ("sincronizar nos três", 'python "{RAIZ}/bin/mb-sync-memoria.py" --source "{RAIZ}/260810_memoria-pessoal.md" --target all --modo conteudo --dir "%USERPROFILE%"'),
    ]),
    ("conferir a cópia instalada", "Gate 5: o arquivo que o agente carregou pode não ser o do repositório. Compare o hash com a tabela de integridade deste painel.", [
        ("hash da skill instalada (PowerShell)", 'Get-FileHash "$env:USERPROFILE\\.claude\\skills\\megabrain\\SKILL.md" -Algorithm SHA256'),
        ("hash da skill instalada (Python)", 'python -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],\'rb\').read()).hexdigest()[:16])" "%USERPROFILE%\\.claude\\skills\\megabrain\\SKILL.md"'),
    ]),
]

MODELOS = [
    ("HANDOFF.md", """# HANDOFF

<!-- mb-sync:lock:start -->
USUARIO: <seu nome>
TRAVADO_POR: livre
<!-- mb-sync:lock:end -->

## <AAMMDD> · <agente>
FIZ: <o que ficou pronto, com os arquivos>
ABERTO: <o que não fechou e por quê>
PRÓXIMO PASSO: <verbo + objeto: "escrever os 3 títulos do slide 4 usando a paleta de DECISOES#4">
TOQUEI: <caminho/arquivo.ext, caminho/outro.ext>
"""),
    ("ESTADO.md", """# ESTADO

FASE: <duplo diamante 1-4, ou fase macro do projeto>
ÚLTIMA ENTREGA: <o quê, quando>
EM ANDAMENTO: <a única coisa em curso>
BLOQUEIO: <o que trava, ou "nenhum">
DECISÃO PENDENTE: <o que precisa de resposta humana>
"""),
    ("DECISOES.md (append)", """## <AAMMDD> · <decisão em uma linha>
ESCOLHIDO: <o que foi decidido>
DESCARTADO: <a alternativa que perdeu>
PORQUÊ: <o critério que decidiu, não a justificativa bonita>
CUSTA: <o que essa escolha custa>
"""),
    ("LICOES.md (append)", """## <AAMMDD> — <contexto em até 5 palavras>
GATILHO: <quando essa situação reaparece>
LIÇÃO: <o que deu errado ou foi descoberto>
ATALHO: <o que fazer direto da próxima vez>
"""),
]


def coletar(raiz: Path) -> list[dict]:
    arquivos = []
    for f in sorted(raiz.rglob("*")):
        if not f.is_file() or f.suffix.lower() not in EXTENSOES:
            continue
        if any(p in IGNORAR for p in f.parts):
            continue
        rel = f.relative_to(raiz).as_posix()
        dados = f.read_bytes()
        arquivos.append({
            "caminho": rel,
            "nome": f.name,
            "texto": dados.decode("utf-8", errors="replace"),
            "bytes": len(dados),
            "sha": hashlib.sha256(dados).hexdigest()[:16],
            "mtime": dt.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
        })
    return arquivos


def agrupar(arquivos: list[dict]) -> list[dict]:
    restantes = {a["caminho"] for a in arquivos}
    grupos = []
    for titulo, regras in GRUPOS:
        itens = []
        for regra in regras:
            for a in arquivos:
                c = a["caminho"]
                if c not in restantes:
                    continue
                if (regra.endswith("/") and c.startswith(regra)) or c == regra:
                    itens.append(c)
                    restantes.discard(c)
        if itens:
            grupos.append({"titulo": titulo, "itens": itens})
    if restantes:
        grupos.append({"titulo": "outros", "itens": sorted(restantes)})
    return grupos


def montar(raiz: Path, arquivos: list[dict]) -> str:
    versao_txt = (raiz / "VERSAO.txt")
    versao = versao_txt.read_text(encoding="utf-8").splitlines()[0] if versao_txt.exists() else "sem VERSAO.txt"
    dados = {
        "raiz": str(raiz),
        "versao": versao,
        "gerado": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "arquivos": arquivos,
        "grupos": agrupar(arquivos),
        "gates": [{"n": n, "nome": nome, "resumo": r, "prompt": p} for n, nome, r, p in GATES],
        "mecanicas": [{"titulo": t, "sobre": s, "comandos": [{"rotulo": r, "cmd": c} for r, c in cs]}
                      for t, s, cs in MECANICAS],
        "modelos": [{"nome": n, "texto": t} for n, t in MODELOS],
    }
    payload = json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.replace("__DADOS__", payload).replace("__VERSAO__", versao.split("—")[0].strip())


TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Painel MEGABRAIN</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --breu:#0B0C0E; --chapa:#15171B; --alto:#1D2026; --risco:#2A2E36;
  --osso:#E9E5DE; --meio:#9AA0AA; --sinal:#FFB000; --travado:#D0473E; --ok:#7FA88C;
  --display:"Archivo","Helvetica Neue",Arial,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Consolas,monospace;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{background:var(--breu);color:var(--osso);font-family:var(--display);font-size:15px;line-height:1.6;
  -webkit-font-smoothing:antialiased}
a{color:var(--sinal);text-decoration:none;border-bottom:1px solid rgba(255,176,0,.3)}
a:hover{border-bottom-color:var(--sinal)}
:focus-visible{outline:2px solid var(--sinal);outline-offset:2px}
button{font-family:inherit;color:inherit;cursor:pointer}

/* ---------- cabeçalho ---------- */
.topo{position:sticky;top:0;z-index:30;background:rgba(11,12,14,.94);backdrop-filter:blur(8px);
  border-bottom:1px solid var(--risco)}
.topo-linha{display:flex;gap:18px;align-items:center;padding:14px 20px;flex-wrap:wrap}
.marca{font-weight:800;letter-spacing:.16em;font-size:15px;text-transform:uppercase;white-space:nowrap}
.marca span{color:var(--sinal)}
.selo{font-family:var(--mono);font-size:11px;color:var(--meio);border:1px solid var(--risco);
  padding:3px 8px;border-radius:2px;white-space:nowrap}
.campos{display:flex;gap:10px;margin-left:auto;flex-wrap:wrap}
.campo{display:flex;align-items:center;gap:7px;background:var(--chapa);border:1px solid var(--risco);
  border-radius:2px;padding:5px 10px}
.campo label{font-family:var(--mono);font-size:10px;letter-spacing:.12em;color:var(--meio);text-transform:uppercase}
.campo input{background:none;border:0;color:var(--osso);font-family:var(--mono);font-size:12px;width:210px;padding:2px 0}
.campo input:focus{outline:none}
@media(max-width:720px){.campo input{width:130px}}

/* ---------- trilha de gates ---------- */
.trilha-caixa{border-bottom:1px solid var(--risco);background:var(--breu)}
.trilha{display:flex;gap:0;padding:0 20px;overflow-x:auto;scrollbar-width:none}
.trilha::-webkit-scrollbar{display:none}
.pad{flex:1 0 auto;min-width:104px;background:none;border:0;border-right:1px solid var(--risco);
  padding:12px 14px 14px;text-align:left;position:relative;transition:background .12s}
.pad:first-child{border-left:1px solid var(--risco)}
.pad:hover{background:var(--alto)}
.pad .n{font-family:var(--mono);font-size:11px;color:var(--meio)}
.pad .rot{display:block;font-weight:600;font-size:13px;margin-top:2px;letter-spacing:-.01em}
.pad::after{content:"";position:absolute;left:0;right:0;bottom:0;height:3px;background:transparent}
.pad[aria-selected="true"]{background:var(--alto)}
.pad[aria-selected="true"]::after{background:var(--sinal)}
.pad[data-feito="1"] .n{color:var(--sinal)}
.pad[data-feito="1"]::after{background:rgba(255,176,0,.35)}

.gate-detalhe{padding:16px 20px 20px;border-top:1px solid var(--risco);background:var(--chapa);display:none}
.gate-detalhe.aberto{display:block}
.gate-detalhe h3{margin:0 0 4px;font-size:17px;font-weight:800;letter-spacing:-.01em}
.gate-detalhe .sub{color:var(--meio);font-size:13px;margin-bottom:12px}
.gate-detalhe pre{background:var(--breu);border:1px solid var(--risco);border-radius:2px;padding:14px;
  font-family:var(--mono);font-size:12.5px;line-height:1.65;white-space:pre-wrap;margin:0 0 12px;max-height:280px;overflow:auto}

/* ---------- corpo ---------- */
.corpo{display:grid;grid-template-columns:250px 1fr;min-height:60vh}
@media(max-width:860px){.corpo{grid-template-columns:1fr}}
.indice{border-right:1px solid var(--risco);padding:18px 0 60px}
@media(max-width:860px){.indice{border-right:0;border-bottom:1px solid var(--risco);padding-bottom:18px}}
.grupo{margin-bottom:18px}
.grupo h4{font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--meio);margin:0 0 6px;padding:0 20px}
.item{display:block;width:100%;text-align:left;background:none;border:0;border-left:2px solid transparent;
  padding:5px 20px;font-size:13.5px;color:var(--osso);opacity:.82}
.item:hover{opacity:1;background:var(--chapa)}
.item[aria-current="true"]{opacity:1;border-left-color:var(--sinal);background:var(--chapa);font-weight:600}
.item.oculto{display:none}

.leitor{padding:26px 34px 90px;min-width:0;max-width:none}
@media(max-width:860px){.leitor{padding:22px 18px 70px}}
.leitor-topo{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;padding-bottom:12px;
  border-bottom:1px solid var(--risco);margin-bottom:22px}
.leitor-topo h2{margin:0;font-size:20px;font-weight:800;letter-spacing:-.015em}
.leitor-topo .meta{font-family:var(--mono);font-size:11px;color:var(--meio);margin-left:auto}

/* ---------- botões ---------- */
.btn{background:var(--alto);border:1px solid var(--risco);border-radius:2px;padding:6px 12px;
  font-family:var(--mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase;transition:.12s}
.btn:hover{border-color:var(--sinal);color:var(--sinal)}
.btn.feito{border-color:var(--ok);color:var(--ok)}
.btn-sinal{background:var(--sinal);color:#131313;border-color:var(--sinal);font-weight:600}
.btn-sinal:hover{background:#ffc23d;color:#131313}
.btn-linha{display:flex;gap:8px;flex-wrap:wrap}

/* ---------- cartões de mecânica ---------- */
.cartao{border:1px solid var(--risco);border-radius:3px;background:var(--chapa);margin-bottom:16px;overflow:hidden}
.cartao h3{margin:0;padding:13px 16px 4px;font-size:15px;font-weight:700;letter-spacing:-.01em}
.cartao .sobre{padding:0 16px 12px;color:var(--meio);font-size:13px}
.cmd{display:flex;gap:12px;align-items:center;border-top:1px solid var(--risco);padding:9px 16px}
.cmd .rot{font-size:12.5px;color:var(--meio);min-width:190px}
.cmd code{font-family:var(--mono);font-size:12px;color:var(--osso);word-break:break-all;flex:1;min-width:0}
.cmd .btn{flex-shrink:0}
@media(max-width:720px){.cmd{flex-wrap:wrap;gap:7px}.cmd .rot{min-width:0;width:100%}}

/* ---------- tabela ---------- */
table{border-collapse:collapse;width:100%;margin:14px 0 26px;font-size:13px}
th,td{border-bottom:1px solid var(--risco);padding:7px 10px;text-align:left;vertical-align:top}
th{font-family:var(--mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--meio);font-weight:500}
td.mono,.mono{font-family:var(--mono);font-size:12px}

/* ---------- markdown ---------- */
.md h1{font-size:23px;font-weight:800;letter-spacing:-.02em;margin:30px 0 10px}
.md h2{font-size:18px;font-weight:700;margin:28px 0 8px;padding-top:14px;border-top:1px solid var(--risco)}
.md h3{font-size:15px;font-weight:700;margin:20px 0 6px}
.md h4{font-size:13px;font-weight:600;margin:16px 0 4px;color:var(--meio)}
.md p{margin:0 0 12px;max-width:74ch}
.md ul,.md ol{margin:0 0 12px;padding-left:20px;max-width:74ch}
.md li{margin-bottom:4px}
.md code{font-family:var(--mono);font-size:12.5px;background:var(--chapa);border:1px solid var(--risco);
  border-radius:2px;padding:1px 5px}
.md pre{background:var(--chapa);border:1px solid var(--risco);border-left:2px solid var(--sinal);
  border-radius:2px;padding:13px 15px;overflow-x:auto;margin:0 0 14px}
.md pre code{background:none;border:0;padding:0;font-size:12.5px;line-height:1.6}
.md blockquote{border-left:2px solid var(--sinal);margin:0 0 14px;padding:2px 0 2px 15px;color:var(--meio);max-width:74ch}
.md hr{border:0;border-top:1px solid var(--risco);margin:24px 0}
.md strong{font-weight:600;color:#fff}
.md table{max-width:100%}
.md .marca-busca{background:rgba(255,176,0,.28);color:#fff;border-radius:2px}

.aviso{font-size:12.5px;color:var(--meio);border-left:2px solid var(--risco);padding-left:12px;margin:18px 0}
.rodape{border-top:1px solid var(--risco);padding:16px 20px 40px;font-family:var(--mono);font-size:11px;color:var(--meio)}
#toast{position:fixed;left:50%;bottom:26px;transform:translateX(-50%) translateY(12px);background:var(--sinal);
  color:#131313;font-family:var(--mono);font-size:12px;font-weight:600;padding:9px 16px;border-radius:2px;
  opacity:0;pointer-events:none;transition:.18s;z-index:60}
#toast.ver{opacity:1;transform:translateX(-50%) translateY(0)}
@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>
</head>
<body>

<header class="topo">
  <div class="topo-linha">
    <div class="marca">MEGA<span>BRAIN</span></div>
    <div class="selo" id="selo-versao">__VERSAO__</div>
    <div class="campos">
      <div class="campo">
        <label for="raiz">raiz</label>
        <input id="raiz" spellcheck="false" title="Caminho da sua instalação do megabrain. Todo comando copiado sai com ele.">
      </div>
      <div class="campo">
        <label for="projeto">projeto</label>
        <input id="projeto" spellcheck="false" value="." title="Pasta do projeto em que você está trabalhando.">
      </div>
      <div class="campo">
        <label for="busca">buscar</label>
        <input id="busca" spellcheck="false" placeholder="anti-slop, trava, duplo diamante…">
      </div>
    </div>
  </div>
  <div class="trilha-caixa">
    <div class="trilha" id="trilha" role="tablist" aria-label="Gates do protocolo"></div>
    <div class="gate-detalhe" id="gate-detalhe" role="tabpanel"></div>
  </div>
</header>

<div class="corpo">
  <nav class="indice" id="indice" aria-label="Arquivos do pacote"></nav>
  <main class="leitor" id="leitor"></main>
</div>

<div class="rodape" id="rodape"></div>
<div id="toast" role="status" aria-live="polite"></div>

<script type="application/json" id="dados">__DADOS__</script>
<script>
const D = JSON.parse(document.getElementById('dados').textContent);
const $ = s => document.querySelector(s);
const esc = t => t.replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

/* ---------------- markdown mínimo ---------------- */
function inline(t){
  return esc(t)
    .replace(/`([^`]+)`/g, (m,c)=>'<code>'+c+'</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[\s(])\*([^*\n]+)\*/g, '$1<em>$2</em>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" rel="noopener">$1</a>');
}
function md(txt){
  const linhas = txt.split('\n'); let out = [], i = 0, lista = null;
  const fechaLista = () => { if(lista){ out.push('</'+lista+'>'); lista = null; } };
  while(i < linhas.length){
    let l = linhas[i];
    if(/^```/.test(l)){
      fechaLista(); const buf = []; i++;
      while(i < linhas.length && !/^```/.test(linhas[i])) buf.push(linhas[i++]);
      i++; out.push('<pre><code>'+esc(buf.join('\n'))+'</code></pre>'); continue;
    }
    if(/^\|/.test(l) && /^\|[\s:|-]+\|?\s*$/.test(linhas[i+1]||'')){
      fechaLista();
      const cel = r => r.replace(/^\||\|$/g,'').split('|').map(c=>inline(c.trim()));
      out.push('<table><thead><tr>'+cel(l).map(c=>'<th>'+c+'</th>').join('')+'</tr></thead><tbody>');
      i += 2;
      while(i < linhas.length && /^\|/.test(linhas[i])){
        out.push('<tr>'+cel(linhas[i]).map(c=>'<td>'+c+'</td>').join('')+'</tr>'); i++;
      }
      out.push('</tbody></table>'); continue;
    }
    let m;
    if(m = l.match(/^(#{1,4})\s+(.*)$/)){ fechaLista(); const n = m[1].length; out.push('<h'+n+'>'+inline(m[2])+'</h'+n+'>'); i++; continue; }
    if(/^(---|___|\*\*\*)\s*$/.test(l)){ fechaLista(); out.push('<hr>'); i++; continue; }
    if(m = l.match(/^>\s?(.*)$/)){
      fechaLista(); const buf = [];
      while(i < linhas.length && /^>/.test(linhas[i])) buf.push(linhas[i++].replace(/^>\s?/,''));
      out.push('<blockquote>'+inline(buf.join(' '))+'</blockquote>'); continue;
    }
    if(m = l.match(/^\s*[-*·]\s+(.*)$/)){
      if(lista !== 'ul'){ fechaLista(); out.push('<ul>'); lista = 'ul'; }
      out.push('<li>'+inline(m[1])+'</li>'); i++; continue;
    }
    if(m = l.match(/^\s*\d+[.)]\s+(.*)$/)){
      if(lista !== 'ol'){ fechaLista(); out.push('<ol>'); lista = 'ol'; }
      out.push('<li>'+inline(m[1])+'</li>'); i++; continue;
    }
    if(!l.trim()){ fechaLista(); i++; continue; }
    const par = [];
    while(i < linhas.length && linhas[i].trim() && !/^(#{1,4}\s|```|>|\||\s*[-*·]\s|\s*\d+[.)]\s|---)/.test(linhas[i])) par.push(linhas[i++]);
    if(par.length){ fechaLista(); out.push('<p>'+inline(par.join('\n'))+'</p>'); } else { i++; }
  }
  fechaLista();
  return out.join('\n');
}

/* ---------------- utilidades ---------------- */
let toastT;
function toast(msg){
  const t = $('#toast'); t.textContent = msg; t.classList.add('ver');
  clearTimeout(toastT); toastT = setTimeout(()=>t.classList.remove('ver'), 1700);
}
function copiar(txt, btn, rotulo){
  const ok = () => { toast(rotulo || 'copiado'); if(btn){ const a = btn.textContent; btn.textContent = 'copiado'; btn.classList.add('feito');
    setTimeout(()=>{ btn.textContent = a; btn.classList.remove('feito'); }, 1400); } };
  if(navigator.clipboard && window.isSecureContext){ navigator.clipboard.writeText(txt).then(ok, ()=>fallback(txt, ok)); }
  else fallback(txt, ok);
}
function fallback(txt, ok){
  const ta = document.createElement('textarea');
  ta.value = txt; ta.style.position='fixed'; ta.style.opacity='0';
  document.body.appendChild(ta); ta.select();
  try{ document.execCommand('copy'); ok(); }catch(e){ toast('copie manualmente'); }
  document.body.removeChild(ta);
}
const raizAtual = () => ($('#raiz').value || D.raiz).replace(/[\\/]+$/,'');
const projetoAtual = () => $('#projeto').value || '.';
const resolver = c => c.replaceAll('{RAIZ}', raizAtual()).replaceAll('{PROJETO}', projetoAtual());

/* ---------------- trilha de gates ---------------- */
const feitos = new Set();
function montarTrilha(){
  $('#trilha').innerHTML = D.gates.map(g =>
    '<button class="pad" role="tab" aria-selected="false" data-g="'+g.n+'">' +
    '<span class="n">GATE '+g.n+'</span><span class="rot">'+esc(g.nome)+'</span></button>').join('');
  $('#trilha').addEventListener('click', e => {
    const b = e.target.closest('.pad'); if(!b) return;
    const g = D.gates.find(x => x.n === b.dataset.g);
    const jaAberto = b.getAttribute('aria-selected') === 'true';
    document.querySelectorAll('.pad').forEach(p => p.setAttribute('aria-selected','false'));
    if(jaAberto){ $('#gate-detalhe').classList.remove('aberto'); return; }
    b.setAttribute('aria-selected','true');
    const d = $('#gate-detalhe');
    d.innerHTML = '<h3>Gate '+g.n+' · '+esc(g.nome)+'</h3><div class="sub">'+esc(g.resumo)+'</div>' +
      '<pre>'+esc(g.prompt)+'</pre><div class="btn-linha">' +
      '<button class="btn btn-sinal" data-copiar-gate="'+g.n+'">copiar prompt do gate</button>' +
      '<button class="btn" data-marcar="'+g.n+'">'+(feitos.has(g.n)?'desmarcar':'marcar como rodado')+'</button>' +
      '<button class="btn" data-bloco>montar bloco de handoff</button></div>';
    d.classList.add('aberto');
  });
  $('#gate-detalhe').addEventListener('click', e => {
    const c = e.target.closest('[data-copiar-gate]');
    if(c){ const g = D.gates.find(x => x.n === c.dataset.copiarGate); copiar(g.prompt, c, 'prompt do gate '+g.n+' copiado'); return; }
    const m = e.target.closest('[data-marcar]');
    if(m){
      const n = m.dataset.marcar;
      feitos.has(n) ? feitos.delete(n) : feitos.add(n);
      m.textContent = feitos.has(n) ? 'desmarcar' : 'marcar como rodado';
      document.querySelector('.pad[data-g="'+n+'"]').dataset.feito = feitos.has(n) ? '1' : '0';
      return;
    }
    if(e.target.closest('[data-bloco]')) montarBloco(e.target.closest('[data-bloco]'));
  });
}
function montarBloco(btn){
  const hoje = new Date().toISOString().slice(2,10).replace(/-/g,'');
  const rodados = D.gates.filter(g => feitos.has(g.n)).map(g => g.n+' '+g.nome).join(' · ') || 'nenhum marcado';
  copiar('## '+hoje+' · <agente>\nGATES RODADOS: '+rodados +
    '\nFIZ: \nABERTO: \nPRÓXIMO PASSO: \nTOQUEI: \nTRAVADO_POR: livre\n', btn, 'bloco de handoff copiado');
}

/* ---------------- índice ---------------- */
const VIRTUAIS = [
  {id:'@inicio', nome:'começar por aqui'},
  {id:'@mecanicas', nome:'mecânicas e comandos'},
  {id:'@modelos', nome:'modelos de arquivo'},
  {id:'@integridade', nome:'integridade dos arquivos'}
];
function montarIndice(){
  let html = '<div class="grupo"><h4>painel</h4>' +
    VIRTUAIS.map(v => '<button class="item" data-abrir="'+v.id+'">'+esc(v.nome)+'</button>').join('') + '</div>';
  html += D.grupos.map(g => '<div class="grupo"><h4>'+esc(g.titulo)+'</h4>' +
    g.itens.map(c => '<button class="item" data-abrir="'+esc(c)+'">'+esc(c.split('/').pop())+'</button>').join('') +
    '</div>').join('');
  $('#indice').innerHTML = html;
  $('#indice').addEventListener('click', e => {
    const b = e.target.closest('[data-abrir]'); if(b) abrir(b.dataset.abrir);
  });
}

/* ---------------- leitor ---------------- */
let atual = '@inicio';
function marcarAtual(id){
  document.querySelectorAll('.item').forEach(i => i.setAttribute('aria-current', i.dataset.abrir === id ? 'true' : 'false'));
}
function cabecalho(titulo, meta, botoes){
  return '<div class="leitor-topo"><h2>'+esc(titulo)+'</h2>' + (botoes||'') +
    '<div class="meta">'+esc(meta||'')+'</div></div>';
}
function abrir(id){
  atual = id; marcarAtual(id);
  const L = $('#leitor');
  if(id === '@inicio') L.innerHTML = telaInicio();
  else if(id === '@mecanicas') L.innerHTML = telaMecanicas();
  else if(id === '@modelos') L.innerHTML = telaModelos();
  else if(id === '@integridade') L.innerHTML = telaIntegridade();
  else {
    const a = D.arquivos.find(x => x.caminho === id);
    if(!a){ L.innerHTML = '<p>arquivo não encontrado.</p>'; return; }
    L.innerHTML = cabecalho(a.caminho, a.bytes.toLocaleString('pt-BR')+' bytes · sha '+a.sha+' · '+a.mtime,
      '<div class="btn-linha"><button class="btn" data-copiar-arq="'+esc(a.caminho)+'">copiar arquivo</button>' +
      '<button class="btn" data-copiar-caminho="'+esc(a.caminho)+'">copiar caminho</button></div>') +
      '<div class="md">'+md(a.texto)+'</div>';
  }
  aplicarBusca();
  window.scrollTo({top:0, behavior:'instant'});
}
function telaInicio(){
  const a = D.arquivos.find(x => x.caminho.startsWith('AUDITORIA'));
  return cabecalho('Painel MEGABRAIN', D.versao + ' · gerado em ' + D.gerado) +
    '<div class="aviso">Este painel não guarda nada no navegador. No megabrain, estado mora em ' +
    '<code>ESTADO.md</code>, <code>HANDOFF.md</code> e <code>DECISOES.md</code> — o painel monta o bloco, você cola.</div>' +
    '<div class="btn-linha" style="margin:18px 0 26px">' +
    '<button class="btn btn-sinal" data-abrir="@mecanicas">ver os comandos</button>' +
    '<button class="btn" data-abrir="skills/megabrain/SKILL.md">abrir o protocolo</button>' +
    '<button class="btn" data-abrir="@integridade">conferir integridade</button>' +
    '<button class="btn" data-copiar-portatil>copiar prompt portátil</button></div>' +
    '<div class="md">' + (a ? md(a.texto) : '<p>Auditoria não encontrada no pacote.</p>') + '</div>';
}
function telaMecanicas(){
  return cabecalho('Mecânicas e comandos', 'raiz e projeto vêm dos campos lá em cima') +
    '<div class="aviso">Edite <strong>raiz</strong> e <strong>projeto</strong> no topo: todo comando é copiado já com o caminho certo.</div>' +
    D.mecanicas.map(m => '<div class="cartao"><h3>'+esc(m.titulo)+'</h3><div class="sobre">'+esc(m.sobre)+'</div>' +
      m.comandos.map(c => '<div class="cmd"><div class="rot">'+esc(c.rotulo)+'</div>' +
        '<code data-cmd="'+esc(c.cmd)+'">'+esc(resolver(c.cmd))+'</code>' +
        '<button class="btn" data-copiar-cmd="'+esc(c.cmd)+'">copiar</button></div>').join('') +
      '</div>').join('');
}
function telaModelos(){
  return cabecalho('Modelos de arquivo', 'os quatro arquivos de estado do Gate 0 e do Gate 6') +
    D.modelos.map(m => '<div class="cartao"><h3>'+esc(m.nome)+'</h3>' +
      '<div class="cmd" style="align-items:flex-start"><pre style="flex:1;margin:0;background:var(--breu);border:1px solid var(--risco);padding:12px;font-family:var(--mono);font-size:12px;white-space:pre-wrap">'+esc(m.texto)+'</pre>' +
      '<button class="btn" data-copiar-modelo="'+esc(m.nome)+'">copiar</button></div></div>').join('');
}
function telaIntegridade(){
  return cabecalho('Integridade dos arquivos', 'Gate 5 — compare com a cópia que o agente carregou') +
    '<div class="aviso">Se o hash da skill instalada no seu agente não bater com o de <code>skills/megabrain/SKILL.md</code>, ' +
    'a cópia que roda não é a do repositório. Foi exatamente isso que a auditoria encontrou.</div>' +
    '<table><thead><tr><th>arquivo</th><th>bytes</th><th>sha256 (16)</th><th>modificado</th></tr></thead><tbody>' +
    D.arquivos.map(a => '<tr><td class="mono">'+esc(a.caminho)+'</td><td class="mono">'+a.bytes.toLocaleString('pt-BR') +
      '</td><td class="mono">'+a.sha+'</td><td class="mono">'+a.mtime+'</td></tr>').join('') +
    '</tbody></table>';
}

/* ---------------- busca ---------------- */
function aplicarBusca(){
  const q = $('#busca').value.trim().toLowerCase();
  document.querySelectorAll('.item').forEach(i => {
    if(!q || i.dataset.abrir.startsWith('@')){ i.classList.remove('oculto'); return; }
    const a = D.arquivos.find(x => x.caminho === i.dataset.abrir);
    const bate = i.textContent.toLowerCase().includes(q) || (a && a.texto.toLowerCase().includes(q));
    i.classList.toggle('oculto', !bate);
  });
  document.querySelectorAll('.md .marca-busca').forEach(m => m.replaceWith(m.textContent));
  if(q.length < 2) return;
  const alvo = $('#leitor .md'); if(!alvo) return;
  const andar = document.createTreeWalker(alvo, NodeFilter.SHOW_TEXT);
  const nos = []; let n;
  while(n = andar.nextNode()) if(n.nodeValue.toLowerCase().includes(q)) nos.push(n);
  nos.slice(0, 300).forEach(no => {
    const frag = document.createDocumentFragment();
    let resto = no.nodeValue, k;
    while((k = resto.toLowerCase().indexOf(q)) !== -1){
      frag.append(resto.slice(0, k));
      const s = document.createElement('span'); s.className = 'marca-busca'; s.textContent = resto.substr(k, q.length);
      frag.append(s); resto = resto.slice(k + q.length);
    }
    frag.append(resto); no.replaceWith(frag);
  });
}

/* ---------------- eventos globais ---------------- */
document.addEventListener('click', e => {
  const ab = e.target.closest('[data-abrir]');
  if(ab && !e.target.closest('.indice')){ abrir(ab.dataset.abrir); return; }
  const cc = e.target.closest('[data-copiar-cmd]');
  if(cc){ copiar(resolver(cc.dataset.copiarCmd), cc, 'comando copiado'); return; }
  const ca = e.target.closest('[data-copiar-arq]');
  if(ca){ const a = D.arquivos.find(x => x.caminho === ca.dataset.copiarArq); copiar(a.texto, ca, 'arquivo copiado'); return; }
  const cp = e.target.closest('[data-copiar-caminho]');
  if(cp){ copiar(raizAtual()+'/'+cp.dataset.copiarCaminho, cp, 'caminho copiado'); return; }
  const cm = e.target.closest('[data-copiar-modelo]');
  if(cm){ const m = D.modelos.find(x => x.nome === cm.dataset.copiarModelo); copiar(m.texto, cm, 'modelo copiado'); return; }
  const pp = e.target.closest('[data-copiar-portatil]');
  if(pp){
    const a = D.arquivos.find(x => x.caminho.includes('PROMPT-PORTATIL'));
    a ? copiar(a.texto, pp, 'prompt portátil copiado') : toast('prompt portátil não encontrado');
  }
});
$('#busca').addEventListener('input', aplicarBusca);
['#raiz','#projeto'].forEach(s => $(s).addEventListener('input', () => {
  if(atual === '@mecanicas') $('#leitor').innerHTML = telaMecanicas();
}));
document.addEventListener('keydown', e => {
  if(e.key === '/' && !/input|textarea/i.test(document.activeElement.tagName)){ e.preventDefault(); $('#busca').focus(); }
  if(e.key === 'Escape' && document.activeElement === $('#busca')){ $('#busca').value = ''; aplicarBusca(); $('#busca').blur(); }
});

/* ---------------- início ---------------- */
$('#raiz').value = D.raiz;
$('#rodape').textContent = 'gerado por bin/mb-painel.py em ' + D.gerado + ' · ' + D.arquivos.length +
  ' arquivos · ' + D.versao + ' · tecle / para buscar';
montarTrilha(); montarIndice(); abrir('@inicio');
</script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--saida", default="PAINEL-MEGABRAIN.html")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    if not (raiz / "VERSAO.txt").exists():
        print(f"{raiz} nao parece a raiz do megabrain (sem VERSAO.txt).")
        return 1
    arquivos = coletar(raiz)
    saida = raiz / args.saida
    saida.write_text(montar(raiz, arquivos), encoding="utf-8")
    print(f"painel: {saida}  ({saida.stat().st_size // 1024} KB, {len(arquivos)} arquivos)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
