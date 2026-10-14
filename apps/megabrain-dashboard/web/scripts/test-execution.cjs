const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {test} = require('node:test');
const ts = require('typescript');
for (const ext of ['.ts', '.tsx']) require.extensions[ext] = function(module, filename) {
  const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {compilerOptions: {
    jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022, esModuleInterop: true,
  }});
  module._compile(compiled.outputText, filename);
};
global.window = {location: {origin: 'http://127.0.0.1:8766'}};
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const Card = require(path.join(__dirname, '../src/Execution.tsx')).default;
const {artifactPreview, filePreview, presentedArtifacts, presentedSteps} = require(path.join(__dirname, '../src/executionState.ts'));
const {previewSandbox} = require(path.join(__dirname, '../src/api.ts'));
const planned = Array.from({length: 7}, (_, i) => ({id: `etapa-${i+1}`, title: `Etapa ${i+1}`, enabled: true, role: 'creator', model: 'codex', effort: 'xhigh', instruction: ''}));
const base = {id:'job', project_id:'project', title:'Pedido', status:'running', route:{stages:planned}};
const render = extra => renderToStaticMarkup(React.createElement(Card, {job:{...base, ...extra}, onPreview:()=>{}, onCancel:async()=>{}}));

test('uma etapa concluida de sete previstas nao aparece como 1 de 1', () => {
  const html = render({steps:[{id:'1-etapa-1', title:'Etapa 1', status:'completed'}]});
  assert.match(html, /1 de 7 etapas/);
  assert.match(html, /Etapa 7/);
});
test('busca nao e pagina aberta', () => {
  const html = render({sources:[{title:'Busca', url:'https://example.com', retrieved:true, retrieval_kind:'search_result'}]});
  assert.match(html, /Resultado de busca · página não aberta/);
  assert.doesNotMatch(html, /Consulta registrada/);
  assert.doesNotMatch(html, /1 página aberta/);
});
test('interrupcao nao deixa etapa girando e futuro aguardando', () => {
  const html = render({status:'interrupted', steps:[{id:'1-etapa-1', title:'Etapa 1', status:'running'}]});
  assert.doesNotMatch(html, /class="[^"]*spin/);
  assert.match(html, /Etapa interrompida/);
  assert.match(html, /Não executada/);
});
test('correcao adicional aumenta o total sem apagar etapas futuras', () => {
  const steps=presentedSteps({...base, steps:[
    {id:'1-etapa-1',title:'Etapa 1',status:'completed'},
    {id:'2-corrigir',title:'Corrigir',status:'running'},
  ]});
  assert.equal(steps.length,8);
  assert.equal(steps.filter(s=>s.status==='pending').length,6);
});
test('arquivo usa previa registrada em vez do endereco de download', () => {
  const url='/api/jobs/abc/artifacts/def';
  const preview=filePreview({path:'script.py',url},[{id:'def',title:'script.py',type:'text',url,preview_url:'/api/jobs/abc/view/def'}]);
  assert.equal(preview.url,'http://127.0.0.1:8766/api/jobs/abc/view/def');
  assert.equal(preview.title,'script.py');
  assert.equal(artifactPreview({title:'Sem prévia',url}),null);
});
test('mudanca de originais nao recebe garantia incondicional', () => {
  const html=render({status:'partial',files:[{path:'script.py',action:'modified'}],verification:{status:'failed',summary:'Os originais mudaram durante o pedido.'}});
  assert.doesNotMatch(html,/Os arquivos originais do projeto são preservados/);
  assert.match(html,/Os originais mudaram durante o pedido/);
});
test('pagina realmente aberta e busca permanecem separadas', () => {
  const html=render({sources:[
    {title:'Página',url:'https://example.com/page',retrieved:true,retrieval_kind:'page_fetch'},
    {title:'Busca',url:'https://example.com/search-result',retrieved:true,retrieval_kind:'search_result'},
  ]});
  assert.match(html,/1 página aberta/);
  assert.match(html,/1 resultado de busca/);
});
test('resultados visuais precedem fontes, codigo e markdown sem cards duplicados',()=>{
  const artifacts=[
    {id:'md',title:'pesquisa.md',type:'text',path:'workspace/pesquisa.md',url:'/api/jobs/a/artifacts/md'},
    {id:'report',title:'Pesquisa e conclusões',type:'html',origin:'research',path:'artifacts/pesquisa.html',url:'/api/jobs/a/artifacts/report'},
    {id:'code',title:'main.js',type:'text',url:'/api/jobs/a/artifacts/code'},
    {id:'app',title:'index.html',type:'html',path:'workspace/index.html',url:'/api/jobs/a/artifacts/app'},
  ];
  const parts=presentedArtifacts({...base,artifacts,files:artifacts.map(a=>({path:a.title,url:a.url}))});
  assert.deepEqual(parts.results.map(a=>a.id),['app','report']);
  assert.deepEqual(parts.files.map(f=>f.path),['pesquisa.md','main.js']);
  const html=render({artifacts});
  const section=html.match(/<section class="execution-artifacts">(.*?)<\/section>/s)[1];
  assert.doesNotMatch(section,/pesquisa\.md|main\.js/);
  assert.ok(section.indexOf('index.html')<section.indexOf('Pesquisa e conclusões'));
  assert.match(html,/<details class="execution-section"><summary>.*?Arquivos do pedido/s);
});
test('arquivo tecnico sem job.files permanece acessivel uma vez',()=>{
  const artifact={title:'test_main.py',type:'text',url:'/api/jobs/a/artifacts/tests',preview_url:'/api/jobs/a/view/tests'};
  const parts=presentedArtifacts({...base,artifacts:[artifact]});
  assert.equal(parts.results.length,0);
  assert.equal(parts.files.length,1);
  assert.equal(filePreview(parts.files[0],[artifact]).url,'http://127.0.0.1:8766/api/jobs/a/view/tests');
});
test('entrada html preservada nao se apresenta como resultado novo',()=>{
  const parts=presentedArtifacts({...base,artifacts:[{title:'Entrada preservada: antes.html',type:'html',origin:'input_snapshot',url:'/api/jobs/a/artifacts/input'}]});
  assert.equal(parts.results.length,0);
  assert.equal(parts.files[0].action,'unchanged');
});
test('formularios locais permitidos somente no wrapper de previa autenticada da mesma origem',()=>{
  const preview='/api/jobs/bad8e714597841a981be0466a624c54e/preview/0123456789abcdef01234567';
  const allowed='allow-scripts allow-same-origin allow-forms';
  assert.equal(previewSandbox(preview),allowed);
  assert.equal(previewSandbox('http://127.0.0.1:8766'+preview),allowed);
  for(const rejected of [
    preview.replace('/preview/','/render/'),
    preview.replace('/preview/','/view/'),
    preview.replace('/preview/','/artifacts/'),
    '/api/files/legacy-html',
    'https://example.com'+preview,
    'http://127.0.0.1:8767'+preview,
    'http://user:pass@127.0.0.1:8766'+preview,
    preview+'?download=1',preview+'#anchor',preview+'/',preview+'/child',
    '/elsewhere'+preview,
    preview.replace('/preview/','/preview%2f'),
    'javascript:alert(1)','data:text/html,<form></form>',
  ])assert.equal(previewSandbox(rejected),'',rejected);
  assert.doesNotMatch(allowed,/allow-top-navigation|allow-popups|allow-downloads/);
});

test('HTML catalogado local mantém recursos autenticados e scripts bloqueados',()=>{
 const route='/api/files/0f976d1a1699f547f33c';const allowed=previewSandbox(route);assert.equal(allowed,'allow-same-origin');assert.doesNotMatch(allowed,/allow-scripts|allow-forms|allow-top-navigation|allow-popups|allow-downloads/);
 for(const rejected of ['https://example.com'+route,'http://127.0.0.1:8767'+route,route+'?x=1',route+'#x',route+'/child'])assert.equal(previewSandbox(rejected),'');
});
