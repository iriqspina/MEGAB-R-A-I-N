"""Project report rendering inside an opaque child, never in the API's origin.

Source files are read only. Messages are proposals/data, never commands. The
host must validate the wrapper window and ticket and ask the human to save any
feedback. A report hash binds drafts and feedback to the version displayed.
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
import mimetypes
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import url2pathname

MAX_REPORT = 64_000_000
MAX_RESOURCE = 8_000_000
MAX_BUNDLE = 40_000_000
MEDIA = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.ico', '.mp3', '.wav', '.ogg', '.mp4', '.webm', '.woff', '.woff2', '.ttf'}
PRIVATE = {'.env', 'private', 'privado', 'privados', 'privadas', 'secrets', 'credentials', 'credenciais', '__pycache__', 'node_modules', '.git', '.venv', 'runtime-packages'}

view_headers = {
    'Content-Security-Policy': "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; frame-src 'self'; connect-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'",
    'X-Frame-Options': 'SAMEORIGIN', 'Referrer-Policy': 'no-referrer', 'Cache-Control': 'no-store',
}
render_headers = {
    'Content-Security-Policy': "sandbox allow-scripts allow-forms; default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; media-src data:; font-src data:; connect-src 'none'; frame-src 'none'; child-src 'none'; object-src 'none'; worker-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'",
    'X-Frame-Options': 'SAMEORIGIN', 'Referrer-Policy': 'no-referrer', 'Cache-Control': 'no-store',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=(), usb=()',
}
VIEW_HEADERS = view_headers
RENDER_HEADERS = render_headers


def _identity(fid, token):
    if not re.fullmatch(r'[a-f0-9]{20}', str(fid)) or not re.fullmatch(r'[A-Za-z0-9_-]{16,160}', str(token)):
        raise ValueError('Identificador ou ticket de relatório inválido.')


def _json(value):
    return json.dumps(value, ensure_ascii=False).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


def confined_file(path, root, *, suffixes=None, limit=MAX_RESOURCE):
    """Permit relative parent steps inside root, but reject hidden/private paths.

Both lexical and resolved paths are checked so a private symlink alias cannot
expose private content. Hardlinks are refused too: their origin is ambiguous.
"""
    root = Path(root).resolve(strict=True)
    raw = Path(path)
    raw = raw if raw.is_absolute() else root / raw
    lexical = Path(__import__('os').path.abspath(raw))
    resolved = raw.resolve(strict=True)
    for candidate in (lexical, resolved):
        if not candidate.is_relative_to(root):
            raise ValueError('Arquivo fora do projeto.')
        if any(part.startswith('.') or part.casefold() in PRIVATE for part in candidate.relative_to(root).parts):
            raise ValueError('Arquivo privado não pode aparecer no relatório.')
    if not resolved.is_file() or resolved.stat().st_nlink > 1 or resolved.stat().st_size > limit:
        raise ValueError('Arquivo indisponível ou acima do limite.')
    if suffixes is not None and resolved.suffix.lower() not in suffixes:
        raise ValueError('Tipo de recurso não permitido.')
    return resolved


BOOTSTRAP = r"""
(()=>{'use strict';const META=__META__,memory=Object.create(null);let started=false;
const send=(kind,payload)=>parent.postMessage({...META,channel:'megabrain-report',kind,payload},'*');
const trim=(v,n=6000)=>typeof v==='string'?v.slice(0,n):'';
function notes(values){return Array.isArray(values)?values.slice(0,150).filter(v=>v&&typeof v.texto==='string').map(v=>({texto:trim(v.texto),id:trim(v.id,180),n:Number(v.n)||0,onde:trim(v.onde,500),criado_em:trim(v.criado_em,80),x:Number(v.x)||0,y:Number(v.y)||0,ancora:trim(v.ancora||v.alvo,300)})):[];}
function state(){const out={};for(const key of Object.keys(memory).slice(0,100)){if(memory[key].length<=50000)out[key]=memory[key];}return out;}
const storage={getItem:k=>Object.hasOwn(memory,String(k))?memory[String(k)]:null,setItem(k,v){k=String(k);v=String(v);if(k.length>250||v.length>50000)return;memory[k]=v;send('draft',{storage:state()});},removeItem(k){delete memory[String(k)];send('draft',{storage:state()});},clear(){for(const k of Object.keys(memory))delete memory[k];send('draft',{storage:{}});},key:i=>Object.keys(memory)[i]||null,get length(){return Object.keys(memory).length;}};
try{Object.defineProperty(window,'localStorage',{value:storage,configurable:false});Object.defineProperty(window,'sessionStorage',{value:storage,configurable:false});}catch{}
let cursor=null,decisions=null;
function hook(name,wrap){let value;Object.defineProperty(window,name,{configurable:true,get:()=>value,set(v){value=v;if(v&&typeof v.iniciar==='function'){const original=v.iniciar;v.iniciar=function(o={}){return wrap(original,o,this);};}}});}
hook('CursorFerramentas',(fn,o,ctx)=>{const own=o.aoSalvarNota;cursor=fn.call(ctx,{...o,segurarMs:400,cancelarAoMover:true,tolerancia:0,atrasoVisualMs:80,aoSalvarNota(n){send('feedback',{kind:'notes',notas:notes([n])});if(typeof own==='function')own(n);}});return cursor;});
hook('DecisoesRespondiveis',(fn,o,ctx)=>{decisions=fn.call(ctx,o);return decisions;});
document.addEventListener('click',event=>{
 const element=event.target instanceof Element?event.target:null;if(!element)return;
 const link=element.closest('a');if(link){const local=link.getAttribute('data-mb-local'),external=link.getAttribute('data-mb-external');if(local||external){event.preventDefault();event.stopImmediatePropagation();if(event.isTrusted)send(local?'open-local':'open-external',local?{path:local}:{url:external});return;}}
 const button=element.closest('button');if(button&&button.id==='dr-enviar'){setTimeout(()=>{if(decisions){send('feedback',{kind:'decisions',finalizado:true,respostas:decisions.respostas(),notas:cursor&&typeof cursor.notas==='function'?notes(cursor.notas()):[],resumo_texto:trim(decisions.resumoTexto?.(),30000)});}},0);}
},true);
document.addEventListener('submit',e=>{e.preventDefault();},true);
window.MegaBrainReport=Object.freeze({saveFeedback(value){if(value&&typeof value==='object')send('feedback',value);}});
async function start(){if(started)return;started=true;const scripts=[...document.querySelectorAll('script[type="application/x-megabrain-script"]')];for(const original of scripts){const s=document.createElement('script');if(original.dataset.mbType==='module')s.type='module';s.textContent=original.textContent;if(s.type==='module'){await new Promise(resolve=>{s.onload=resolve;s.onerror=resolve;original.replaceWith(s);});}else original.replaceWith(s);}document.dispatchEvent(new Event('DOMContentLoaded',{bubbles:true}));if(document.readyState==='complete')window.dispatchEvent(new Event('load'));send('loaded',{});}
window.addEventListener('message',event=>{const m=event.data;if(event.source!==parent||!m||m.channel!=='megabrain-report-restore'||m.token!==META.token||m.fid!==META.fid||m.hash!==META.hash)return;const saved=m.storage;if(saved&&typeof saved==='object'&&!Array.isArray(saved)){for(const [k,v] of Object.entries(saved).slice(0,100))if(k.length<=250&&typeof v==='string'&&v.length<=50000)memory[k]=v;}start();});
document.addEventListener('DOMContentLoaded',()=>send('ready',{}),{once:true});
})();
"""


def wrapper_report(fid, token, storage=None, expected_hash=None):
    """Authenticated envelope. Child is opaque and has no API/network access."""
    _identity(fid, token)
    if expected_hash is not None and not re.fullmatch(r'[a-f0-9]{64}', str(expected_hash)):
        raise ValueError('Versão de relatório inválida.')
    meta = _json({'fid': fid, 'token': token})
    if storage is not None:
        if not isinstance(storage, dict): raise ValueError('Rascunho de relatório inválido.')
        storage = {str(k): v for k, v in list(storage.items())[:100] if len(str(k)) <= 250 and isinstance(v, str) and len(v) <= 50000}
        if len(_json(storage)) > 128000: raise ValueError('Rascunho de relatório acima do limite.')
    initial = _json(storage)
    version = '&amp;version=' + expected_hash if expected_hash else ''
    expected = _json(expected_hash)
    return '''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Relatório no MegaBrain</title><style>html,body,iframe{margin:0;width:100%;height:100%;border:0}body{overflow:hidden}#report-error{position:absolute;inset:0;padding:30px;background:#17131e;color:#f2e5ee;font:16px/1.6 system-ui}#report-error[hidden]{display:none}</style><iframe id="report" title="Relatório interativo isolado" sandbox="allow-scripts allow-forms" referrerpolicy="no-referrer" src="/api/reports/'''+fid+'/render?ticket='+token+version+'''"></iframe><p id="report-error" role="status" hidden></p><script>
(()=>{'use strict';const META='''+meta+''',initialStorage='''+initial+''',inner=document.getElementById('report');let hash='''+expected+''';
const size=value=>{try{return JSON.stringify(value).length;}catch{return Infinity;}};
window.addEventListener('message',event=>{const m=event.data;
 if(event.source!==inner.contentWindow||event.origin!=='null'||!m||m.channel!=='megabrain-report'||m.token!==META.token||m.fid!==META.fid||!/^([a-f0-9]{64})$/.test(m.hash)||size(m)>160000)return;
 if(hash&&hash!==m.hash){inner.hidden=true;const error=document.getElementById('report-error');error.hidden=false;error.textContent='O relatório mudou durante a abertura. Reabra o resultado para carregar a versão atual; suas respostas anteriores continuam preservadas.';parent.postMessage({...META,channel:'megabrain-report',kind:'stale',hash,payload:{message:error.textContent}},location.origin);return;}hash=m.hash;const key='megabrain-report:'+META.fid+':'+hash;
 if(m.kind==='ready'){let storage=initialStorage;if(storage===null){storage={};try{storage=JSON.parse(sessionStorage.getItem(key)||'{}');}catch{}}inner.contentWindow.postMessage({channel:'megabrain-report-restore',...META,hash,storage},'*');}
 else if(m.kind==='draft'){const s=m.payload?.storage;if(!s||typeof s!=='object'||Array.isArray(s)||size(s)>128000)return;try{sessionStorage.setItem(key,JSON.stringify(s));}catch{}}
 else if(!['feedback','loaded','open-local','open-external'].includes(m.kind))return;
 parent.postMessage({...m,...META,hash},location.origin);
});
})();</script></html>'''


def render_report(path, root, fid, token):
    """Read a report and inline permitted project-local resources, preserving source."""
    _identity(fid, token)
    root = Path(root).resolve(strict=True)
    path = confined_file(path, root, suffixes={'.html', '.htm'}, limit=MAX_REPORT)
    source = path.read_bytes()
    meta = {'fid': fid, 'token': token, 'hash': hashlib.sha256(source).hexdigest()}
    # Inline source data is covered by MAX_REPORT. Keep the independent budget
    # for additional local resources; large self-contained HTML must not spend it.
    budget = [0]

    def resource(value, suffixes, base=path.parent):
        parsed = urlsplit(value or '')
        if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith(('/', '\\')):
            return None
        try:
            candidate = confined_file(base / unquote(parsed.path), root, suffixes=suffixes)
            budget[0] += candidate.stat().st_size
            if budget[0] > MAX_BUNDLE:
                return None
            return candidate
        except (ValueError, OSError):
            return None

    def data_url(p):
        mime = mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
        return 'data:' + mime + ';base64,' + base64.b64encode(p.read_bytes()).decode('ascii')

    def local_link(value):
        """Catalogue legacy file: URIs and absolute project links remain usable."""
        value = value or ''
        parsed = urlsplit(value)
        try:
            if parsed.scheme == 'file' and parsed.netloc in {'', 'localhost'}:
                candidate = Path(url2pathname(unquote(parsed.path)))
            elif Path(value).is_absolute():
                candidate = Path(value)
            elif not parsed.scheme and not parsed.netloc and parsed.path and not parsed.path.startswith(('/', '\\')):
                candidate = path.parent / unquote(parsed.path)
            else:
                return None
            # Links identify another document; they never inline or spend the
            # additional resource budget. HTML gets the report limit here too.
            limit = MAX_REPORT if candidate.suffix.lower() in {'.html', '.htm'} else MAX_RESOURCE
            return confined_file(candidate, root, limit=limit)
        except (ValueError, OSError):
            return None

    def css(content, base):
        # CSS cannot import other code; local font/image URLs may be embedded.
        content = re.sub(r'@import\s+(?:url\([^)]*\)|[\"\'][^\"\']*[\"\'])[^;]*;', '', content, flags=re.I)
        def replace(match):
            value = next(group for group in match.groups() if group is not None).strip()
            # Embedded visual resources and SVG paint references belong to the
            # document itself; preserve their spelling, including quoted ')'.
            if value.startswith('#') or re.match(r'^data:(?:image/|font/)', value, re.I):
                return match.group(0)
            p = resource(value, MEDIA, base)
            return 'url("' + (data_url(p) if p else 'about:blank') + '")'
        return re.sub(r'''url\(\s*(?:"([^"\\]*(?:\\.[^"\\]*)*)"|'([^'\\]*(?:\\.[^'\\]*)*)'|([^)]*?))\s*\)''', replace, content, flags=re.I)

    class Report(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.out = []; self.external_script = False; self.style = False

        def handle_starttag(self, tag, attrs):
            values = dict(attrs)
            if tag in {'base', 'iframe', 'frame', 'frameset', 'object', 'embed'} or tag == 'meta' and values.get('http-equiv'):
                return
            if tag == 'script':
                script_type = str(values.get('type') or '').casefold()
                if values.get('src') is not None:
                    p = resource(values['src'], {'.js', '.mjs'})
                    if p:
                        code = re.sub(r'</script', r'<\\/script', p.read_text(encoding='utf-8-sig'), flags=re.I)
                        self.out.append('<script type="application/x-megabrain-script" data-mb-type="'+('module' if script_type == 'module' else '')+'">'+code+'</script>')
                    self.external_script = True
                    return
                if script_type not in {'', 'module', 'text/javascript', 'application/javascript', 'text/ecmascript', 'application/ecmascript'}:
                    self.out.append('<script type="'+html.escape(script_type, quote=True)+'">')
                else:
                    self.out.append('<script type="application/x-megabrain-script" data-mb-type="'+('module' if script_type == 'module' else '')+'">')
                return
            if tag == 'link':
                p = resource(values.get('href'), {'.css'}) if str(values.get('rel', '')).casefold() == 'stylesheet' else None
                if p:
                    style = css(p.read_text(encoding='utf-8-sig'), p.parent)
                    self.out.append('<style>'+re.sub(r'</style', r'<\\/style', style, flags=re.I)+'</style>')
                return
            rendered = []
            for name, value in attrs:
                if name in {'srcdoc', 'srcset', 'ping', 'integrity', 'crossorigin', 'target', 'download'} or name.startswith('data-mb-'):
                    continue
                if name == 'style' and value:
                    value = css(value, path.parent)
                if name in {'src', 'href', 'xlink:href', 'action', 'formaction', 'poster', 'data'}:
                    if value and value.startswith('#'):
                        pass
                    elif tag == 'a' and name == 'href':
                        parsed = urlsplit(value or '')
                        local = local_link(value)
                        if local:
                            rendered.append('data-mb-local="'+html.escape(local.relative_to(root).as_posix(), quote=True)+'"')
                        elif parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password:
                            rendered.append('data-mb-external="'+html.escape(value, quote=True)+'"')
                        value = '#'
                    elif name in {'src', 'poster', 'href', 'xlink:href'} and (p := resource(value, MEDIA)):
                        value = data_url(p)
                    elif value and re.match(r'^data:(?:image/|audio/|video/|font/)', value, re.I) and name in {'src', 'poster'}:
                        pass
                    else:
                        value = 'about:blank'
                rendered.append(name if value is None else name+'="'+html.escape(value, quote=True)+'"')
            self.out.append('<'+tag+(' '+' '.join(rendered) if rendered else '')+'>')
            if tag == 'style': self.style = True

        def handle_startendtag(self, tag, attrs):
            self.handle_starttag(tag, attrs)
            # SVG shapes are not HTML void elements. Expanding <rect/> to an
            # open <rect> makes following text its child and loses its render.
            if tag not in {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}:
                self.handle_endtag(tag)

        def handle_endtag(self, tag):
            if tag == 'script' and self.external_script:
                self.external_script = False; return
            if tag == 'style': self.style = False
            if tag not in {'base', 'iframe', 'frame', 'frameset', 'object', 'embed'}:
                self.out.append('</'+tag+'>')

        def handle_data(self, data):
            if not self.external_script:
                self.out.append(css(data, path.parent) if self.style else data)
        def handle_entityref(self, name): self.out.append('&'+name+';')
        def handle_charref(self, name): self.out.append('&#'+name+';')
        def handle_comment(self, data): self.out.append('<!--'+data+'-->')
        def handle_decl(self, decl): self.out.append('<!'+decl+'>')

    parser = Report(); parser.feed(source.decode('utf-8-sig', errors='replace')); parser.close()
    result = ''.join(parser.out)
    bootstrap = '<script>'+BOOTSTRAP.replace('__META__', _json(meta))+'</script>'
    # Keep legacy report sources intact; their initializer uses the current shared gesture.
    if 'CursorFerramentas' in result:
        cursor_source = Path(__file__).resolve().parents[2] / 'motor/modelos/interacoes/261010_cursor-ferramentas/cursor-ferramentas.js'
        cursor_code = re.sub(r'</script', r'<\\/script', cursor_source.read_text(encoding='utf-8-sig'), flags=re.I)
        bootstrap += '<script>' + cursor_code + '</script>'
    # Shim comes before every original script; original scripts run after restore.
    head = re.search(r'<head(?:\s[^>]*)?>', result, flags=re.I)
    if head:
        result = result[:head.end()] + bootstrap + result[head.end():]
    else:
        result = '<!doctype html><meta charset="utf-8">' + bootstrap + result
    return result
