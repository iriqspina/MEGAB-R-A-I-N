const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {test} = require('node:test');
const ts = require('typescript');
require.extensions['.ts'] = function(module, filename) {
  const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022}});
  module._compile(compiled.outputText, filename);
};
const nav = require(path.join(__dirname, '../src/navigation.ts'));

// B-APP F0d · resolvedor de destino (PLANO_FINAL §3.5). Estado sintético; nenhuma tela é tocada.
const state = (loaded = {}) => ({
  projectIds: new Set(['p1', 'p2']),
  jobIds: new Set(['j1']),
  loadedItems: pid => (pid in loaded ? new Set(loaded[pid]) : null),
});
const report = (projectId, itemId, intent = 'user_action') => ({intent, target: {kind: 'report', projectId, itemId}});

test('chegada passiva nunca navega, nem para relatório conhecido (D07)', () => {
  assert.deepEqual(nav.resolveTarget(report('p1', 'f1', 'passive_arrival'), state({p1: ['f1']})), {type: 'none', reason: 'passive_arrival'});
  assert.deepEqual(nav.resolveTarget(nav.fromReturnArrival('p1', 'f1', 'h1'), state()), {type: 'none', reason: 'passive_arrival'});
});

test('repetir o mesmo alvo devolve a mesma abertura; nenhuma ação fecha (D05)', () => {
  const first = nav.resolveTarget(report('p1', 'f1'), state({p1: ['f1']}));
  const again = nav.resolveTarget(report('p1', 'f1'), state({p1: ['f1']}));
  assert.deepEqual(first, {type: 'open-item', projectId: 'p1', itemId: 'f1', needsDetail: false});
  assert.deepEqual(again, first);
  for (const kind of ['project', 'report', 'delivery', 'file', 'reference', 'link', 'job', 'comment', 'correction', 'session', 'quota'])
    assert.ok(!/close|toggle/.test(nav.resolveTarget({intent: 'user_action', target: {kind, projectId: 'p1', itemId: 'j1'}}, state()).type), kind);
});

test('homônimo em projetos distintos resolve pelo projeto do alvo', () => {
  const s = state({p1: ['mesmo-id'], p2: ['mesmo-id']});
  assert.equal(nav.resolveTarget(report('p2', 'mesmo-id'), s).projectId, 'p2');
  assert.equal(nav.resolveTarget(report('p1', 'mesmo-id'), s).projectId, 'p1');
});

test('item fora do catálogo carregado pede o detalhe em vez de sumir', () => {
  assert.equal(nav.resolveTarget(report('p1', 'f9'), state({p1: ['f1']})).needsDetail, true);
  assert.equal(nav.resolveTarget(report('p1', 'f1'), state()).needsDetail, true, 'projeto sem detalhe carregado');
});

test('projeto desconhecido e pedido fora da lista viram falha conhecida com o vínculo preservado', () => {
  const lost = {intent: 'user_action', target: {kind: 'report', projectId: 'p9', itemId: 'f1', title: 'Antigo'}};
  const out = nav.resolveTarget(lost, state());
  assert.equal(out.type, 'known-failure');
  assert.equal(out.retry, true);
  assert.deepEqual(out.target, lost.target);
  assert.match(out.message, /"Antigo"/);
});

test('pedido carregado abre; pedido fora da lista leva à Atividade sem prometer nova tentativa', () => {
  assert.deepEqual(nav.resolveTarget({intent: 'user_action', target: {kind: 'job', projectId: 'p1', itemId: 'j1'}}, state()), {type: 'open-job', projectId: 'p1', jobId: 'j1'});
  const old = nav.resolveTarget({intent: 'user_action', target: {kind: 'job', projectId: 'p1', itemId: 'j-velho', projectName: 'MegaBrain'}}, state());
  assert.equal(old.type, 'open-section');
  assert.equal(old.section, 'activity');
  assert.doesNotMatch(old.notice, /tente de novo/i);
});

test('conteúdo de projeto sem projeto não abre nada; cotas não precisam de projeto', () => {
  const out = nav.resolveTarget({intent: 'user_action', target: {kind: 'report', itemId: 'f1'}}, state());
  assert.equal(out.type, 'known-failure');
  assert.equal(out.retry, false);
  assert.deepEqual(nav.resolveTarget({intent: 'user_action', target: {kind: 'quota'}}, state()), {type: 'open-quotas'});
});

test('tipos sem leitor próprio vão à seção do projeto com aviso de onde está', () => {
  const out = nav.resolveTarget({intent: 'user_action', target: {kind: 'comment', projectId: 'p2', itemId: 'c1', title: 'Nota', projectName: 'Bubble'}}, state());
  assert.deepEqual(out, {type: 'open-section', projectId: 'p2', section: 'now', notice: 'Comentário "Nota" está em Bubble.'});
  assert.equal(nav.resolveTarget({intent: 'user_action', target: {kind: 'delivery', projectId: 'p2', itemId: 'd1'}}, state()).section, 'results');
});

test('catálogo: módulo mantém a seção e painel global não vira projeto falso', () => {
  const mod = nav.fromCatalog({kind: 'module', project_id: 'p1', ref: 'references'});
  assert.deepEqual(nav.resolveTarget(mod, state()), {type: 'open-project', projectId: 'p1', module: 'references'});
  const sessions = nav.fromCatalog({kind: 'global', project_id: '__global__', ref: 'sessions'});
  assert.deepEqual(nav.resolveTarget(sessions, state()), {type: 'open-global', panel: 'sessions'});
  const semProjeto = nav.resolveTarget({intent: 'user_action', target: {kind: 'project'}}, state());
  assert.equal(semProjeto.type, 'known-failure');
});

test('apresentação e chegada preservam projeto, arquivo e versão', () => {
  assert.deepEqual(nav.fromPresentation('p1', 'f1', 'h1').target, {kind: 'report', projectId: 'p1', itemId: 'f1', versionHash: 'h1', source: 'presentation'});
  assert.deepEqual(nav.fromReturnArrival('p2', 'f2', 'h2'), {intent: 'passive_arrival', target: {kind: 'report', projectId: 'p2', itemId: 'f2', versionHash: 'h2', source: 'return'}});
});

test('adaptadores traduzem as entradas atuais sem perder projeto, item e intenção', () => {
  assert.deepEqual(nav.fromCatalog({kind: 'global', project_id: '__global__', ref: 'quotas'}).target.kind, 'quota');
  assert.deepEqual(nav.fromCatalog({kind: 'process', project_id: 'p1', ref: 'j1'}).target, {kind: 'job', projectId: 'p1', itemId: 'j1', source: 'catalog'});
  assert.equal(nav.fromPresentation('p1', 'f1', 'h').intent, 'explicit_presentation');
  assert.equal(nav.resolveTarget(nav.fromPresentation('p1', 'f1', 'h'), state({p1: ['f1']})).type, 'open-item');
  const located = nav.fromLocator({kind: 'link', project_id: 'p1', project_name: 'MegaBrain', title: 'Site', target: {kind: 'link', projectId: 'p1', itemId: 'r1'}});
  assert.deepEqual(located, {intent: 'user_action', target: {kind: 'link', projectId: 'p1', itemId: 'r1', source: 'locator', title: 'Site', projectName: 'MegaBrain'}});
  assert.deepEqual(nav.resolveTarget(nav.fromHomeCard('p2'), state()), {type: 'open-project', projectId: 'p2'});
});
