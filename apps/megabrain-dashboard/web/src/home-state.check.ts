// Verificações do estado da home sem dependências de teste. Uso pelo coordenador, por exemplo:
//   npx tsx -e "import('./src/home-state.check.ts').then(m=>{const f=m.runHomeStateChecks();console.log(f.length?f:'ok');process.exit(f.length?1:0)})"
// Não é importado pelo aplicativo.
import {addPanel,adjustLayout,dedupeReports,homeLayout,homeLayoutKey,mergeLayout,normalizeHome,openOwner,orderProjects,panelKey,parsePanelPayload,pinOwners,recentDeliveries,removePanel,replaceLayoutItems,resetOpenLayout,resolvePanel,routingOwners,sanitizePreview,splitRendered,toPanelInput,GLOBAL_PID,HOME_PANEL_LIMIT,HOME_SECTIONS_VERSION,STRIP_MODULES,type HomeCatalog} from './home-state';
import type {HomePanel,Job,LayoutItem,Project,ProjectDetail,Workspace} from './types';
import {isPinClosed,setPinClosed} from './home-state';
import {catalogState,classifyReturnArrivals,promotePanel} from './home-state';

const base:Workspace={openProjects:[],activeProject:null,compareProject:null,layouts:{},hiddenModules:{},density:'comfortable',longPressMs:1000,views:[]};
const project=(id:string,updated_at?:string):Project=>({id,name:`Projeto ${id}`,updated_at});
const panel=(kind:HomePanel['kind'],pid:string,ref?:string):HomePanel=>({key:panelKey(kind,pid,ref),kind,project_id:pid,ref,title:`${kind} ${pid}`});
const detail=(pid:string,deliveries:ProjectDetail['deliveries'],updated_at?:string):ProjectDetail=>({project:project(pid,updated_at),deliveries,assets:[],activity:[],sessions:[],comments:[],revision:'r'});
const row=(layout:LayoutItem[],i:string)=>layout.find(a=>a.i===i);
const geom=(a?:LayoutItem)=>a?`${a.x},${a.y},${a.w},${a.h}`:'ausente';
// Simula salvar no /workspace e ler de novo (boot/recarga).
const reload=(ws:Workspace)=>normalizeHome(JSON.parse(JSON.stringify(ws)) as Workspace).ws;
const HASH='a'.repeat(64);

export function runHomeStateChecks():string[]{
  const failures:string[]=[];const check=(name:string,ok:boolean)=>{if(!ok)failures.push(name);};

  // Estado salvo malformado não derruba; nenhum painel válido é cortado do estado.
  const many=Array.from({length:HOME_PANEL_LIMIT+2},(_,n)=>({kind:'project',project_id:`p${n}`,title:`P${n}`,key:'chave forjada'}));
  const messy={...base,layouts:'quebrado' as unknown as Workspace['layouts'],homePanels:['x',null,{kind:'shell',project_id:'a'},{kind:'process',project_id:'a'},many[0],...many] as unknown as HomePanel[]};
  const n1=normalizeHome(messy);
  check('acima do teto continua salvo',n1.ws.homePanels!.filter(p=>p.kind!=='strip').length===HOME_PANEL_LIMIT+2&&n1.ws.homePanels!.filter(p=>p.kind==='strip').length===3);
  check('excedente de exibição informado',n1.overflow===2);
  const split=splitRendered(n1.ws.homePanels!);
  check('teto só na exibição',split.shown.filter(p=>p.kind!=='strip').length===HOME_PANEL_LIMIT&&split.waiting.length===2&&split.waiting[0].project_id===`p${HOME_PANEL_LIMIT}`&&split.shown.filter(p=>p.kind==='strip').length===3);
  check('inválidos contados',n1.invalid===4);
  check('chave recalculada',n1.ws.homePanels!.find(p=>p.kind==='project')?.key==='project:p0:');
  check('layouts não-objeto viram vazio',typeof n1.ws.layouts==='object'&&!Array.isArray(n1.ws.layouts));
  check('view padrão é home',n1.ws.view==='home'&&n1.ws.startView==='home');

  // Geometria inválida é corrigida; layouts de projeto ficam intactos; geometria de fechado é guardada.
  const legacy=[{i:'now',x:0,y:0,w:4,h:4}];
  const n2=normalizeHome({...base,homePanels:[panel('project','a')],layouts:{'a:flex:desk':legacy,'home:desktop':[{i:'project:a:',x:Number.NaN,y:0,w:6,h:9},{i:'project:a:',x:40,y:-5,w:99,h:1000},{i:'fechado',x:2,y:3,w:6,h:6}] as LayoutItem[]}});
  const fixed=n2.ws.layouts['home:desktop'];
  check('layout de projeto preservado',n2.ws.layouts['a:flex:desk']===legacy);
  check('geometria limitada',geom(row(fixed,'project:a:'))==='0,0,12,40');
  check('geometria de painel fechado mantida',geom(row(fixed,'fechado'))==='2,3,6,6');

  // Workspace legado: tipos antigos e demais campos passam sem mudança.
  const legacyWs={...base,openProjects:['a'],activeProject:'a',compareProject:'b',hiddenModules:{a:['process']},startView:'last' as const,view:'project' as const,responseViews:[{id:'f1',title:'R',type:'html',url:'/api/files/f1',project_id:'a'}],compareRatio:40,
    homePanels:[{key:'x',kind:'project',project_id:'a',title:'Projeto A'},{key:'y',kind:'process',project_id:'a',ref:'j1',title:'Pedido 1'},{key:'z',kind:'report',project_id:'a',ref:'f2',title:'Relatório 2'}] as HomePanel[]};
  const n3=normalizeHome(legacyWs);
  check('legado: três painéis com títulos salvos',n3.invalid===0&&n3.ws.homePanels!.filter(p=>p.kind!=='strip').map(p=>`${p.key}|${p.title}`).join(';')==='project:a:|Projeto A;process:a:j1|Pedido 1;report:a:f2|Relatório 2');
  check('legado: demais campos intocados',n3.ws.responseViews===legacyWs.responseViews&&n3.ws.startView==='last'&&n3.ws.view==='project'&&n3.ws.compareProject==='b'&&n3.ws.hiddenModules===legacyWs.hiddenModules&&n3.ws.openProjects===legacyWs.openProjects&&n3.ws.compareRatio===40);
  check('legado sem snapshot continua sem snapshot',!n3.ws.homePanels![2].preview);

  // Payload de arraste forjado: só tipo e ids passam; título/destino vêm do catálogo.
  const forged=parsePanelPayload(JSON.stringify({kind:'report',project_id:'a',ref:'f1',url:'javascript:alert(1)',title:'falso',preview:{id:'f1',title:'x',type:'html',url:'javascript:alert(1)'}}));
  check('payload sem url/título/snapshot',!!forged&&!('url' in forged)&&!('title' in forged)&&!('preview' in forged));
  check('payload inválido',parsePanelPayload('{"kind":"report","project_id":"a"}')===null&&parsePanelPayload('não é json')===null);
  check('módulo fora da lista recusado',toPanelInput({kind:'module',project_id:'a',ref:'shell'})===null&&toPanelInput({kind:'module',project_id:'a'})===null);
  check('global fora da lista recusado',toPanelInput({kind:'global',project_id:GLOBAL_PID,ref:'now'})===null);
  check('global só com projeto fixo',toPanelInput({kind:'global',project_id:'a',ref:'quotas'})===null);
  check('projeto fixo recusado fora do global',toPanelInput({kind:'project',project_id:GLOBAL_PID})===null&&toPanelInput({kind:'module',project_id:GLOBAL_PID,ref:'now'})===null&&toPanelInput({kind:'report',project_id:GLOBAL_PID,ref:'f1'})===null);
  const jobs:Job[]=[{id:'j1',project_id:'a',status:'running',title:'Pedido 1'},{id:'j2',project_id:'a',status:'completed',title:'Pedido 2'},{id:'j3',project_id:'b',status:'running',title:'Outro'}];
  const catalog:HomeCatalog={projects:[project('a'),project('b')],jobs,reports:pid=>pid==='a'?[{id:'f1',title:'Relatório real',type:'html',url:'/api/files/f1',hash:HASH}]:null};
  check('relatório fora do catálogo recusado',resolvePanel({kind:'report',project_id:'a',ref:'f9'},catalog)===null);
  const resolved=resolvePanel(forged!,catalog);
  check('relatório do catálogo usa título real',resolved?.title==='Relatório real');
  check('snapshot vem do catálogo',resolved?.preview?.url==='/api/files/f1'&&resolved?.preview?.hash===HASH&&resolved?.preview?.project_id==='a');
  check('projeto inexistente recusado',resolvePanel({kind:'project',project_id:'z'},catalog)===null);
  check('módulo de projeto ausente recusado',resolvePanel({kind:'module',project_id:'z',ref:'results'},catalog)===null);
  check('módulo usa título do catálogo',resolvePanel({kind:'module',project_id:'a',ref:'activity'},catalog)?.title==='Atividade');
  check('global não depende de projeto',resolvePanel({kind:'global',project_id:GLOBAL_PID,ref:'quotas'},{...catalog,projects:[]})?.key==='global:*:quotas');
  check('pedido de outro projeto recusado',resolvePanel({kind:'process',project_id:'a',ref:'j3'},catalog)===null);
  const k1=resolvePanel({kind:'process',project_id:'a',ref:'j1'},catalog)?.key,k2=resolvePanel({kind:'process',project_id:'a',ref:'j2'},catalog)?.key;
  check('dois pedidos do mesmo projeto distintos',!!k1&&!!k2&&k1!==k2);

  // Título salvo de módulo/global é ignorado; snapshot salvo é revalidado.
  const n4=normalizeHome({...base,homePanels:[{key:'?',kind:'module',project_id:'a',ref:'results',title:'Forjado'},{key:'?',kind:'global',project_id:GLOBAL_PID,ref:'sessions',title:'Forjado'},
    {key:'?',kind:'report',project_id:'a',ref:'f1',title:'R',preview:{id:'f1',title:'R',type:'html',url:'javascript:alert(1)'}},
    {key:'?',kind:'report',project_id:'a',ref:'f2',title:'R',preview:{id:'outro',title:'R',type:'html',url:'/api/files/f2'}},
    {key:'?',kind:'report',project_id:'a',ref:'f3',title:'R',preview:{id:'f3',title:'R',type:'html',url:'/api/files/f3',hash:HASH,extra:'x'}}] as unknown as HomePanel[]});
  const [m4,g4,bad4,mismatch4,ok4]=n4.ws.homePanels!.filter(p=>p.kind!=='strip');
  check('módulo/global com título do catálogo',m4.title==='Resultados'&&g4.title==='Sessões conectadas');
  check('snapshot com endereço inseguro descartado',!bad4.preview&&bad4.kind==='report');
  check('snapshot de outro relatório descartado',!mismatch4.preview);
  check('snapshot válido mantido sem campos extras',ok4.preview?.hash===HASH&&!('extra' in (ok4.preview||{})));
  check('snapshot exige endereço',sanitizePreview({id:'f',title:'t',type:'html'},'a','f')===undefined);

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

  // Fechar é reversível: A/B automáticos -> fechar A -> mover B -> recarregar -> reabrir A na mesma geometria.
  const desk=homeLayoutKey(12);
  let ws:Workspace={...base,homePanels:[A,B]};
  const auto=homeLayout([A,B],ws.layouts[desk],12);const before=geom(row(auto,A.key));
  ws=removePanel(ws,A.key,{layoutKey:desk,item:row(auto,A.key)!});
  check('fechar retira só da lista',ws.homePanels!.length===1&&ws.homePanels![0].key===B.key);
  const movedB={i:B.key,x:0,y:20,w:4,h:5};
  ws={...ws,layouts:{...ws.layouts,[desk]:mergeLayout(ws.layouts[desk],[movedB],12)}};
  ws=reload(ws);
  ws=addPanel(ws,A).ws;
  const reopened=homeLayout(readOpen(ws),ws.layouts[desk],12);
  check('reabrir A recupera a geometria',geom(row(reopened,A.key))===before);
  check('B mantém o movimento',geom(row(reopened,B.key))==='0,20,4,5');
  check('fechar sem posição efetiva não apaga a guardada',geom(row(removePanel({...base,homePanels:[A],layouts:{[desk]:[{i:A.key,x:3,y:4,w:5,h:6}]}},A.key).layouts[desk],A.key))==='3,4,5,6');
  check('outra largura intocada ao fechar',geom(row(removePanel({...base,homePanels:[A],layouts:{'home:mobile':[{i:A.key,x:0,y:7,w:1,h:8}]}},A.key,{layoutKey:desk,item:{i:A.key,x:0,y:0,w:6,h:9}}).layouts['home:mobile'],A.key))==='0,7,1,8');

  // Acima do teto: salvar a grade não apaga geometria dos que esperam; fechar um exibido revela o próximo.
  const crowd=Array.from({length:HOME_PANEL_LIMIT+2},(_,n)=>panel('project',`c${n}`));
  const waitingGeom={i:crowd[HOME_PANEL_LIMIT].key,x:6,y:50,w:6,h:7};
  let big:Workspace={...base,homePanels:crowd,layouts:{[desk]:[waitingGeom]}};
  const shown=splitRendered(crowd).shown;const grid=homeLayout(shown,big.layouts[desk],12);
  big={...big,layouts:{...big.layouts,[desk]:mergeLayout(big.layouts[desk],grid,12)}};
  check('salvar exibidos preserva quem espera',geom(row(big.layouts[desk],waitingGeom.i))==='6,50,6,7');
  big=reload(removePanel(big,crowd[0].key,{layoutKey:desk,item:row(grid,crowd[0].key)!}));
  const after=splitRendered(big.homePanels!);
  check('fechar um exibido revela o próximo',after.shown.filter(p=>p.kind!=='strip').length===HOME_PANEL_LIMIT&&after.shown.some(p=>p.key===waitingGeom.i)&&after.waiting.length===1&&after.waiting.every(p=>p.kind!=='strip'));
  check('revelado volta com a geometria guardada',geom(row(homeLayout(after.shown,big.layouts[desk],12),waitingGeom.i))==='6,50,6,7');
  check('nenhuma geometria perdida acima do teto',crowd.every(p=>row(big.layouts[desk],p.key)||p.key===crowd[HOME_PANEL_LIMIT+1].key));

  // Abrir: duplicata não duplica; acima do teto salva e espera; soltura só posiciona em grade organizada.
  const full={...base,homePanels:Array.from({length:HOME_PANEL_LIMIT},(_,n)=>panel('project',`p${n}`))};
  const r1=addPanel(full,A);check('acima do teto salva sem retirar',r1.status==='waiting'&&r1.ws.homePanels!.length===HOME_PANEL_LIMIT+1);
  const promotion=promotePanel(r1.ws,A.key);
  check('abrir o décimo terceiro traz à tela',promotion.status==='promoted'&&splitRendered(promotion.ws.homePanels!).shown.some(p=>p.key===A.key));
  check('promover não retira nenhum painel',promotion.ws.homePanels!.length===r1.ws.homePanels!.length&&r1.ws.homePanels!.every(p=>promotion.ws.homePanels!.some(q=>q.key===p.key)));
  const displaced=splitRendered(r1.ws.homePanels!).shown.at(-1)!;
  check('deslocado fica guardado',splitRendered(promotion.ws.homePanels!).waiting.some(p=>p.key===displaced.key));
  check('geometria automática do deslocado congelada',geom(row(promotion.ws.layouts[desk],displaced.key))===geom(row(homeLayout(splitRendered(r1.ws.homePanels!).shown,undefined,12),displaced.key)));
  const promotedSaved=promotePanel({...r1.ws,layouts:{[desk]:[{i:A.key,x:6,y:50,w:6,h:7}],'a:flex:desk':legacy}},A.key);
  check('promover conserva geometria guardada',geom(row(promotedSaved.ws.layouts[desk],A.key))==='6,50,6,7');
  check('promover conserva layout de projeto',promotedSaved.ws.layouts['a:flex:desk']===legacy);
  check('recarregar conserva promoção',splitRendered(reload(promotedSaved.ws).homePanels!).shown.some(p=>p.key===A.key));
  check('abrir exibido é idempotente',promotePanel(promotion.ws,A.key).ws===promotion.ws&&promotePanel(promotion.ws,A.key).status==='shown');
  check('promover ausente não altera estado',promotePanel(promotion.ws,'ausente').ws===promotion.ws&&promotePanel(promotion.ws,'ausente').status==='missing');
  check('catálogo distingue guardado do visível',catalogState(r1.ws,new Set(),new Set(),A)==='stored');
  check('catálogo mostra antes de fechar',catalogState(promotion.ws,new Set(),new Set(),A)==='visible');
  check('catálogo deslocado vira guardado',catalogState(promotion.ws,new Set(),new Set(),displaced)==='stored');
  const withA={...base,homePanels:[A]};
  check('duplicata detectada',addPanel(withA,A).status==='exists');
  check('soltura em grade automática não grava posição',!addPanel(withA,B,{x:7,y:3,cols:12}).ws.layouts['home:desktop']);
  const dropped=addPanel({...withA,layouts:{'home:desktop':[{i:A.key,x:0,y:0,w:12,h:9}]}},B,{x:11,y:2,cols:12}).ws.layouts['home:desktop'];
  check('soltura em grade organizada posiciona dentro das colunas',row(dropped,B.key)?.x===6&&row(dropped,B.key)?.y===2);
  const redrop=addPanel({...withA,layouts:{'home:desktop':[{i:A.key,x:0,y:0,w:12,h:9},{i:B.key,x:0,y:30,w:4,h:11}]}},B,{x:5,y:3,cols:12}).ws.layouts['home:desktop'];
  check('soltura de reaberto atualiza posição sem duplicar chave',redrop.filter(a=>a.i===B.key).length===1&&geom(row(redrop,B.key))==='5,3,4,11');
  const widened=adjustLayout(two,A.key,'wide',12);check('alternar largura',row(widened,A.key)?.w===12&&row(widened,A.key)?.x===0);
  const sideBySide=resetOpenLayout({...base,homePanels:[A],layouts:{[desk]:[{i:A.key,x:0,y:0,w:4,h:4},{i:B.key,x:1,y:1,w:5,h:5}]}},12);
  check('lado a lado preserva fechados',!row(sideBySide.layouts[desk],A.key)&&geom(row(sideBySide.layouts[desk],B.key))==='1,1,5,5');

  // Um dono por relatório: Respostas tem precedência; a geometria do painel da home fica guardada.
  const R=panel('report','a','f1');const owners=new Set(['a:f1']);
  check('promoção respeita editor de Respostas',promotePanel({...base,homePanels:[R]},R.key,owners).status==='elsewhere');
  const waitingReport=panel('report','a','waiting');
  const arrivalWs:Workspace={...base,view:'home',homePanels:[...full.homePanels!,waitingReport],views:[{project_id:'a',id:'closed'},{project_id:'a',id:'unmounted'},{project_id:'a',id:'live'}],closedPins:{'a:closed':true}};
  const arrivals=[{project_id:'a',id:'waiting'},{project_id:'a',id:'closed'},{project_id:'a',id:'unmounted'},{project_id:'a',id:'live'},{project_id:'a',id:'response'},{project_id:'b',id:'fresh'}];
  const arrivalOwners=new Map<'a:live','home'>([['a:live','home']]);
  const destinations=classifyReturnArrivals(arrivals,arrivalWs,new Set(['a:response']),arrivalOwners);
  check('retorno em espera promove seu painel',destinations.promoteHome.length===1&&destinations.promoteHome[0].id==='waiting');
  check('retorno de pin fechado reabre',destinations.reopenPins.some(p=>p.id==='closed'));
  check('retorno de pin sem quadro montado revela',destinations.reopenPins.some(p=>p.id==='unmounted'));
  check('retorno do pin visível mantém instância',destinations.kept.length===1&&destinations.kept[0].id==='live');
  check('retorno já em Respostas atualiza ali',destinations.responses.some(p=>p.id==='response'));
  check('retorno novo segue para Respostas',destinations.responses.some(p=>p.id==='fresh'));
  check('nenhuma chegada excluída sem destino',destinations.responses.length+destinations.promoteHome.length+destinations.reopenPins.length+destinations.kept.length===arrivals.length);
  check('classificação não altera pin nem fonte',isPinClosed(arrivalWs,'a','closed')&&arrivalWs.homePanels!.at(-1)===waitingReport);
  const hiddenHome={...base,view:'project' as const,homePanels:[R]};
  check('retorno revela relatório da home oculta',classifyReturnArrivals([{project_id:'a',id:'f1'}],hiddenHome,new Set(),new Map()).promoteHome.length===1);
  check('catálogo home oculta mostra no primeiro clique',catalogState(hiddenHome,new Set(),new Set(),R)==='stored');
  check('catálogo Respostas recolhidas mostra primeiro',catalogState({...base,responsesCollapsed:true},owners,new Set(),R)==='stored');
  check('catálogo Respostas visíveis fecha',catalogState({...base,responsesCollapsed:false},owners,new Set(),R)==='visible');
  check('catálogo pin escondido mostra primeiro',catalogState(arrivalWs,new Set(),new Set(),{kind:'report',project_id:'a',ref:'unmounted'})==='stored');
  check('catálogo pin visível fecha',catalogState(arrivalWs,new Set(),new Set(['a:live']),{kind:'report',project_id:'a',ref:'live'})==='visible');
  check('catálogo pin fechado abre',catalogState(arrivalWs,new Set(),new Set(),{kind:'report',project_id:'a',ref:'closed'})==='closed');
  const deduped=dedupeReports({...base,homePanels:[A,R],layouts:{[desk]:[{i:R.key,x:0,y:0,w:6,h:9}]}},owners);
  check('duplicata vai para Respostas',deduped.moved===1&&!deduped.ws.homePanels!.some(p=>p.key===R.key)&&!!row(deduped.ws.layouts[desk],R.key));
  check('render nunca monta o mesmo relatório duas vezes',splitRendered([A,R],owners).shown.every(p=>p.key!==R.key)&&splitRendered([A,R],owners).elsewhere.length===1);
  check('alternância vê o dono em Respostas',openOwner([R],owners,{kind:'report',project_id:'a',ref:'f1'})==='responses'&&openOwner([R],new Set<string>(),{kind:'report',project_id:'a',ref:'f1'})==='home'&&openOwner([],new Set<string>(),{kind:'project',project_id:'a'})===null);

  // Fixados: o quadro da home é o dono persistente; o principal só sem a home; outro destino deixa o fixado estático.
  const pins=[{project_id:'a',id:'f1'},{project_id:'a',id:'f2'},{project_id:'a',id:'f3'},{project_id:'b',id:'f4'},{project_id:'c',id:'f5'},{id:'sem-projeto'}];
  const PA=panel('project','a'),RF3=panel('report','a','f3');
  const hosts=pinOwners(pins,[PA,RF3],new Set(['a:f2']),new Set(['a']),new Set(['a','b']));
  check('fixado no quadro da home vence o principal',hosts.get('a:f1')==='home');
  check('fixado aberto em Respostas não tem editor fixado',!hosts.has('a:f2'));
  check('fixado com painel de relatório na home fica estático',!hosts.has('a:f3'));
  check('fixado só no quadro principal',hosts.get('b:f4')==='main');
  check('fixado sem quadro montado não tem dono',!hosts.has('c:f5')&&hosts.size===2);
  // A decisão não depende da visão: mesmo conjunto de quadros da home com ou sem o principal dá o mesmo dono.
  check('dono do fixado independe do quadro principal',pinOwners(pins,[PA],new Set<string>(),new Set(['a']),new Set<string>()).get('a:f1')==='home');

  // Esteira: um editor por projeto; módulo Processo > quadro do projeto > pedido; painel sem conteúdo não é dono.
  const MP=panel('module','a','process'),MR=panel('module','a','results'),J1=panel('process','a','j1'),J2=panel('process','b','j3'),PB=panel('project','b');
  const owners1=routingOwners([J1,PA,MR,MP,J2,PB],()=>true);
  check('módulo Processo é o dono da esteira',owners1.get('a')===MP.key);
  check('quadro do projeto antes do pedido',owners1.get('b')===PB.key);
  check('sem pronto, próximo da fila',routingOwners([J1,PA,MP],p=>p.key!==MP.key&&p.key!==PA.key).get('a')===J1.key);
  check('sem painel na home, sem dono (quadro principal edita)',!routingOwners([MR],()=>true).has('a'));

  // Quadro do projeto: gravar substitui só as chaves exibidas; ocultos e fixados retirados guardam a posição.
  const boardSaved:LayoutItem[]=[{i:'now',x:0,y:0,w:4,h:4},{i:'process',x:4,y:8,w:8,h:6},{i:'report:f1',x:0,y:12,w:6,h:5}];
  const boardNext=replaceLayoutItems(boardSaved,[{i:'now',x:4,y:0,w:8,h:5,minW:3,maxW:12} as LayoutItem]);
  check('quadro: oculto mantém geometria',geom(row(boardNext,'process'))==='4,8,8,6'&&geom(row(boardNext,'report:f1'))==='0,12,6,5');
  check('quadro: exibido atualizado sem duplicar',geom(row(boardNext,'now'))==='4,0,8,5'&&boardNext.filter(a=>a.i==='now').length===1&&!('minW' in row(boardNext,'now')!));
  check('quadro: base ausente',replaceLayoutItems(undefined,[{i:'now',x:0,y:0,w:4,h:4}]).length===1);

  // Recentes pela data da entrega, não do projeto; sem data no fim; histórico fora.
  const projects=[project('velho','2020-01-01T00:00:00Z'),project('novo','2026-10-01T00:00:00Z')];
  const details={velho:detail('velho',[{id:'d1',title:'Entrega nova de projeto antigo',updated_at:'2026-10-12T10:00:00Z'},{id:'d2',title:'Sem data'},{id:'d3',title:'Histórica',updated_at:'2026-10-13T00:00:00Z',historical:true} as ProjectDetail['deliveries'][number]]),novo:detail('novo',[{id:'d4',title:'Mais antiga',updated_at:'2026-09-01T00:00:00Z'}])};
  const recent=recentDeliveries(projects,details,8);
  check('recente global pela data da entrega',recent[0]?.delivery.id==='d1'&&recent[1]?.delivery.id==='d4');
  check('sem data no fim',recent.at(-1)?.delivery.id==='d2'&&recent.at(-1)?.at===null);
  check('histórico excluído',!recent.some(r=>r.delivery.id==='d3'));
  check('em andamento primeiro',orderProjects(projects,new Set(['velho']))[0].id==='velho'&&orderProjects(projects,new Set())[0].id==='novo');
  const pinState={...base,views:[{id:'f1',project_id:'a',title:'Manual',url:'/api/files/f1',type:'html'}],layouts:{'a:flex:desk':boardSaved}};
  const hiddenPin=setPinClosed(pinState,'a','f1',true);
  check('catalogue close flag keeps manual pin',hiddenPin.views===pinState.views&&hiddenPin.views.length===1&&isPinClosed(hiddenPin,'a','f1'));
  check('catalogue close keeps original geometry',hiddenPin.layouts===pinState.layouts&&geom(row(hiddenPin.layouts['a:flex:desk'],'report:f1'))==='0,12,6,5');
  const revealed=setPinClosed(hiddenPin,'a','f1',false);
  check('ensure-open restores flag without unpin',!isPinClosed(revealed,'a','f1')&&revealed.views===pinState.views&&revealed.layouts===pinState.layouts);
  check('pin flags survive workspace reload',isPinClosed(reload(hiddenPin),'a','f1')&&!isPinClosed(reload(revealed),'a','f1'));
  check('independent pin flag preserved',isPinClosed(setPinClosed(hiddenPin,'b','f2',true),'a','f1'));
  check('invalid closed flag is not truthy',!isPinClosed({...base,closedPins:{'a:f1':'true'}},'a','f1'));

  // 261014 · seções da mesa (strip): migração idempotente, teto só para comuns, fechamento persistente, reabertura pelo catálogo.
  const stripsKey=(id:string)=>panelKey('strip',GLOBAL_PID,id);
  const fresh=normalizeHome({...base,homePanels:[A]});
  check('migração cria as três seções abertas',STRIP_MODULES.every(m=>fresh.ws.homePanels!.some(p=>p.key===stripsKey(m.id)&&p.kind==='strip'&&p.title===m.title)));
  check('migração marca a versão',fresh.ws.homeSectionsVersion===HOME_SECTIONS_VERSION);
  const freshAgain=normalizeHome(JSON.parse(JSON.stringify(fresh.ws)) as Workspace);
  check('normalização é idempotente',JSON.stringify(freshAgain.ws)===JSON.stringify(fresh.ws));
  const stripDesk=fresh.ws.layouts['home:desktop']!,stripMob=fresh.ws.layouts['home:mobile']!;
  check('estado novo: seções no topo do desktop',geom(row(stripDesk,stripsKey('projects')))==='0,0,12,6'&&geom(row(stripDesk,stripsKey('processes')))==='0,6,6,7'&&geom(row(stripDesk,stripsKey('recent')))==='6,6,6,8');
  check('mobile: seções empilhadas em uma coluna',[stripsKey('projects'),stripsKey('processes'),stripsKey('recent')].every(k=>row(stripMob,k)?.x===0&&row(stripMob,k)?.w===1));
  // Estado antigo com geometria salva: seções entram depois da última linha, sem deslocar nada salvo.
  const migrated=normalizeHome({...base,homePanels:[A],layouts:{[desk]:[{i:A.key,x:3,y:10,w:6,h:9}]}});
  check('estado antigo: seção depois dos painéis salvos',(row(migrated.ws.layouts[desk],stripsKey('projects'))?.y||0)>=19);
  check('estado antigo: geometria salva intacta',geom(row(migrated.ws.layouts[desk],A.key))==='3,10,6,9');
  // Fechar seção e recarregar: não reaparece (marca persistida); catálogo reabre com a geometria guardada.
  const stripPanel=migrated.ws.homePanels!.find(p=>p.key===stripsKey('projects'))!;
  const closed=reload(removePanel(migrated.ws,stripPanel.key,{layoutKey:desk,item:row(migrated.ws.layouts[desk],stripPanel.key)!}));
  check('seção fechada não reaparece na recarga',!closed.homePanels!.some(p=>p.key===stripPanel.key)&&closed.homeSectionsVersion===HOME_SECTIONS_VERSION);
  const stripBack=addPanel(closed,stripPanel).ws;
  check('reabrir seção recupera geometria',geom(row(stripBack.layouts[desk],stripPanel.key))===geom(row(migrated.ws.layouts[desk],stripPanel.key)));
  check('reabrir seção não expulsa comum',stripBack.homePanels!.some(p=>p.key===A.key)&&splitRendered(readOpen(stripBack)).shown.some(p=>p.key===stripPanel.key));
  // Teto: seções nunca ficam em espera nem ocupam vaga de painel comum.
  const strips3=STRIP_MODULES.map(m=>({key:stripsKey(m.id),kind:'strip' as const,project_id:GLOBAL_PID,ref:m.id,title:m.title}));
  const crowd20=Array.from({length:HOME_PANEL_LIMIT+8},(_,n)=>panel('project',`x${n}`));
  const withStrips=splitRendered([...strips3,...crowd20]);
  check('seções fora do teto de exibição',withStrips.shown.filter(p=>p.kind==='strip').length===3&&withStrips.shown.filter(p=>p.kind!=='strip').length===HOME_PANEL_LIMIT&&withStrips.waiting.length===8&&withStrips.waiting.every(p=>p.kind!=='strip'));
  check('catálogo vê seção fechada como fechada',catalogState(closed,new Set(),new Set(),{kind:'strip',project_id:GLOBAL_PID,ref:'projects'})==='closed');
  // Teclado no título: wider/narrow respeitam borda e largura mínima.
  const kb:LayoutItem[]=[{i:A.key,x:0,y:0,w:6,h:5,minW:3},{i:B.key,x:6,y:0,w:6,h:5,minW:3}];
  check('wider avança e cola na borda',geom(row(adjustLayout(kb,B.key,'wider',12),B.key))==='5,0,7,5');
  check('narrow respeita largura mínima',geom(row(adjustLayout(kb,B.key,'narrow',12),B.key))==='6,0,5,5'&&row(adjustLayout([{i:B.key,x:0,y:0,w:3,h:5}],B.key,'narrow',12),B.key)?.w===3);
  // Entrada forjada de seção: só os três identificadores reais, sempre com projeto fixo.
  check('seção fora da lista recusada',toPanelInput({kind:'strip',project_id:GLOBAL_PID,ref:'shell'})===null&&toPanelInput({kind:'strip',project_id:'a',ref:'projects'})===null);
  check('seção resolve sem projeto no catálogo',resolvePanel({kind:'strip',project_id:GLOBAL_PID,ref:'recent'},{projects:[],jobs:[],reports:()=>null})?.key===stripsKey('recent'));
  return failures;
}
function readOpen(ws:Workspace){return ws.homePanels||[];}
