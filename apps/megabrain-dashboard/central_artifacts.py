"""Authenticated references for immutable job artifacts, separate from source files."""
import base64,hashlib,html,json,re
from html.parser import HTMLParser
from pathlib import Path
from central_store import APP,now
from central_execution import TEXT_EXTENSIONS, _relative, _no_links, _text_file, _public_url

TEXT_TYPES={extension:'text/plain' for extension in TEXT_EXTENSIONS}
TEXT_TYPES.update({'.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json','.html':'text/html','.htm':'text/html','.svg':'image/svg+xml'})
PREVIEW_WRAPPER_HEADERS={
    'Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; frame-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'",
    'X-Frame-Options':'SAMEORIGIN','Cache-Control':'no-store','Referrer-Policy':'no-referrer',
    'X-Content-Type-Options':'nosniff'}
RENDER_HEADERS={
    # allow-forms enables validation/submit events for client-side UI. Network
    # submissions remain forbidden by form-action, including the same origin.
    'Content-Security-Policy':"sandbox allow-scripts allow-forms; default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; media-src data: blob:; connect-src 'none'; frame-src 'none'; worker-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'",
    'X-Frame-Options':'SAMEORIGIN','Cache-Control':'no-store','Referrer-Policy':'no-referrer',
    'X-Content-Type-Options':'nosniff'}

def job_directory(job_id):
    if not re.fullmatch(r'[a-f0-9]{32}',job_id):raise ValueError('Identificador de pedido inválido.')
    return APP/'data/jobs'/job_id

def checked_path(directory,relative):
    base=Path(directory).absolute();_no_links(base,base)
    rel=_relative(str(relative).replace('\\','/'))
    if rel.parts[0] not in {'workspace','artifacts'}:raise ValueError('Logs e controles não são artefatos publicados.')
    candidate=base.joinpath(*rel.parts);_no_links(candidate,base);resolved=candidate.resolve(strict=True)
    if not resolved.is_relative_to(base) or not resolved.is_file():raise ValueError('Resultado fora da área do pedido.')
    if resolved.suffix.lower() not in TEXT_TYPES:raise ValueError('Tipo de artefato não permitido.')
    _text_file(resolved)
    return resolved

def register_artifact(job_id,relative,title=None,origin='execution'):
    directory=job_directory(job_id);path=checked_path(directory,relative)
    digest=hashlib.sha256(path.read_bytes()).hexdigest();aid=hashlib.sha256(str(relative).encode()).hexdigest()[:24]
    out=dict(id=aid,title=title or path.name,path=str(relative).replace('\\','/'),type='html' if path.suffix.lower() in {'.html','.htm'} else 'text',sha256=digest,size=path.stat().st_size,origin=origin,url=f'/api/jobs/{job_id}/artifacts/{aid}',at=now())
    if out['type']=='html':out.update(preview_url=f'/api/jobs/{job_id}/preview/{aid}',interactive=True)
    else:out.update(preview_url=f'/api/jobs/{job_id}/view/{aid}',interactive=False)
    return out

def resolve_artifact(job,artifact_id):
    artifact=next((a for a in job.get('artifacts',[]) if a.get('id')==artifact_id),None)
    if not artifact:raise KeyError('Artefato não encontrado.')
    path=checked_path(job_directory(job['id']),artifact['path'])
    if hashlib.sha256(path.read_bytes()).hexdigest()!=artifact['sha256']:raise ValueError('O artefato mudou desde a verificação; execute uma nova conferência.')
    return path,artifact

def research_report(job,text,sources):
    folder=job_directory(job['id'])/'artifacts';folder.mkdir(exist_ok=True)
    sources=[s for s in sources if _public_url(s.get('url'))]
    from central_research_view import render_research_report
    content=render_research_report(job,text,sources,now())
    (folder/'pesquisa.html').write_text(content,encoding='utf-8')
    (folder/'fontes.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding='utf-8')
    return [register_artifact(job['id'],'artifacts/pesquisa.html','Pesquisa e conclusões','research'),register_artifact(job['id'],'artifacts/fontes.json','Fontes da pesquisa','research')]

def preview_wrapper(job_id,artifact_id):
    """Parent frame CSP prevents a generated script navigating itself externally."""
    if not re.fullmatch(r'[a-f0-9]{32}',job_id) or not re.fullmatch(r'[a-f0-9]{24}',artifact_id):
        raise ValueError('Identificador de prévia inválido.')
    url=f'/api/jobs/{job_id}/render/{artifact_id}'
    return '<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Prévia isolada</title><style>html,body,iframe{margin:0;width:100%;height:100%;border:0}body{overflow:hidden}</style><iframe title="Resultado interativo isolado" sandbox="allow-scripts allow-forms" referrerpolicy="no-referrer" src="'+url+'"></iframe></html>'


def isolated_preview(content,job,artifact=None):
    """Make registered local JS/CSS/SVG self-contained; block other URL attributes.

Scripts remain untrusted and execute only under RENDER_HEADERS inside the
PREVIEW_WRAPPER_HEADERS parent. This transformation is not an HTML sanitizer
for an unsandboxed document. Dynamically requested resources stay CSP-blocked.
"""
    from urllib.parse import unquote,urlsplit
    parent=Path((artifact or {}).get('path','workspace/index.html')).parent
    def resource(value,suffixes):
        if not value:return None
        parsed=urlsplit(value)
        if parsed.scheme or parsed.netloc or value.startswith(('/', '\\')):return None
        candidate=(parent/unquote(parsed.path)).as_posix()
        # Normalize harmless ./ while still refusing parent traversal.
        if '..' in Path(candidate).parts:return None
        found=next((a for a in job.get('artifacts',[]) if a.get('path')==candidate),None)
        if not found:return None
        try:path,_=resolve_artifact(job,found['id'])
        except (ValueError,KeyError,OSError):return None
        return path if path.suffix.lower() in suffixes else None
    class Preview(HTMLParser):
        def __init__(self):super().__init__(convert_charrefs=False);self.out=[];self.skip_script=False
        def handle_starttag(self,tag,attrs):
            values=dict(attrs)
            if tag=='base' or tag=='meta' and str(values.get('http-equiv','')).casefold()=='refresh':return
            if tag in {'iframe','object','embed','frame','frameset'}:return
            if tag=='script' and values.get('src') is not None:
                p=resource(values['src'],{'.js','.mjs'})
                if p:
                    code=p.read_text(encoding='utf-8-sig').replace('</script','<\\/script').replace('</SCRIPT','<\\/SCRIPT')
                    module=' type="module"' if values.get('type')=='module' else ''
                    self.out.append('<script'+module+'>'+code+'</script>')
                self.skip_script=True;return
            if tag=='link':
                p=resource(values.get('href'),{'.css'}) if str(values.get('rel','')).casefold()=='stylesheet' else None
                if p:self.out.append('<style>'+p.read_text(encoding='utf-8-sig').replace('</style','<\\/style')+'</style>')
                return
            rendered=[]
            for name,value in attrs:
                if name in {'srcdoc','srcset','ping','integrity','crossorigin'}:continue
                if name in {'src','href','xlink:href','action','formaction','poster','data'}:
                    if value and value.startswith('#'):pass
                    elif value and value.startswith('data:') and name in {'src','poster'}:pass
                    elif tag=='img' and name=='src' and (p:=resource(value,{'.svg'})):
                        value='data:image/svg+xml;base64,'+base64.b64encode(p.read_bytes()).decode()
                    else:value='about:blank'
                rendered.append(name if value is None else name+'="'+html.escape(value,quote=True)+'"')
            self.out.append('<'+tag+(' '+' '.join(rendered) if rendered else '')+'>')
        def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs)
        def handle_endtag(self,tag):
            if tag=='script' and self.skip_script:self.skip_script=False;return
            if tag not in {'iframe','object','embed','frame','frameset'}:self.out.append('</'+tag+'>')
        def handle_data(self,data):
            if not self.skip_script:self.out.append(data)
        def handle_entityref(self,name):self.out.append('&'+name+';')
        def handle_charref(self,name):self.out.append('&#'+name+';')
        def handle_decl(self,decl):self.out.append('<!'+decl+'>')
        def handle_comment(self,data):self.out.append('<!--'+data+'-->')
    parser=Preview();parser.feed(content);parser.close();return ''.join(parser.out)
