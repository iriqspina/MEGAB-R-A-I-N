// Verificações do estado da home sem dependências de teste. Uso pelo coordenador, por exemplo:
//   npx tsx -e "import('./src/home-state.check.ts').then(m=>{const f=m.runHomeStateChecks();console.log(f.length?f:'ok');process.exit(f.length?1:0)})"
// Não é importado pelo aplicativo.
import {addPanel,adjustLayout,homeLayout,homeLayoutKey,normalizeHome,orderProjects,panelKey,parsePanelPayload,recentDeliveries,removePanel,resolvePanel,HOME_PANEL_LIMIT,type HomeCatalog} from './home-state';
import type {HomePanel,Job,LayoutItem,Project,ProjectDetail,Workspace} from './types';

const base:Workspace={openProjects:[],activeProject:null,compareProject:null,layouts:{},hiddenModules:{},density:'comfortable',longPressMs:1000,views:[]};
const project=(id:string,updated_at?:string):Project=>({id,name:`Projeto ${id}`,updated_at});
const panel=(kind:HomePanel['kind'],pid:string,ref?:string):HomePanel=>({key:panelKey(kind,pid,ref),kind,project_id:pid,ref,title:`${kind} ${pid}`});
const detail=(pid:string,deliveries:ProjectDetail['deliveries'],updated_at?:string):ProjectDetail=>({project:project(pid,updated_at),deliveries,assets:[],activity:[],sessions:[],comments:[],revision:'r'});
const row=(layout:LayoutItem[],i:string)=>layout.find(a=>a.i===i);

export function runHomeStateChecks():string[]{
  const failures:string[]=[];const check=(name:string,ok:boolean)=>{if(!ok)failures.push(name);};

  // Estado salvo malformado não derruba e não ultrapassa o limite.
  const many=Array.from({length:8},(_,n)=>({kind:'project',project_id:`p${n}`,title:`P${n}`,key:'chave forjada'}));
  const messy={...base,layouts:'quebrado' as unknown as Workspace['layouts'],homePanels:['x',null,{kind:'shell',project_id:'a'},{kind:'process',project_id:'a'},many[0],...many] as unknown as HomePanel[]};
  const n1=normalizeHome(messy);
  check('limite de painéis',n1.ws.homePanels!.length===HOME_PANEL_LIMIT);
  check('excedente informado',n1.overflow===2);
  check('inválidos contados',n1.invalid===4);
  check('chave recalculada',n1.ws.homePanels![0].key==='project:p0:');
  check('layouts não-objeto viram vazio',typeof n1.ws.layouts==='object'&&!Array.isArray(n1.ws.layouts));
  check('view padrão é home',n1.ws.view==='home'&&n1.ws.startView==='home');

  // Geometria inválida é corrigida; layouts de projeto ficam intactos.
  const legacy=[{i:'now',x:0,y:0,w:4,h:4}];
  const n2=normalizeHome({...base,homePanels:[panel('project','a')],layouts:{'a:flex:desk':legacy,'home:desktop':[{i:'project:a:',x:Number.NaN,y:0,w:6,h:9},{i:'project:a:',x:40,y:-5,w:99,h:1000},{i:'fantasma',x:0,y:0,w:6,h:6}] as LayoutItem[]}});
  const fixed=n2.ws.layouts['home:desktop'];
  check('layout de projeto preservado',n2.ws.layouts['a:flex:desk']===legacy);
  check('geometria limitada',fixed.length===1&&fixed[0].w===12&&fixed[0].x===0&&fixed[0].y===0&&fixed[0].h===40);

  // Payload de arraste forjado: só tipo e ids passam; título/destino vêm do catálogo.
  const forged=parsePanelPayload(JSON.stringify({kind:'report',project_id:'a',ref:'f1',url:'javascript:alert(1)',title:'falso'}));
  check('payload sem url/título',!!forged&&!('url' in forged)&&!('title' in forged));
  check('payload inválido',parsePanelPayload('{"kind":"report","project_id":"a"}')===null&&parsePanelPayload('não é json')===null);
  const jobs:Job[]=[{id:'j1',project_id:'a',status:'running',title:'Pedido 1'},{id:'j2',project_id:'a',status:'completed',title:'Pedido 2'},{id:'j3',project_id:'b',status:'running',title:'Outro'}];
  const catalog:HomeCatalog={projects:[project('a'),project('b')],jobs,reports:pid=>pid==='a'?[{id:'f1',title:'Relatório real',type:'html',url:'/api/files/f1'}]:null};
  check('relatório fora do catálogo recusado',resolvePanel({kind:'report',project_id:'a',ref:'f9'},catalog)===null);
  check('relatório do catálogo usa título real',resolvePanel(forged!,catalog)?.title==='Relatório real');
  check('projeto inexistente recusado',resolvePanel({kind:'project',project_id:'z'},catalog)===null);
  check('pedido de outro projeto recusado',resolvePanel({kind:'process',project_id:'a',ref:'j3'},catalog)===null);
  const k1=resolvePanel({kind:'process',project_id:'a',ref:'j1'},catalog)?.key,k2=resolvePanel({kind:'process',project_id:'a',ref:'j2'},catalog)?.key;
  check('dois pedidos do mesmo projeto distintos',!!k1&&!!k2&&k1!==k2);

  // Lado a lado: primeira abertura redistribui; organização manual é preservada.
  const A=panel('project','a'),B=panel('project','b'),C=panel('process','a','j1');
  check('um painel ocupa a largura',row(homeLayout([A],undefined,12),A.key)?.w===12);
  const two=homeLayout([A,B],undefined,12);
  check('dois painéis na mesma linha',row(two,A.key)?.y===row(two,B.key)?.y&&row(two,A.key)?.w===6&&row(two,B.key)?.x===6);
  const manual=[{i:A.key,x:6,y:0,w:6,h:9},{i:B.key,x:0,y:0,w:6,h:9}];
  const three=homeLayout([A,B,C],manual,12);
  check('manual preservado ao abrir C',row(three,A.key)?.x===6&&row(three,B.key)?.x===0&&(row(three,C.key)?.y||0)>=9);
  const mobile=homeLayout([A,B,C],undefined,1);
  check('celular em uma coluna',mobile.every(a=>a.x===0&&a.w===1)&&homeLayoutKey(1)!==homeLayoutKey(12));

  // Abrir/fechar: limite avisa sem retirar; duplicata não duplica; soltura só posiciona em grade organizada.
  const full={...base,homePanels:Array.from({length:HOME_PANEL_LIMIT},(_,n)=>panel('project',`p${n}`))};
  const r1=addPanel(full,A);check('limite não retira painéis',r1.status==='full'&&r1.ws.homePanels!.length===HOME_PANEL_LIMIT);
  const withA={...base,homePanels:[A]};
  check('duplicata detectada',addPanel(withA,A).status==='exists');
  check('soltura em grade automática não grava posição',!addPanel(withA,B,{x:7,y:3,cols:12}).ws.layouts['home:desktop']);
  const dropped=addPanel({...withA,layouts:{'home:desktop':[{i:A.key,x:0,y:0,w:12,h:9}]}},B,{x:11,y:2,cols:12}).ws.layouts['home:desktop'];
  check('soltura em grade organizada posiciona dentro das colunas',row(dropped,B.key)?.x===6&&row(dropped,B.key)?.y===2);
  const removed=removePanel({...base,homePanels:[A,B],layouts:{'home:desktop':[{i:A.key,x:0,y:0,w:6,h:9}],'home:mobile':[{i:A.key,x:0,y:0,w:1,h:9}]}},A.key);
  check('fechar limpa as duas larguras',removed.homePanels!.length===1&&!removed.layouts['home:desktop'].length&&!removed.layouts['home:mobile'].length);
  const widened=adjustLayout(two,A.key,'wide',12);check('alternar largura',row(widened,A.key)?.w===12&&row(widened,A.key)?.x===0);

  // Recentes pela data da entrega, não do projeto; sem data no fim; histórico fora.
  const projects=[project('velho','2020-01-01T00:00:00Z'),project('novo','2026-10-01T00:00:00Z')];
  const details={velho:detail('velho',[{id:'d1',title:'Entrega nova de projeto antigo',updated_at:'2026-10-12T10:00:00Z'},{id:'d2',title:'Sem data'},{id:'d3',title:'Histórica',updated_at:'2026-10-13T00:00:00Z',historical:true} as ProjectDetail['deliveries'][number]]),novo:detail('novo',[{id:'d4',title:'Mais antiga',updated_at:'2026-09-01T00:00:00Z'}])};
  const recent=recentDeliveries(projects,details,8);
  check('recente global pela data da entrega',recent[0]?.delivery.id==='d1'&&recent[1]?.delivery.id==='d4');
  check('sem data no fim',recent.at(-1)?.delivery.id==='d2'&&recent.at(-1)?.at===null);
  check('histórico excluído',!recent.some(r=>r.delivery.id==='d3'));
  check('em andamento primeiro',orderProjects(projects,new Set(['velho']))[0].id==='velho'&&orderProjects(projects,new Set())[0].id==='novo');
  return failures;
}
