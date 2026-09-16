"""Entrada estável para entregas. Registro explícito + legado sem presumir aprovação."""
from __future__ import annotations
import datetime as dt
import html
import hashlib
import json
from pathlib import Path
import mb_trava as trava
import mb_utils as u

MARCADOR='<!-- MEGABRAIN:CATALOGO:1 -->'
ESTADOS=('rascunho','em_revisao','pronto','arquivado','nao_verificado')
LEITURA={'.html','.htm','.md','.txt','.pdf','.png','.jpg','.jpeg','.gif','.svg','.docx','.xlsx','.pptx','.mp4','.wav','.mp3','.json'}
def e(value): return html.escape(str(value),quote=True)
def caminho(root,value):
    p=Path(value); p=(root/p).resolve() if not p.is_absolute() else p.resolve()
    if not p.is_relative_to(root): raise ValueError('Destino fora do projeto: '+str(p))
    return p
def linha(root,ident,titulo,pasta,arquivo=None,**kw):
    return dict(id=ident,titulo=titulo,pasta=str(pasta),pasta_url=pasta.as_uri(),arquivo=str(arquivo) if arquivo else None,arquivo_url=arquivo.as_uri() if arquivo else None,projeto=root.name,tarefa=titulo,sessao='não informada',estado='nao_verificado',origem='legado',proxima_acao='Consultar a pasta; estado ainda não classificado.',**kw)
def coletar(projeto):
    root=Path(projeto).resolve(strict=True); inbox=caminho(root,'00_PARA-VOCE')
    registro=caminho(root,'dados/entregas.json'); rows=[]; usados=set(); ids=set()
    if registro.exists():
        doc=json.loads(registro.read_text(encoding='utf-8-sig'))
        if not isinstance(doc,dict) or doc.get('schema_version')!=1 or not isinstance(doc.get('entregas'),list): raise ValueError('Registro de entregas inválido')
        for item in doc['entregas']:
            if not isinstance(item,dict): raise ValueError('Entrega precisa ser objeto')
            for field in ('id','titulo','pasta','estado','proxima_acao'):
                if not isinstance(item.get(field),str) or not item[field].strip(): raise ValueError('Campo ausente: '+field)
            if item['id'] in ids: raise ValueError('ID de entrega duplicado: '+item['id'])
            ids.add(item['id'])
            if item['estado'] not in ESTADOS: raise ValueError('Estado de entrega inválido')
            folder=caminho(root,item['pasta']); file=caminho(root,item['arquivo']) if item.get('arquivo') else None
            if not folder.is_dir() or (file and not file.is_file()): raise ValueError('Destino registrado ausente: '+str(file or folder))
            if file and not file.is_relative_to(folder): raise ValueError('Arquivo fora da pasta declarada')
            if file and file.suffix.lower() not in LEITURA: raise ValueError('Entrada principal precisa ser documento, não executável')
            r=linha(root,item['id'],item['titulo'],folder,file)
            for field in ('projeto','tarefa','sessao','estado','proxima_acao','atualizado_em','pedido_inicial','pedido_atual','etapa'):
                if field in item: r[field]=str(item[field])
            r['origem']='registro'; r['fonte']=str(registro); rows.append(r); usados.add(folder)
            if r['estado']=='pronto':
                if not file or not item.get('verificado_sha256') or not item.get('verificacao'):
                    r.update(estado='em_revisao',proxima_acao='Estado pronto sem prova associada: conferir o artefato.')
                elif hashlib.sha256(file.read_bytes()).hexdigest()!=item['verificado_sha256']:
                    r.update(estado='em_revisao',proxima_acao='O arquivo mudou desde a verificação. Revisar a versão atual.')
    if inbox.is_dir():
        for p in sorted(inbox.iterdir(),key=lambda p:p.name.casefold()):
            if p.name in ('INICIO.html','_arquivo') or p.resolve() in usados: continue
            # Do not follow links to another project or recurse into runtime trees.
            try: p=caminho(root,p)
            except ValueError: continue
            if p.is_dir():
                candidates=[p/n for n in ('INICIO.html','index.html','RELATORIO.html','LEIAME.md','RESULTADO.md')]
                file=next((x for x in candidates if x.is_file() and x.resolve().is_relative_to(root)),None)
                if file is None:
                    file=next((x for x in sorted(p.iterdir()) if x.is_file() and x.suffix.lower() in ('.html','.md','.pdf') and x.resolve().is_relative_to(root)),None)
                folder=p
            elif p.is_file():
                folder=p.parent; file=p if p.suffix.lower() in LEITURA else None
            else: continue
            r=linha(root,'legado:'+p.name,p.name.replace('_',' '),folder,file)
            r.update(origem='registro técnico' if p.name.startswith('orquestracao') else 'legado',fonte=str(p),atualizado_em=dt.datetime.fromtimestamp(p.stat().st_mtime).astimezone().isoformat())
            rows.append(r)
    return {'schema_version':1,'gerado_em':dt.datetime.now().astimezone().isoformat(timespec='seconds'),'projeto':str(root),'pasta':str(inbox),'entregas':rows,'relatorio':str(root/'00_painel'/'RELATORIO.html') if (root/'00_painel'/'RELATORIO.html').is_file() else None}

CSS='''
:root{color-scheme:dark;--fundo:#101018;--card:#1C1C29;--card2:#252535;--tinta:#F7F6FC;--corpo:#D2CFDF;--fraco:#B7B2C8;--linha:#515064;--roxo:#CE82FF;--azul:#1CB0F6;--verde:#58CC02;--coral:#FF4B4B;--amarelo:#FFC800;--mono:Consolas,monospace}
html[data-tema=claro]{color-scheme:light;--fundo:#F5F3EE;--card:#FFF;--card2:#ECE8F3;--tinta:#191923;--corpo:#454552;--fraco:#5E5E6E;--linha:#B5ACBF}
*{box-sizing:border-box}body{margin:0;background:var(--fundo);color:var(--tinta);font:16px/1.55 'Segoe UI',sans-serif}body:before{content:'';position:fixed;inset:0 0 auto;height:6px;background:linear-gradient(90deg,var(--roxo),var(--azul),var(--verde));z-index:2}main{max-width:1180px;margin:auto;padding:28px 30px 60px}header{display:flex;align-items:center;justify-content:space-between;gap:20px}h1{font-size:36px;line-height:1.15;margin:10px 0 14px;letter-spacing:-.03em}h2{font-size:23px;margin:0 0 8px}h3{font-size:19px;margin:5px 0}p{margin:8px 0 14px;max-width:75ch}.eyebrow{font:700 12px var(--mono);letter-spacing:.08em;color:var(--fraco)}.muted,small{color:var(--fraco)}.actions{display:flex;flex-wrap:wrap;gap:10px;align-items:center}button,.button{font:600 14px 'Segoe UI',sans-serif;color:var(--tinta);background:var(--card2);border:1px solid var(--linha);padding:9px 13px;border-radius:8px;cursor:pointer;text-decoration:none;display:inline-block;min-height:42px}button:hover,.button:hover{border-color:var(--roxo)}.primary{background:var(--roxo);color:#23132C;border-color:transparent;font-weight:800}a{color:inherit;text-underline-offset:3px}:focus-visible{outline:3px solid var(--azul);outline-offset:3px}.focus{background:var(--card);border:1px solid var(--linha);border-left:5px solid var(--roxo);padding:24px;margin:26px 0}.path{display:block;white-space:pre-wrap;overflow-wrap:anywhere;user-select:all;font:13px/1.55 var(--mono);color:var(--corpo);margin:12px 0}.toolbar{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0 12px}.toolbar label{flex:1;min-width:180px;font-size:13px;color:var(--corpo)}input,select,textarea{display:block;width:100%;color:var(--tinta);background:var(--card);border:1px solid var(--linha);padding:12px;font:inherit;border-radius:6px;margin-top:5px}article{padding:22px 0;border-top:1px solid var(--linha)}.meta{font:12px/1.6 var(--mono);color:var(--fraco);overflow-wrap:anywhere}.tag{display:inline-block;border:1px solid var(--linha);border-radius:5px;padding:2px 8px;font-size:12px;margin-right:6px}.row-head{display:flex;align-items:baseline;justify-content:space-between;gap:16px}.empty{border:1px dashed var(--linha);padding:24px}details{border-top:1px solid var(--linha);margin-top:24px;padding-top:18px}summary{cursor:pointer;font-weight:700;min-height:44px}.guide{background:var(--card);padding:22px;margin-top:25px;border-radius:8px}.guide ol{padding-left:22px}#toast{position:fixed;bottom:20px;left:20px;right:20px;max-width:660px;margin:auto;background:var(--tinta);color:var(--fundo);padding:13px 20px;border-radius:6px;box-shadow:0 3px 15px #0005}#toast:empty{display:none}[hidden]{display:none!important}footer{margin-top:30px;color:var(--fraco);font-size:13px}noscript{display:block;padding:15px;border:1px solid var(--coral)}@media(max-width:600px){main{padding:22px 16px 40px}header{align-items:flex-start}h1{font-size:29px}.focus{padding:18px}.row-head{display:block}.toolbar{display:block}.toolbar label{display:block;margin-bottom:12px}.actions button,.actions .button{flex-grow:1;text-align:center}.path{font-size:12px}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
'''
CSS+='\n.compass{margin:14px 0;padding:12px 15px;border-left:3px solid var(--azul);background:var(--card2);font-size:14px;overflow-wrap:anywhere}.compass b{display:block;margin-bottom:5px}\n'
JS='''
(()=>{const $=s=>document.querySelector(s), root=document.documentElement, theme=$('#theme');
function setTheme(v){root.dataset.tema=v;theme.textContent='Tema: '+v;theme.setAttribute('aria-pressed',String(v==='claro'))}try{setTheme(localStorage.getItem('megabrain.pop.tema')==='claro'?'claro':'escuro')}catch(_){setTheme('escuro')}
theme.disabled=false;theme.onclick=()=>{const v=root.dataset.tema==='claro'?'escuro':'claro';setTheme(v);try{localStorage.setItem('megabrain.pop.tema',v)}catch(_){say('Tema alterado nesta janela; preferência não pôde ser salva.')}};
let timer;function say(t){$('#toast').textContent=t;clearTimeout(timer);timer=setTimeout(()=>$('#toast').textContent='',5500)}
async function copy(t){try{if(navigator.clipboard){await navigator.clipboard.writeText(t);say('Caminho completo copiado.');return}}catch(_){}const a=document.createElement('textarea');a.value=t;a.setAttribute('aria-label','Caminho completo para copiar');document.body.append(a);a.select();let ok=false;try{ok=document.execCommand('copy')}catch(_){}if(ok){a.remove();say('Caminho completo copiado.')}else{say('Cópia automática indisponível. O caminho está selecionado: use Ctrl+C.');a.focus();a.select()}}
document.querySelectorAll('[data-copy]').forEach(b=>{b.disabled=false;b.onclick=()=>copy(b.dataset.copy)});
const normalize=v=>v.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();
function filter(){const q=normalize($('#q').value),state=$('#state').value;let count=0,old=0;document.querySelectorAll('article[data-search]').forEach(a=>{const show=normalize(a.dataset.search).includes(q)&&(!state||a.dataset.state===state);a.hidden=!show;if(show){count++;if(a.dataset.origin!=='registro')old++}});$('#count').textContent=count+' destino(s) encontrado(s)';$('#empty').hidden=count!==0;if(q||state)$('#legacy').open=old>0;}
$('#q').disabled=false;$('#state').disabled=false;$('#q').oninput=filter;$('#state').onchange=filter;filter();
})();
'''
def controles(row):
    a=(f'<a class="button primary" href="{e(row["arquivo_url"])}">Abrir entrega</a>' if row.get('arquivo_url') else '')
    return a+f'<a class="button" href="{e(row["pasta_url"])}">Abrir pasta</a><button disabled data-copy="{e(row.get("arquivo") or row["pasta"])}">Copiar caminho</button>'
def card(row):
    search=' '.join(str(row.get(k,'')) for k in ('titulo','projeto','tarefa','sessao','pasta','arquivo','estado','pedido_inicial','pedido_atual','etapa'))
    compass=''
    if any(row.get(k) for k in ('pedido_inicial','pedido_atual','etapa')):
        compass='<div class="compass"><b>Contexto desta entrega</b>'+''.join(f'<div>{label}: {e(row[key])}</div>' for key,label in (('pedido_inicial','Começou'),('pedido_atual','Agora'),('etapa','Etapa')) if row.get(key))+'</div>'
    return f'''<article data-search="{e(search)}" data-origin="{e(row['origem'])}" data-state="{e(row['estado'])}"><div class="row-head"><h3>{e(row['titulo'])}</h3><span class="tag">{e(row['estado'].replace('_',' '))}</span></div><div class="meta">Projeto: {e(row['projeto'])} · Sessão: {e(row['sessao'])} · Origem: {e(row['origem'])}</div>{compass}<p>{e(row['proxima_acao'])}</p><div class="actions">{controles(row)}</div><code class="path">{e(row.get('arquivo') or row['pasta'])}</code><div class="meta">Fonte: {e(row['fonte'])}<br>Data registrada: {e(row.get('atualizado_em','não informada'))}</div></article>'''
def gerar_html(data):
    reg=[x for x in data['entregas'] if x['origem']=='registro']; leg=[x for x in data['entregas'] if x['origem']!='registro']
    rel=f'<a class="button" href="{e(Path(data["relatorio"]).as_uri())}">Relatório técnico</a>' if data['relatorio'] else ''
    cards=''.join(card(x) for x in reg) or '<p class="muted">Nenhuma entrega registrada ainda. O acervo abaixo preserva os destinos existentes.</p>'
    return f'''<!doctype html><html lang="pt-BR" data-tema="escuro"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MEGABRAIN · Início</title><style>{CSS}</style></head><body>{MARCADOR}<main><header><div><div class="eyebrow">MEGABRAIN / SUA ENTRADA FIXA</div><h1>O que você precisa ver.</h1></div><button id="theme" disabled aria-pressed="false">Tema: escuro</button></header><p>Entregas e próximos passos em um endereço. Cada item mostra de qual projeto e sessão veio.</p><div class="actions"><a class="button" href="{e(Path(data['pasta']).as_uri())}">Pasta de entregas</a><button disabled data-copy="{e(data['pasta'])}">Copiar pasta completa</button>{rel}</div><code class="path">{e(data['pasta'])}</code><noscript>Busca, cópia e tema precisam de JavaScript. Os links e caminhos abaixo continuam disponíveis.</noscript><section class="focus"><div class="eyebrow">ENTREGAS REGISTRADAS</div>{cards}</section><div class="toolbar"><label>Buscar por tarefa, projeto ou caminho<input disabled id="q" type="search" placeholder="Ex.: plataforma, Portfolio, Figma" autocomplete="off"></label><label>Estado declarado<select disabled id="state"><option value="">Todos os estados</option>{''.join(f'<option value="{x}">{x.replace("_"," ")}</option>' for x in ESTADOS)}</select></label></div><p id="count" role="status" aria-live="polite">{len(data['entregas'])} destinos</p><p id="empty" class="empty" hidden>Nenhum destino corresponde à busca. Apague o termo ou selecione todos os estados.</p><details id="legacy"><summary>Acervo anterior e registros técnicos ({len(leg)})</summary><p class="muted">Os arquivos permanecem no endereço original. “Não verificado” significa que ainda não há estado explícito; uma revisão de IA não é aprovação humana.</p>{''.join(card(x) for x in leg)}</details><section class="guide"><h2>A mesma esteira, na medida do pedido.</h2><ol><li>Entender o pedido e recuperar o contexto.</li><li>Ativar enquadramento, pesquisa, execução e revisão conforme o caso.</li><li>Verificar o resultado e entregar um destino que abre.</li><li>Guardar só decisões e aprendizados que mudam o trabalho.</li></ol><p>A sensibilidade muda revisões opcionais. Autorização, verificação necessária e preservação do seu trabalho continuam obrigatórias.</p><p class="muted">No aplicativo MEGABRAIN, use “Sensibilidade”. Este HTML é uma fotografia navegável; sozinho não altera configurações nem acompanha sessões ao vivo.</p></section><footer>Gerado em {e(data['gerado_em'])}. Projeto: <code class="path">{e(data['projeto'])}</code>“Abrir pasta” pode abrir a listagem do navegador. No aplicativo, abre o Explorer. Fontes: registro de entregas e diretório local; a geração não certifica o conteúdo dos arquivos.</footer></main><div id="toast" role="status" aria-live="polite"></div><script>{JS}</script></body></html>'''
def gerar(projeto):
    data=coletar(projeto); root=Path(data['projeto']); out=caminho(root,'00_PARA-VOCE/INICIO.html')
    recibo=caminho(root,'dados/catalogo-geracao.json')
    with trava.travado(out,agente=trava.agente_script('mb-catalogo'),motivo='Gerar entrada de entregas'):
        if out.exists():
            if MARCADOR not in out.read_text(encoding='utf-8-sig'): raise ValueError('INICIO.html existe sem marcador do gerador; preservado.')
            anterior=json.loads(recibo.read_text(encoding='utf-8-sig')) if recibo.exists() else {}
            if anterior.get('sha256') != hashlib.sha256(out.read_bytes()).hexdigest(): raise ValueError('INICIO.html mudou fora do gerador; edição preservada. Revise antes de regenerar.')
        out.parent.mkdir(parents=True,exist_ok=True)
        if not u.atomic_write_text(out,gerar_html(data)): raise OSError('Falha gravando entrada')
        recibo.parent.mkdir(parents=True,exist_ok=True)
        if not u.atomic_write_text(recibo,json.dumps({'schema_version':1,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'gerado_em':data['gerado_em']},indent=2)): raise OSError('Entrada gerada; recibo não salvo. Conferir antes de regenerar.')
    return out
