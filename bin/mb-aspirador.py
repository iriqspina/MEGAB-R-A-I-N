#!/usr/bin/env python3
"""
mb-aspirador.py — limpeza mecanica e nao destrutiva de codigo do MEGABRAIN.

Default: dry-run. Lista o que seria corrigido sem alterar nenhum arquivo.
Com --aplicar: faz backup do original e aplica apenas correcoes mecanicas
seguras (espacos, quebras, linhas em branco). Imports nao usados sao
reportados, mas nunca removidos automaticamente — exigem revisao humana.

Nunca apaga arquivos. Nunca muda logica, nomes ou comentarios.

Uso:
    python bin/mb-aspirador.py [--dir CAMINHO] [--aplicar] [--ext py,js,ts]
"""

import argparse
import ast
import datetime as dt
import html
import json
import shutil
from pathlib import Path
from typing import Iterable

import mb_utils as u

DEFAULT_EXTS = {"py", "js", "ts", "jsx", "tsx", "md", "txt", "yaml", "yml", "json", "css", "scss"}
BACKUP_DIR_NAME = ".mb-aspirador"
TAB_SIZE = 4
INFO_MAX_BYTES = 100_000  # limite por arquivo informativo anexado
INFO_EXTS = {"md", "txt"}
INFO_IGNORAR_NOME = {".env", ".env.local", ".env.production", ".env.development"}


class Problema:
    def __init__(self, tipo: str, linha: int | None, descricao: str):
        self.tipo = tipo
        self.linha = linha
        self.descricao = descricao


def extensao(caminho: Path) -> str:
    return caminho.suffix.lstrip(".").lower()


def _ler_texto(caminho: Path) -> str | None:
    """Lê texto de `caminho` uma única vez, retornando None se não for texto."""
    try:
        return caminho.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None
    except OSError:
        return None


def detectar_trailing_whitespace(linhas: list[str]) -> list[Problema]:
    probs = []
    for i, linha in enumerate(linhas, start=1):
        sem_quebra = linha.rstrip("\n\r")
        if sem_quebra and sem_quebra != sem_quebra.rstrip():
            probs.append(Problema("trailing-whitespace", i, "espacos no final da linha"))
    return probs


def detectar_linhas_branco_fim(linhas: list[str]) -> list[Problema]:
    if not linhas:
        return []
    vazias_no_fim = 0
    for linha in reversed(linhas):
        if linha.strip() == "":
            vazias_no_fim += 1
        else:
            break
    if vazias_no_fim > 1:
        return [Problema("linhas-branco-fim", len(linhas), f"{vazias_no_fim} linhas vazias no final (manter 1)")]
    return []


def detectar_tabs(linhas: list[str]) -> list[Problema]:
    probs = []
    usa_espacos = any(linha.startswith(" ") and linha.strip() for linha in linhas)
    for i, linha in enumerate(linhas, start=1):
        if "\t" in linha and usa_espacos:
            probs.append(Problema("tabs-mistos", i, "tab em arquivo que ja usa espacos"))
            break  # basta um; correcao eh global
    return probs


def detectar_quebra_inconsistente(texto: str) -> list[Problema]:
    if "\r\n" in texto and "\n" in texto.replace("\r\n", ""):
        return [Problema("quebra-mista", None, "arquivo mistura CRLF e LF")]
    return []


def detectar_python_morto(texto: str) -> list[Problema]:
    probs = []
    try:
        arvore = ast.parse(texto)
    except SyntaxError as e:
        return [Problema("syntax-error", e.lineno, f"erro de sintaxe: {e.msg}")]

    imports = {}
    for node in ast.walk(arvore):
        if isinstance(node, ast.Import):
            for alias in node.names:
                nome = alias.asname or alias.name.split(".")[0]
                imports[nome] = node.lineno
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                nome = alias.asname or alias.name
                imports[nome] = node.lineno

    usados = set()
    for node in ast.walk(arvore):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            usados.add(node.id)

    for nome, linha in imports.items():
        if nome not in usados:
            probs.append(Problema("import-nao-usado", linha, f"import '{nome}' nao usado"))

    return probs


def analisar(caminho: Path) -> tuple[list[Problema], list[str] | None]:
    texto = _ler_texto(caminho)
    if texto is None:
        return [Problema("nao-texto", None, "arquivo binario ou ilegivel - ignorado")], None

    linhas = texto.splitlines(keepends=True)
    probs = []

    probs.extend(detectar_trailing_whitespace(linhas))
    probs.extend(detectar_linhas_branco_fim(linhas))
    probs.extend(detectar_tabs(linhas))
    probs.extend(detectar_quebra_inconsistente(texto))

    if extensao(caminho) == "py":
        probs.extend(detectar_python_morto(texto))

    return probs, linhas


def corrigir(linhas: list[str], probs: list[Problema], caminho: Path) -> list[str]:
    tipos = {p.tipo for p in probs}

    if "trailing-whitespace" in tipos:
        novas = []
        for linha in linhas:
            if linha.endswith("\r\n"):
                novas.append(linha[:-2].rstrip() + "\r\n")
            elif linha.endswith("\n"):
                novas.append(linha[:-1].rstrip() + "\n")
            elif linha.endswith("\r"):
                novas.append(linha[:-1].rstrip() + "\r")
            else:
                novas.append(linha.rstrip())
        linhas = novas

    if "tabs-mistos" in tipos:
        novas = []
        for linha in linhas:
            nova = ""
            i = 0
            while i < len(linha) and linha[i] in " \t":
                if linha[i] == "\t":
                    espacos = TAB_SIZE - (len(nova) % TAB_SIZE)
                    nova += " " * espacos
                else:
                    nova += linha[i]
                i += 1
            novas.append(nova + linha[i:])
        linhas = novas

    if "quebra-mista" in tipos:
        linhas = [l.replace("\r\n", "\n") for l in linhas]
        linhas = [l.replace("\r", "\n") for l in linhas]

    if "linhas-branco-fim" in tipos:
        while len(linhas) > 1 and linhas[-1].strip() == "":
            linhas.pop()
        if linhas and not linhas[-1].endswith("\n"):
            linhas[-1] += "\n"
        elif not linhas:
            linhas = [""]

    return linhas


def arquivos_no_diretorio(raiz: Path, exts: set[str]) -> Iterable[Path]:
    ignorar = {".git", ".venv", "node_modules", "__pycache__", BACKUP_DIR_NAME}
    yield from u.walk_files(raiz, exts=exts, ignorar=ignorar)


def e_informativo_seguro(caminho: Path, raiz: Path) -> bool:
    if caminho.name in INFO_IGNORAR_NOME:
        return False
    if caminho.suffix.lstrip(".").lower() not in INFO_EXTS:
        return False
    if _ler_texto(caminho) is None:
        return False
    try:
        if caminho.stat().st_size > INFO_MAX_BYTES:
            return False
    except OSError:
        return False
    rel = str(caminho.relative_to(raiz)).replace("\\", "/")
    # pula relatorios do proprio aspirador para nao poluir
    if rel.startswith(f"{BACKUP_DIR_NAME}/relatorio-"):
        return False
    return True


def coletar_informacionais(raiz: Path, timestamp: str) -> list[tuple[str, str, str]]:
    """
    Coleta notas locais da ferramenta (.md/.txt) de .mb-aspirador/.
    Não coleta arquivos da raiz do projeto — o relatório DNA é quem carrega
    a documentação do projeto; o aspirador apenas registra notas suas.
    """
    encontrados: list[tuple[str, str, str]] = []
    base = raiz / BACKUP_DIR_NAME
    if not base.exists():
        return encontrados

    for caminho in sorted(base.iterdir()):
        if not caminho.is_file():
            continue
        if not e_informativo_seguro(caminho, raiz):
            continue
        rel = str(caminho.relative_to(raiz)).replace("\\", "/")
        formato = "markdown" if extensao(caminho) == "md" else "texto"
        conteudo = caminho.read_text(encoding="utf-8")
        encontrados.append((rel, conteudo, formato))

    return encontrados


def formatar_anexo_html(rel: str, conteudo: str, formato: str) -> str:
    titulo = html.escape(rel)
    if formato == "markdown":
        corpo = markdown_para_html_basico(conteudo)
    else:
        corpo = f'<pre><code>{html.escape(conteudo)}</code></pre>'
    return f'<details class="anexo"><summary>{titulo}</summary><div>{corpo}</div></details>'


def gerar_relatorio(raiz: Path, resultados: list[tuple[Path, list[Problema]]], aplicado: bool, timestamp: str, informacionais: list[tuple[str, str, str]] | None = None) -> str:
    linhas = [
        f"# Relatorio mb-aspirador — {timestamp}",
        "",
        f"- Diretorio: `{raiz}`",
        f"- Modo: {'aplicado (com backup)' if aplicado else 'dry-run (apenas leitura)'}",
        f"- Arquivos analisados: {len(resultados)}",
        "",
    ]

    com_problema = [(c, p) for c, p in resultados if p]
    linhas.append(f"## Resumo — {len(com_problema)} arquivo(s) com sugestoes")
    linhas.append("")

    if not com_problema:
        linhas.append("Nenhum problema mecanico encontrado.")
    else:
        for caminho, probs in com_problema:
            rel = caminho.relative_to(raiz)
            linhas.append(f"### `{rel}`")
            linhas.append("")
            for pr in probs:
                pos = f"linha {pr.linha}" if pr.linha else "arquivo"
                linhas.append(f"- [{pr.tipo}] {pos}: {pr.descricao}")
            linhas.append("")

    info = informacionais or []
    if info:
        linhas.append("## Informacionais anexados")
        linhas.append("")
        for rel, _, fmt in info:
            linhas.append(f"- `{rel}` ({fmt})")
        linhas.append("")

    return "\n".join(linhas)


def contagem_por_tipo(resultados: list[tuple[Path, list[Problema]]]) -> dict[str, int]:
    contagem: dict[str, int] = {}
    for _, probs in resultados:
        for p in probs:
            contagem[p.tipo] = contagem.get(p.tipo, 0) + 1
    return contagem


def snippet_html(linhas: list[str], num_linha: int, contexto: int = 2) -> str:
    """Retorna trecho HTML com a linha problemática destacada."""
    inicio = max(0, num_linha - contexto - 1)
    fim = min(len(linhas), num_linha + contexto)
    partes = ['<div class="snippet"><pre><code>']
    for i in range(inicio, fim):
        conteudo = linhas[i].rstrip("\n\r")
        conteudo_visivel = conteudo.replace("\t", "→   ")
        numero = i + 1
        marcado = numero == num_linha
        classe = "line hit" if marcado else "line"
        seta = "▶ " if marcado else "  "
        partes.append(
            f'<span class="{classe}"><span class="num">{seta}{numero:4}</span>'
            f'{html.escape(conteudo_visivel)}</span>'
        )
    partes.append("</code></pre></div>")
    return "\n".join(partes)


def markdown_para_html_basico(texto: str) -> str:
    """Converte Markdown simples para HTML basico (paragrafos, listas, negrito, code)."""
    linhas = texto.splitlines()
    html_linhas: list[str] = []
    dentro_lista = False

    for linha in linhas:
        if linha.startswith("# "):
            html_linhas.append(f"<h1>{html.escape(linha[2:])}</h1>")
        elif linha.startswith("## "):
            html_linhas.append(f"<h2>{html.escape(linha[3:])}</h2>")
        elif linha.startswith("### "):
            html_linhas.append(f"<h3>{html.escape(linha[4:])}</h3>")
        elif linha.startswith("- "):
            if not dentro_lista:
                html_linhas.append("<ul>")
                dentro_lista = True
            item = linha[2:]
            item = html.escape(item)
            item = item.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
            item = item.replace("`", "<code>", 1).replace("`", "</code>", 1)
            html_linhas.append(f"<li>{item}</li>")
        elif linha.strip() == "":
            if dentro_lista:
                html_linhas.append("</ul>")
                dentro_lista = False
            html_linhas.append("")
        else:
            if dentro_lista:
                html_linhas.append("</ul>")
                dentro_lista = False
            linha = html.escape(linha)
            linha = linha.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
            # code inline: par simples de backticks
            while "`" in linha:
                linha = linha.replace("`", "<code>", 1).replace("`", "</code>", 1)
            html_linhas.append(f"<p>{linha}</p>")

    if dentro_lista:
        html_linhas.append("</ul>")

    return "\n".join(html_linhas)


def gerar_relatorio_html(
    raiz: Path,
    resultados: list[tuple[Path, list[Problema]]],
    aplicado: bool,
    timestamp: str,
    documentacao: str,
    informacionais: list[tuple[str, str, str]] | None = None,
) -> str:
    com_problema = [(c, p) for c, p in resultados if p]
    sem_problema = [(c, p) for c, p in resultados if not p]
    total_arquivos = len(resultados)
    contagem = contagem_por_tipo(resultados)
    data_iso = dt.datetime.now().isoformat()
    info = informacionais or []

    json_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "name": f"Relatorio mb-aspirador — {timestamp}",
        "dateCreated": data_iso,
        "about": {
            "@type": "SoftwareApplication",
            "name": "mb-aspirador",
        },
        "variableMeasured": [
            {"propertyID": "diretorio", "value": str(raiz)},
            {"propertyID": "modo", "value": "aplicado" if aplicado else "dry-run"},
            {"propertyID": "arquivos_analisados", "value": total_arquivos},
            {"propertyID": "arquivos_com_problema", "value": len(com_problema)},
            {"propertyID": "contagem_por_tipo", "value": contagem},
            {"propertyID": "informacionais_anexados", "value": [rel for rel, _, _ in info]},
        ],
    }, ensure_ascii=False, indent=2)

    css = """
    :root { --bg:#0d1117; --surface:#161b22; --border:#30363d; --text:#c9d1d9; --muted:#8b949e; --accent:#58a6ff; --ok:#238636; --warn:#d29922; --danger:#da3633; }
    * { box-sizing: border-box; }
    body { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; max-width: 1100px; margin: 0 auto; padding: 2rem; }
    header { border-bottom: 1px solid var(--border); padding-bottom: 1rem; margin-bottom: 2rem; }
    h1 { margin: 0 0 .5rem; font-size: 1.6rem; }
    .badge { display: inline-block; padding: .25rem .6rem; border-radius: 999px; font-size: .75rem; font-weight: 600; text-transform: uppercase; }
    .dry { background: var(--warn); color: #000; }
    .applied { background: var(--ok); color: #fff; }
    .meta { color: var(--muted); font-size: .9rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; margin: 1.5rem 0; }
    .card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; }
    .card .value { font-size: 1.6rem; font-weight: 700; color: var(--accent); }
    .card .label { font-size: .8rem; color: var(--muted); text-transform: uppercase; }
    section { margin: 2rem 0; }
    h2 { font-size: 1.25rem; border-bottom: 1px solid var(--border); padding-bottom: .4rem; }
    h3 { font-size: 1.05rem; margin-top: 1.5rem; color: var(--accent); }
    table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
    th, td { text-align: left; padding: .5rem; border-bottom: 1px solid var(--border); }
    th { color: var(--muted); font-weight: 500; }
    .ok { color: var(--ok); }
    .problem { color: var(--warn); }
    .snippet { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; overflow-x: auto; margin: .5rem 0; }
    .snippet pre { margin: 0; padding: .75rem; }
    .line { display: block; white-space: pre; color: var(--text); }
    .line.hit { background: rgba(218,54,51,.15); }
    .num { color: var(--muted); user-select: none; display: inline-block; width: 3.5rem; }
    .tag { display: inline-block; padding: .1rem .35rem; border-radius: 4px; font-size: .75rem; background: var(--border); color: var(--text); margin-right: .25rem; }
    .tag.trailing-whitespace { background: #388bfd33; }
    .tag.tabs-mistos { background: #a371f733; }
    .tag.import-nao-usado { background: #d2992233; }
    .tag.syntax-error { background: #da363333; }
    .ai-box { background: var(--surface); border-left: 4px solid var(--accent); padding: 1rem; border-radius: 0 8px 8px 0; }
    details { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; margin: 1rem 0; }
    summary { padding: .75rem 1rem; cursor: pointer; font-weight: 600; }
    details > div { padding: 0 1rem 1rem; }
    details.anexo summary { color: var(--accent); }
    details.anexo pre { background: var(--bg); padding: .75rem; border-radius: 6px; overflow-x: auto; }
    code { font-family: ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size: .9em; }
    .muted { color: var(--muted); }
    """

    # Resumo por arquivo (tabela)
    linhas_tabela = []
    for caminho, probs in resultados:
        rel = html.escape(str(caminho.relative_to(raiz)))
        if probs:
            tipos = ", ".join(sorted({p.tipo for p in probs}))
            linhas_tabela.append(f'<tr><td><code>{rel}</code></td><td class="problem">{len(probs)}</td><td><code>{html.escape(tipos)}</code></td></tr>')
        else:
            linhas_tabela.append(f'<tr><td><code>{rel}</code></td><td class="ok">0</td><td class="muted">—</td></tr>')

    # Detalhes por arquivo
    detalhes = []
    for caminho, probs in com_problema:
        rel = html.escape(str(caminho.relative_to(raiz)))
        detalhes.append(f'<h3 id="{html.escape(rel)}"><code>{rel}</code></h3>')
        texto = u.safe_read_text(caminho) or ""
        linhas_arquivo = texto.splitlines(keepends=True)
        for p in probs:
            tipo_tag = f'<span class="tag {p.tipo}">{p.tipo}</span>'
            pos = f"linha {p.linha}" if p.linha else "arquivo"
            detalhes.append(f'<p>{tipo_tag} <strong>{pos}</strong>: {html.escape(p.descricao)}</p>')
            if p.linha and 1 <= p.linha <= len(linhas_arquivo):
                detalhes.append(snippet_html(linhas_arquivo, p.linha))

    if not detalhes:
        detalhes.append('<p class="ok">Nenhum problema mecanico encontrado.</p>')

    contagem_html = ""
    if contagem:
        itens = [f'<div class="card"><div class="value">{v}</div><div class="label">{html.escape(k)}</div></div>' for k, v in sorted(contagem.items())]
        contagem_html = '<div class="grid">' + "".join(itens) + '</div>'

    badge = '<span class="badge dry">dry-run</span>' if not aplicado else '<span class="badge applied">aplicado</span>'

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Relatorio mb-aspirador — {timestamp}</title>
<meta name="generator" content="mb-aspirador">
<meta name="mb-aspirador:timestamp" content="{timestamp}">
<meta name="mb-aspirador:diretorio" content="{html.escape(str(raiz))}">
<meta name="mb-aspirador:modo" content="{'aplicado' if aplicado else 'dry-run'}">
<meta name="mb-aspirador:arquivos-analisados" content="{total_arquivos}">
<meta name="mb-aspirador:arquivos-com-problema" content="{len(com_problema)}">
<script type="application/ld+json">{json_ld}</script>
<style>{css}</style>
</head>
<body>
<header>
  <h1>Relatorio mb-aspirador {badge}</h1>
  <p class="meta">Gerado em {html.escape(data_iso)} · Diretorio: <code>{html.escape(str(raiz))}</code></p>
</header>

<section>
  <h2>Resumo</h2>
  <div class="grid">
    <div class="card"><div class="value">{total_arquivos}</div><div class="label">arquivos analisados</div></div>
    <div class="card"><div class="value">{len(com_problema)}</div><div class="label">com sugestoes</div></div>
    <div class="card"><div class="value">{len(sem_problema)}</div><div class="label">limpos</div></div>
    <div class="card"><div class="value">{sum(len(p) for _, p in resultados)}</div><div class="label">problemas encontrados</div></div>
  </div>
  {contagem_html}
</section>

<section class="ai-box">
  <h2>Para a IA que ler este relatorio</h2>
  <p>Este e o relatorio de uma ferramenta de limpeza <strong>nao destrutiva</strong>. O modo atual e
  <strong>{'aplicado' if aplicado else 'dry-run'}</strong>. Correcoes mecanicas seguras
  (espacos, quebras, linhas em branco, tabs) {'foram aplicadas com backup' if aplicado else 'seriam aplicadas com --aplicar'}.
  Imports nao usados sao apenas reportados; nunca remova codigo sem revisao humana.</p>
  <p>Proxima acao sugerida: {('revisar o diff entre cada arquivo e seu backup em .mb-aspirador/backups/' + timestamp + '/') if aplicado else 'rodar python bin/mb-aspirador.py --dir <pasta> --aplicar se o usuario confirmar'}.</p>
</section>

<section>
  <h2>Arquivos analisados</h2>
  <table>
    <thead><tr><th>Arquivo</th><th>Problemas</th><th>Tipos</th></tr></thead>
    <tbody>{''.join(linhas_tabela)}</tbody>
  </table>
</section>

<section>
  <h2>Detalhes</h2>
  {''.join(detalhes)}
</section>

<details>
  <summary>Documentacao do mb-aspirador</summary>
  <div>{documentacao}</div>
</details>

<section>
  <h2>Notas locais do aspirador</h2>
  <p class="muted">Arquivos <code>.md</code>/<code>.txt</code> encontrados em <code>{BACKUP_DIR_NAME}/</code>. Ignorados: env files, relatórios antigos e arquivos maiores que {INFO_MAX_BYTES // 1000} KB. A documentacao do projeto vive no relatorio DNA, nao aqui.</p>
  {''.join(formatar_anexo_html(rel, conteudo, fmt) for rel, conteudo, fmt in info) if info else '<p class="muted">Nenhuma nota local encontrada.</p>'}
</section>

<footer class="meta">
  <p>mb-aspirador — MEGABRAIN · relatorio em Markdown tambem disponivel em <code>.mb-aspirador/relatorio-{timestamp}.md</code></p>
</footer>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description="Aspirador de codigo nao destrutivo do MEGABRAIN")
    ap.add_argument("--dir", default=".", help="pasta a varrer (default: atual)")
    ap.add_argument("--ext", default=",".join(sorted(DEFAULT_EXTS)), help="extensoes separadas por virgula")
    ap.add_argument("--aplicar", action="store_true", help="aplica correcoes apos backup (default: dry-run)")
    ap.add_argument("--backup-dir", default=None, help="pasta de backup (default: .mb-aspirador/backups/...)")
    args = ap.parse_args()

    raiz = Path(args.dir).resolve()
    if not raiz.is_dir():
        u.die(f"diretorio nao encontrado: {raiz}")

    # Backup opcional customizado deve ficar dentro da raiz varrida.
    if args.backup_dir:
        backup_custom = Path(args.backup_dir).resolve()
        try:
            u.resolve_within(backup_custom, raiz)
        except ValueError as e:
            u.die(f"--backup-dir fora da pasta varrida: {e}")

    exts = u.parse_csv_extensoes(args.ext)
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_base = Path(args.backup_dir) if args.backup_dir else raiz / BACKUP_DIR_NAME / "backups" / timestamp

    resultados: list[tuple[Path, list[Problema]]] = []

    for caminho in sorted(arquivos_no_diretorio(raiz, exts)):
        probs, linhas = analisar(caminho)
        resultados.append((caminho, probs))

        if not probs or not linhas:
            continue

        tipos_seguros = {"trailing-whitespace", "linhas-branco-fim", "tabs-mistos", "quebra-mista"}
        corrigiveis = [p for p in probs if p.tipo in tipos_seguros]
        if args.aplicar and corrigiveis:
            texto_original = "".join(linhas)
            novo = corrigir(linhas, corrigiveis, caminho)
            novo_texto = "".join(novo)
            if novo_texto != texto_original:
                destino_backup = backup_base / caminho.relative_to(raiz)
                destino_backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(caminho, destino_backup)
                caminho.write_text(novo_texto, encoding="utf-8", newline="")

    # Carrega documentacao embutida e informacionais do projeto para o relatorio
    doc_path = Path(__file__).parent.parent / "referencias" / "260813_aspirador-codigo.md"
    documentacao = "Documentacao nao encontrada."
    if doc_path.exists():
        doc_md = doc_path.read_text(encoding="utf-8")
        documentacao = markdown_para_html_basico(doc_md)

    informacionais = coletar_informacionais(raiz, timestamp)

    relatorio_md = gerar_relatorio(raiz, resultados, args.aplicar, timestamp, informacionais)
    relatorio_html = gerar_relatorio_html(raiz, resultados, args.aplicar, timestamp, documentacao, informacionais)

    base = raiz / BACKUP_DIR_NAME
    base.mkdir(parents=True, exist_ok=True)
    (base / f"relatorio-{timestamp}.md").write_text(relatorio_md, encoding="utf-8")
    (base / f"relatorio-{timestamp}.html").write_text(relatorio_html, encoding="utf-8")

    print(relatorio_md)
    print(f"\nRelatorios salvos em:")
    print(f"  Markdown: {base / f'relatorio-{timestamp}.md'}")
    print(f"  HTML:     {base / f'relatorio-{timestamp}.html'}")
    if args.aplicar:
        print(f"Backups em: {backup_base}")


if __name__ == "__main__":
    main()
