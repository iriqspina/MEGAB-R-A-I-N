"""Local settings requests: allowlisted deltas, revision checks and GUI receipts.

This module has no Qt dependency. The central never overwrites widget settings;
only the existing widget's event loop applies an accepted request.
"""
from __future__ import annotations
import hashlib,json,os,re,time,uuid
from pathlib import Path
from . import paths,persistence

VERSION=1
FONTS=['Segoe UI','Segoe UI Variable Display','Bahnschrift','Cascadia Code','Consolas','Inter','Arial','Verdana','Trebuchet MS','Georgia','Calibri','Tahoma']
PROVIDERS={'codex':'Codex','codex_gpt2':'Codex · segunda conta','claude':'Claude','spark':'Codex Spark','zai':'Z.ai','gemini_cli':'Gemini CLI','gemini_web':'Gemini','antigravity':'Antigravity'}
CHOICES={'visual_mode':['legacy','trilho'],'surface_preset':['carvao','meia_noite','ameixa','musgo','telha','nevoa','papel'],
 'font_family':FONTS,'scale':[0.8,0.9,1.0,1.15,1.3,1.5],
 'number_mode':['used','remaining'],'reset_mode':['relative','absolute'],
 'poll_minutes':[2,5,10,15,30],'alert_percent':[0,75,90],'hover_mode':['none','opaque','fade'],'layout':['horizontal','vertical']}
RANGES={'size_name':(8,32),'size_value':(10,48),'size_hint':(8,28),'size_detail':(8,28),'bg_opacity_percent':(20,100),'strip_height':(40,10000),'strip_width':(360,10000)}
RANGES.update({'window_width':(240,10000),'window_height':(40,10000)})
BOOLS={'always_on_top','expanded','show_pacing','show_footer','lock_position','click_through','snap_edges'}
ALLOWED=set(CHOICES)|set(RANGES)|BOOLS|{'visible_providers','provider_order'}

def atomic_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
        os.replace(temp,path)
    finally:
        if temp.exists():temp.unlink()

def read_raw():
    if not paths.SETTINGS_PATH.exists():return {},b''
    data=paths.SETTINGS_PATH.read_bytes()
    value=json.loads(data.decode('utf-8-sig'))
    if not isinstance(value,dict):raise ValueError('Configuração local inválida; o arquivo foi preservado.')
    return value,data

def settings_view():
    raw,data=read_raw()
    merged=persistence.migrate_settings(raw)
    return {'revision':hashlib.sha256(data).hexdigest(),'values':{k:merged.get(k) for k in sorted(ALLOWED)},
            'contract_version':VERSION,'schema':{'choices':CHOICES,'ranges':RANGES,'booleans':sorted(BOOLS),'providers':PROVIDERS}}

def validate_patch(changes):
    if not isinstance(changes,dict) or not changes or set(changes)-ALLOWED:raise ValueError('Escolha apenas configurações visuais ou de comportamento do widget.')
    for key,value in changes.items():
        if key in BOOLS and not isinstance(value,bool):raise ValueError('Opção booleana inválida: '+key)
        if key in RANGES:
            lo,hi=RANGES[key]
            if key in {'window_width','window_height'} and value is None:continue
            if isinstance(value,bool) or not isinstance(value,int) or not lo<=value<=hi:raise ValueError('Valor fora do intervalo: '+key)
        if key in CHOICES:
            if isinstance(value,bool) or value not in CHOICES[key]:raise ValueError('Opção inválida: '+key)
        if key=='visible_providers':
            if not isinstance(value,dict) or set(value)-set(PROVIDERS) or any(not isinstance(v,bool) for v in value.values()):raise ValueError('Visibilidade de provedores inválida.')
        if key=='provider_order':
            if not isinstance(value,list) or len(value)>len(PROVIDERS) or any(not isinstance(v,str) or v not in PROVIDERS for v in value) or len(set(value))!=len(value):raise ValueError('Ordem dos provedores inválida.')
    return changes

def request_patch(changes,expected_revision):
    validate_patch(changes)
    if not isinstance(expected_revision,str) or not re.fullmatch('[a-f0-9]{64}',expected_revision):raise ValueError('Releia a configuração antes de salvar.')
    if settings_view()['revision']!=expected_revision:raise ValueError('A configuração mudou. Releia antes de salvar para preservar a alteração mais recente.')
    ident=uuid.uuid4().hex
    atomic_json(paths.DATA_DIR/'settings-requests'/(ident+'.json'),{'id':ident,'at':time.time(),'expected_revision':expected_revision,'changes':changes})
    return {'request_id':ident,'status':'requested','message':'Pedido enviado; aguardando a aplicação no widget.'}

def request_status(ident):
    if not isinstance(ident,str) or not re.fullmatch('[a-f0-9]{32}',ident):raise ValueError('Pedido de configuração inválido.')
    folder=paths.DATA_DIR/'settings-requests'
    receipt=folder/(ident+'.receipt.json')
    if receipt.is_file():
        data=json.loads(receipt.read_text(encoding='utf-8'))
        if data.get('status')=='applied':data['changed_since_apply']=settings_view()['revision']!=data.get('revision')
        return data
    request=folder/(ident+'.json')
    if not request.is_file():return {'request_id':ident,'status':'not_found','message':'Pedido não encontrado.'}
    age=time.time()-json.loads(request.read_text(encoding='utf-8'))['at']
    if age>20:return {'request_id':ident,'status':'unavailable','message':'O widget não confirmou a alteração. A configuração não foi marcada como aplicada; reabra o widget para carregar esta integração.'}
    return {'request_id':ident,'status':'requested','message':'Aguardando confirmação do widget.'}

def process_requests(apply):
    folder=paths.DATA_DIR/'settings-requests'
    if not folder.is_dir():return
    pending=[p for p in folder.glob('*.json') if re.fullmatch('[a-f0-9]{32}',p.stem) and not p.with_name(p.stem+'.receipt.json').exists()]
    for path in sorted(pending)[:20]:
        ident=path.stem
        if not re.fullmatch('[a-f0-9]{32}',ident):continue
        receipt=folder/(ident+'.receipt.json')
        if receipt.exists():continue
        try:
            if path.stat().st_size>16384:raise ValueError('Pedido grande demais.')
            request=json.loads(path.read_text(encoding='utf-8'))
            age=time.time()-request['at']
            if not 0<=age<=20:raise ValueError('Pedido expirou sem aplicação. Releia e tente novamente.')
            validate_patch(request['changes'])
            result=apply(request['changes'],request['expected_revision'])
            result={**result,'request_id':ident,'applied_at':time.time(),'contract_version':VERSION}
        except Exception as exc:
            result={'request_id':ident,'status':'rejected','message':str(exc)[:500],'contract_version':VERSION}
        atomic_json(receipt,result)
