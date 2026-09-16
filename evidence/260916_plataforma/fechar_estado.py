from pathlib import Path
import json,sys,subprocess
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'bin'))
import mb_trava as t
def edit(relative,fn):
 p=ROOT/relative
 with t.travado(p,agente='codex-plataforma-2242',motivo='Fechar integração verificada da análise Claude'):
  text=p.read_text(encoding='utf-8-sig');new=fn(text)
  if new!=text:p.write_text(new,encoding='utf-8')
def backlog(text):
 d=json.loads(text)
 for x in d['itens']:
  if x['id'] in ('PLAT-01','PLAT-02'):x['estado']='implementado_verificado_localmente'
  if x['id']=='PLAT-06':x['fonte']='evidence/260916_plataforma/contexto-medicao.md'
  if x['id']=='PLAT-04':x['criterio']+='; ocultação também deve preservar os resultados das buscas em cada cliente'
 return json.dumps(d,ensure_ascii=False,indent=2)+'\n'
edit('dados/plataforma-backlog.json',backlog)
note='Integração Claude: bússola por entrega implementada; plano original vinculado. O falso zero do medidor foi corrigido por consulta ao campo evento: 177 registros nos cinco logs citados. Ativação atual por cliente continua distinta de registro histórico.\n'
edit('memoria/estado/HANDOFF.md',lambda s:s.replace('Verificação e limites:',note+'Verificação e limites:',1) if 'Integração Claude: bússola' not in s else s)
edit('memoria/estado/ESTADO.md',lambda s:s.replace('Aberto: consolidar aplicações',note+'Aberto: consolidar aplicações',1) if 'Integração Claude: bússola' not in s else s)
lesson='''\n## 260916 — valor do evento não é nome de campo
GATILHO: relatório conclui que o medidor está ausente porque d.get('contexto_injetado') retorna vazio.
LIÇÃO: o nome procurado era o valor de evento; a consulta errada encontrou zero onde os cinco logs tinham 177 registros.
ATALHO: inspecionar o formato de uma linha, reproduzir consulta correta e distinguir registro histórico, código instalado e ativação no cliente atual antes de propor outro medidor.
'''
edit('memoria/nucleo/licoes-megabrain.md',lambda s:s if '## 260916 — valor do evento não é nome de campo' in s else s+lesson)
# O dashboard estava sem alterações na medição inicial; recupera bytes exatos do mesmo commit.
rel='apps/megabrain-dashboard/dashboard.py';dest=HERE/'backup'/rel
initial=(HERE/'git-antes.txt').read_text(encoding='utf-8');base=json.loads((HERE/'baseline.json').read_text(encoding='utf-8'))
if not dest.exists() and rel not in initial:
 old=subprocess.run(['git','show',base['head']+':'+rel],cwd=ROOT,capture_output=True,check=True).stdout
 dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(old)
print('Estado final e lição registrados, histórico preservado.')
