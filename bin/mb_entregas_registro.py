"""Escritor do registro explícito de entregas, sem mover ou presumir aprovação."""
import datetime as dt
import json
from pathlib import Path
import mb_trava as t
import mb_utils as u
from mb_catalogo import coletar, caminho, ESTADOS, LEITURA

def registrar(projeto, item):
    root=Path(projeto).resolve(strict=True); p=caminho(root,'dados/entregas.json')
    for key in ('id','titulo','tarefa','sessao','pasta','estado','proxima_acao'):
        if not isinstance(item.get(key),str) or not item[key].strip(): raise ValueError('Campo obrigatório: '+key)
    if item['estado'] not in ESTADOS: raise ValueError('Estado inválido')
    for key in ('pedido_inicial','pedido_atual','etapa'):
        if key in item and (not isinstance(item[key],str) or len(item[key])>400): raise ValueError('Resumo inválido: '+key)
    folder=caminho(root,item['pasta']); file=caminho(root,item['arquivo']) if item.get('arquivo') else None
    if not folder.is_dir() or file and (not file.is_file() or not file.is_relative_to(folder) or file.suffix.lower() not in LEITURA): raise ValueError('Destino inválido')
    with t.travado(p,agente=t.agente_script('mb-entregas-registro'),motivo='Registrar entrega explícita'):
        doc=json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else {'schema_version':1,'revision':0,'entregas':[]}
        if not isinstance(doc,dict) or doc.get('schema_version')!=1 or not isinstance(doc.get('entregas'),list): raise ValueError('Registro inválido; preservado')
        # Check existing records before modifying the registry.
        if p.exists(): coletar(root)
        doc['entregas']=[row for row in doc['entregas'] if row['id']!=item['id']]
        doc['entregas'].insert(0,dict(item,projeto=root.name,atualizado_em=dt.datetime.now().astimezone().isoformat(timespec='seconds')))
        doc['revision']=doc.get('revision',0)+1;p.parent.mkdir(parents=True,exist_ok=True)
        if not u.atomic_write_text(p,json.dumps(doc,ensure_ascii=False,indent=2)+'\n'): raise OSError('Falha gravando registro')
    return item['id']
