"""Visual research readout; raw source stays available in each collapsed subject.
Uso: render_research_report(job, text, sources, created_at) -> HTML seguro.
Somente biblioteca padrão. Não interpreta HTML do modelo nem executa scripts.
"""
from html import escape
import re
from urllib.parse import urlsplit


def _inline(text):
    # Links viram texto, porque a prévia isolada bloqueia navegação externa.
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 — \2', str(text))
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'Imagem citada: \1 — \2', text)
    value = escape(text)
    value = re.sub(r'\*\*([^*\n]+)\*\*', r'<strong>\1</strong>', value)
    value = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', value)
    return value


def _body(lines):
    out, paragraph, listed, fenced, code = [], [], False, False, []
    def flush():
        if paragraph:
            out.append('<p>' + _inline(' '.join(paragraph)) + '</p>')
            paragraph.clear()
    def close_list():
        nonlocal listed
        if listed:
            out.append('</ul>'); listed = False
    for line in lines:
        if line.lstrip().startswith('```'):
            flush(); close_list()
            if fenced:
                out.append('<pre><code>' + escape('\n'.join(code)) + '</code></pre>'); code = []
            fenced = not fenced
            continue
        if fenced:
            code.append(line); continue
        bullet = re.match(r'^\s*(?:[-*+]\s+|\d+[.)]\s+)(.+)', line)
        if bullet:
            flush()
            if not listed: out.append('<ul>'); listed = True
            out.append('<li>' + _inline(bullet[1]) + '</li>')
        elif not line.strip():
            flush(); close_list()
        else:
            close_list(); paragraph.append(line.strip())
    flush(); close_list()
    if code: out.append('<pre><code>' + escape('\n'.join(code)) + '</code></pre>')
    return ''.join(out)


def _public_source(source):
    url = str(source.get('url', ''))
    try: parsed = urlsplit(url)
    except ValueError: return False
    return bool(parsed.scheme in {'http', 'https'} and parsed.hostname and not parsed.username and not parsed.password)


def render_research_report(job, text, sources, created_at):
    sections, title, lines, fenced = [], 'Leitura da pesquisa', [], False
    for line in str(text).splitlines():
        if line.lstrip().startswith('```'): fenced = not fenced
        heading = re.match(r'^#{1,6}\s+(.+?)\s*#*$', line) if not fenced else None
        if heading:
            if any(v.strip() for v in lines): sections.append((title, lines))
            title, lines = heading[1][:140], []
        else: lines.append(line)
    if any(v.strip() for v in lines): sections.append((title, lines))
    if not sections: sections = [('Sem texto de pesquisa', ['A execução ainda não registrou uma síntese.'])]
    sources = [source for source in sources if isinstance(source, dict) and _public_source(source)]
    opened = sum(source.get('retrieved') is True and source.get('retrieval_kind') == 'page_fetch' for source in sources)
    searched = sum(source.get('retrieval_kind') == 'search_result' for source in sources)
    cards = []
    mark = '<svg class="mark" viewBox="0 0 32 32" aria-hidden="true"><rect x="5" y="4" width="22" height="24" rx="5"/><path d="M11 11h10M11 16h10M11 21h6"/></svg>'
    for heading, content in sections:
        # Preserva toda a fonte no detalhe; resumo é somente o início literal.
        first = next((line.strip() for line in content if line.strip() and not line.lstrip().startswith('```')), '')
        first = re.sub(r'^[-*+]\s+|^\d+[.)]\s+', '', first)
        short = first if len(first) <= 230 else first[:230].rsplit(' ', 1)[0] + '…'
        cards.append('<article><header>' + mark + '<h2>' + _inline(heading) + '</h2></header><p class="lead">' + _inline(short) + '</p><details><summary>Ler detalhes deste assunto</summary>' + _body(content) + '</details></article>')
    source_rows = []
    for source in sources:
        label = 'Página aberta' if source.get('retrieved') is True and source.get('retrieval_kind') == 'page_fetch' else 'Resultado de busca; página não aberta' if source.get('retrieval_kind') == 'search_result' else 'Link citado; abertura não comprovada'
        source_rows.append('<li><strong>' + _inline(source.get('title') or 'Fonte sem título') + '</strong><span>' + escape(label) + '</span><code>' + escape(str(source['url'])) + '</code>' + ('<small>Registro: ' + escape(str(source['accessed_at'])) + '</small>' if source.get('accessed_at') else '') + '</li>')
    diagram = '<svg class="flow" viewBox="0 0 720 126" role="img" aria-label="Ilustração: fontes registradas, síntese, conferência"><g fill="#262131" stroke="#705366"><rect x="8" y="14" width="202" height="74" rx="13"/><rect x="259" y="14" width="202" height="74" rx="13"/><rect x="510" y="14" width="202" height="74" rx="13"/></g><g fill="#eee4ef" font-family="system-ui,sans-serif" font-size="19" text-anchor="middle"><text x="109" y="57">Fontes registradas</text><text x="360" y="57">Síntese</text><text x="611" y="57">Conferência</text></g><g stroke="#ee9bc7" stroke-width="3" fill="none"><path d="M220 51h27m-7-7 7 7-7 7M470 51h28m-7-7 7 7-7 7"/></g><text x="10" y="116" fill="#b8a8bd" font-family="system-ui,sans-serif" font-size="13">Ilustração do processo; não comprova conclusão das etapas.</text></svg>'
    css = 'html{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#17141d;color:#eee6f2;font:16px/1.6 system-ui,sans-serif}.page{max-width:940px;margin:auto;padding:30px 24px 50px}h1{font-size:clamp(25px,5vw,38px);line-height:1.15;letter-spacing:-1px;margin:12px 0 17px}h2{font-size:20px;line-height:1.3;margin:0}p{margin:12px 0}.eyebrow,small{color:#b8a8bd;font-size:12px}.intro{color:#cec0d3}.flow{width:100%;height:auto;margin:12px 0}.facts{display:flex;flex-wrap:wrap;gap:10px}.facts>span{border:1px solid #534057;background:#251e2c;border-radius:10px;padding:9px 13px;font-size:13px}.facts b{font-size:22px;color:#f3a3ce;margin-right:6px}article{border:1px solid #ffffff14;background:#201b27;border-radius:15px;padding:21px;margin:17px 0}article header{display:flex;align-items:center;gap:10px}.mark{width:30px;min-width:30px;height:30px;fill:#372137;stroke:#ef9ac8;stroke-width:1.6}.lead{color:#dbcede}details{border-top:1px solid #ffffff14;margin-top:15px;padding-top:12px}summary{cursor:pointer;color:#eaaaD0;font-size:14px;min-height:30px}summary:focus-visible{outline:2px solid #ee9bc7;outline-offset:5px}details p,details li{font-size:14px;color:#c5b8ce}li+li{margin-top:8px}code{font:13px/1.6 ui-monospace,Consolas,monospace;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#16121c;border-radius:9px;padding:13px}.sources{margin-top:30px}.sources ol{padding-left:22px}.sources li{margin:17px 0}.sources li>*{display:block}.sources code{color:#b7c8f0;user-select:text}.sources span{font-size:12px;color:#c4adc9}.notice{padding:13px 15px;background:#2d2130;border-left:3px solid #e99bc3;border-radius:8px;font-size:14px;color:#decae1}@media(max-width:500px){.page{padding:23px 17px}article{padding:17px}.facts{gap:7px}.facts>span{font-size:12px;padding:8px 10px}.flow{min-height:90px}h2{font-size:18px}}'
    return '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + escape(str(job.get('title', 'Pesquisa MegaBrain'))) + '</title><style>' + css + '</style></head><body><main class="page"><span class="eyebrow">MEGABRAIN · PESQUISA · ' + escape(str(created_at)) + '</span><h1>' + escape(str(job.get('title', 'Pesquisa'))) + '</h1><p class="intro">Síntese da execução. O estado de revisão e os testes continuam registrados no pedido.</p><div class="facts"><span><b>' + str(opened) + '</b>páginas abertas</span><span><b>' + str(searched) + '</b>resultados de busca</span></div>' + diagram + ''.join(cards) + '<section class="sources"><h2>Fontes e procedência</h2><p class="notice">Abra os links em <strong>Fontes da pesquisa</strong> no pedido. Esta prévia mostra os endereços em texto para consulta e cópia.</p><ol>' + ''.join(source_rows) + '</ol></section></main></body></html>'
