from pathlib import Path
import datetime as dt,hashlib,json,re,sys,subprocess
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'bin'))
from mb_entregas_registro import registrar
from mb_catalogo import gerar
import mb_trava as t
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def suite(name):
 p=HERE/name;s=p.read_text(encoding='utf-8-sig',errors='replace');m=re.search(r'Ran (\d+) tests in ([\d.]+)s',s)
 return {'arquivo':str(p),'testes':int(m[1]) if m else None,'segundos':float(m[2]) if m else None,'falhas':re.findall(r'^(?:FAIL|ERROR): (.+)$',s,re.M),'sha256':sha(p)}
baseline=suite('testes-antes.log');motor=suite('testes-finais.log');auto=suite('testes-automations-finais.log');dash=suite('testes-dashboard-finais.log')
ready='--concluir' in sys.argv
proof={'schema_version':1,'medido_em':dt.datetime.now().astimezone().isoformat(),'estado':'verificado_no_escopo' if ready else 'em_verificacao_visual','baseline':baseline,'motor':motor,'automacoes':auto,'dashboard':dash,'novas_falhas_motor':sorted(set(motor['falhas'])-set(baseline['falhas'])),'limites':['As duas falhas preexistentes continuam abertas.','Teste automatizado e inspeção visual não medem satisfação no uso prolongado.','Não certifica ativação em todas as sessões e clientes.','Arquivos antigos não foram movidos nem ocultados.'],'revisao_independente':str(HERE/'revisao-candidato.md'),'revisao_plano_v6':'260916_175608_306d11cb'}
if ready:
 for key,file in [('navegador','ui-browser.json'),('aplicativo','ui-nativo.json')]:
  d=json.loads((HERE/file).read_text(encoding='utf-8'));proof[key]={'arquivo':str(HERE/file),'passou':d['pass'],'verificacoes':len(d['tests']),'sha256':sha(HERE/file)}
 if proof['novas_falhas_motor'] or auto['falhas'] or dash['falhas'] or not all(proof[k]['passou'] for k in ('navegador','aplicativo')):raise RuntimeError('Verificação impede marcar como pronta')
(HERE/'verificacao-final.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
if ready:
 reg=json.loads((ROOT/'dados/entregas.json').read_text(encoding='utf-8'))
 item=next(x for x in reg['entregas'] if x['id']=='plataforma-260916')
 item.update(estado='pronto',etapa='Implementação local verificada; evolução restante documentada.',verificado_sha256=sha(Path(item['arquivo'])),verificacao=str(HERE/'verificacao-final.json'))
 registrar(ROOT,item);gerar(ROOT)
 sources=json.loads((HERE/'baseline.json').read_text(encoding='utf-8'))['sources']
 paths=set(sources)|{'bin/mb_triagem.py','bin/mb-triagem.py','bin/mb_catalogo.py','bin/mb-catalogo.py','bin/mb_entregas_registro.py','bin/mb-entregas-registro.py','apps/automations/automations.py','apps/megabrain-dashboard/dashboard.py','01_acoes/00_ABRIR-MEGABRAIN.vbs','motor/referencias/260916_plataforma-contrato.md','motor/modelos/260916_ENTREGA.json','motor/modelos/260916_ESTADO-ATUAL.md','dados/plataforma-backlog.json','dados/preferencias-megabrain.json','apps/automations/tests/test_route_health_260916.py'}
 paths.update(str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'motor/tests').glob('test_mb_*') if any(x in p.name for x in ('triagem','catalogo','plataforma')))
 rows=[]
 for name in sorted(paths):
  p=ROOT/name
  if not p.is_file():continue
  old=sources.get(name,{}).get('sha256');backup=HERE/'backup'/name
  if backup.exists():old=sha(backup)
  if old==sha(p):continue
  rows.append({'arquivo':str(p),'sha256_final':sha(p),'sha256_inicial':old,'backup':str(backup) if backup.exists() else None,'observacao':'Estado ao finalizar; conferir edição posterior antes de reverter.'})
 (HERE/'manifesto-final.json').write_text(json.dumps({'schema_version':1,'medido_em':proof['medido_em'],'arquivos':rows,'sincronizacoes':str(HERE/'sincronizacao.json'),'gerados':['00_PARA-VOCE/INICIO.html','00_painel/RELATORIO.html','dados/estado.json'],'restauracao':'REVERTER.md'},ensure_ascii=False,indent=2),encoding='utf-8')
 print('Entrega pronta, verificação e manifesto gravados.')
else:print('Recibo criado; validação visual final pendente.')
