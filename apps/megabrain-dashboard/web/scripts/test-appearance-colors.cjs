const fs=require('node:fs'),ts=require('typescript'),assert=require('node:assert/strict'),{test}=require('node:test');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,f);
const {appearanceFor,colorRows,inheritedLook,presentProject,projectAppearanceKey,readAppearance,setAppearance,setColor,typeAppearanceKey,validColor}=require('../src/appearance-state.ts');

const base={openProjects:[],activeProject:null,compareProject:null,layouts:{},hiddenModules:{},density:'comfortable',longPressMs:1000,views:[]};
// Simula salvar no /workspace e ler de novo (o servidor guarda o JSON como veio).
const reload=ws=>JSON.parse(JSON.stringify(ws));

test('qualquer cor #rrggbb é aceita e normalizada; o resto é descartado',()=>{
  assert.equal(validColor('#12AB9f'),'#12ab9f');
  for(const bad of ['red','#12ab9','#12ab9ff','url(x)','#ggg000',null,42])assert.equal(validColor(bad),undefined);
  const ws=setAppearance(base,'module:p:now',{color:'#12AB9F'});
  assert.equal(readAppearance(ws,'module:p:now').color,'#12ab9f');
  assert.deepEqual(readAppearance({...base,appearance:{k:{color:'javascript:alert(1)'}}},'k'),{});
});

test('cor por tipo vale para o mesmo tipo em todos os projetos; a cor própria do quadro manda',()=>{
  let ws=setColor(base,typeAppearanceKey('now'),'#00ff88');
  assert.equal(appearanceFor(ws,'module:a:now','Agora').color,'#00ff88');
  assert.equal(appearanceFor(ws,'module:b:now','Agora','#c7a0ff').color,'#00ff88');
  assert.equal(appearanceFor(ws,'module:a:results','Resultados').color,'#b2e58a');
  ws=setColor(ws,'module:b:now','#ff0000');
  assert.equal(appearanceFor(ws,'module:b:now','Agora').color,'#ff0000');
  // Projeto e relatório não herdam a cor do tipo.
  assert.equal(appearanceFor(ws,projectAppearanceKey('a'),'A','#c7a0ff').color,'#c7a0ff');
  assert.equal(appearanceFor(ws,'report:a:x','R','#c7a0ff').color,'#c7a0ff');
});

test('trocar a cor preserva nome e emoji; voltar ao padrão só remove a cor',()=>{
  let ws=setAppearance(base,projectAppearanceKey('b'),{emoji:'💡',name:'Bolha'});
  ws=setColor(ws,projectAppearanceKey('b'),'#8bc8ff');
  assert.deepEqual(readAppearance(ws,projectAppearanceKey('b')),{name:'Bolha',emoji:'💡',color:'#8bc8ff'});
  ws=setColor(ws,projectAppearanceKey('b'),null);
  assert.deepEqual(readAppearance(ws,projectAppearanceKey('b')),{name:'Bolha',emoji:'💡'});
  const solo=setColor(setColor(base,'module:a:now','#123456'),'module:a:now',null);
  assert.equal(Object.prototype.hasOwnProperty.call(solo.appearance,'module:a:now'),false);
});

test('cores e posições sobrevivem a salvar e reabrir, sem uma mexer na outra',()=>{
  const layouts={'home:desktop':[{i:'project:a:',x:0,y:0,w:12,h:20}],'a:flex:desk':[{i:'now',x:2,y:0,w:4,h:4}]};
  let ws={...base,layouts};
  ws=setColor(ws,projectAppearanceKey('a'),'#efc987');ws=setColor(ws,typeAppearanceKey('references'),'#336699');
  const back=reload(ws);
  assert.deepEqual(back.layouts,layouts);
  assert.equal(appearanceFor(back,projectAppearanceKey('a'),'A','#c7a0ff').color,'#efc987');
  assert.equal(appearanceFor(back,'module:z:references','Referências').color,'#336699');
});

test('menu lista primeiro os projetos da mesa e abertos, depois os demais em ordem; quadros da mesa sem os de projeto',()=>{
  const raw=[{id:'a',name:'Zeta',color:'#c7a0ff'},{id:'b',name:'Bubble',color:'#c7a0ff'},{id:'c',name:'Alfa',color:'#c7a0ff'},{id:'d',name:'Beta',color:'#c7a0ff'}];
  let ws={...base,openProjects:['c'],homePanels:[{key:'project:b:',kind:'project',project_id:'b',title:'Bubble'},{key:'module:b:now',kind:'module',project_id:'b',ref:'now',title:'Agora'}]};
  ws=setAppearance(ws,projectAppearanceKey('b'),{emoji:'💡',color:'#8bc8ff'});
  const projects=raw.map(p=>presentProject(ws,p));
  const rows=colorRows(ws,projects);
  assert.deepEqual(rows.featured.map(r=>r.label),['💡 Bubble','Alfa']);
  assert.deepEqual(rows.others.map(r=>r.label),['Beta','Zeta']);
  assert.equal(rows.featured[0].color,'#8bc8ff');assert.equal(rows.featured[0].own,true);
  assert.deepEqual(rows.desk.map(r=>[r.key,r.color,r.hint]),[['module:b:now','#8bc8ff','Módulo · Bubble']]);
  assert.equal(rows.types.length,6);assert.equal(rows.types.find(r=>r.key==='type:now').color,'#ff82c4');
});

test('relatório fixado dentro do quadro não herda cor de tipo, mesmo com id igual a um tipo',()=>{
  const ws=setColor(setColor(base,typeAppearanceKey('now'),'#00ff88'),typeAppearanceKey('x1'),'#111111');
  assert.equal(appearanceFor(ws,'module:a:report:x1','R').color,appearanceFor(base,'module:a:report:x1','R').color);
  assert.equal(appearanceFor(ws,'module:a:report:now','R').color,appearanceFor(base,'module:a:report:now','R').color);
});

test('o diálogo de um quadro mostra como padrão a cor herdada do tipo, não a paleta fixa',()=>{
  let ws=setColor(base,typeAppearanceKey('now'),'#00ff88');
  assert.equal(inheritedLook(ws,'module:a:now','Agora').color,'#00ff88');
  ws=setColor(ws,'module:a:now','#ff0000');
  assert.equal(inheritedLook(ws,'module:a:now','Agora').color,'#00ff88');
  assert.equal(appearanceFor(ws,'module:a:now','Agora').color,'#ff0000');
});

test('menu usa só os quadros visíveis e marca padrão quando o tipo não tem escolha',()=>{
  const ws={...base,homePanels:[{key:'module:b:now',kind:'module',project_id:'b',ref:'now',title:'Agora'},{key:'report:b:r1',kind:'report',project_id:'b',ref:'r1',title:'R1'}]};
  const rows=colorRows(ws,[{id:'b',name:'Bubble',color:'#8bc8ff'}],[ws.homePanels[0]]);
  assert.deepEqual(rows.desk.map(r=>r.key),['module:b:now']);
  assert.equal(rows.types.find(r=>r.key==='type:now').hint,'Padrão');
  assert.equal(colorRows(setColor(ws,'type:now','#123456'),[]).types.find(r=>r.key==='type:now').hint,undefined);
});
