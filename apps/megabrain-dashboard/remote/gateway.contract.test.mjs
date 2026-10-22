// Route contract between the backend, the frontend and the remote gateway (261020).
// The gateway list froze on 261011 while the app grew: reports, returns and quotas
// answered 404 remotely and the old tests stayed green. Here every route the backend
// declares (read from the FastAPI decorators by AST, not copied from the gateway)
// needs an explicit decision, and the gateway is exercised against that decision.
import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { readFileSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import gateway from './gateway.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const APP = dirname(HERE);
const SERVER = join(APP, 'central_server.py');
const PUBLIC_ORIGIN = 'https://gateway.example.test';
const SECRET = 'c'.repeat(64); // Test fixture only.
const METHODS = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE'];

// remote: forwarded to the fixed loopback upstream. local: refused by the gateway with
// 403 local_only and a readable message. static: SPA catch-all, only the shell assets.
// `ui` explains how the interface behaves remotely when the frontend calls a local route.
const DECISIONS = {
  'GET /api/projects/{pid}/control': ['remote', 'Consultar espera ou pausa do projeto.'],
  'PUT /api/projects/{pid}/control': ['remote', 'Alterar espera/pausa por acao explicita, CSRF e revision.'],
  'GET /api/health': ['remote', 'Saúde pública genérica.'],
  'POST /api/pair': ['remote', 'Pareamento por código no corpo JSON.'],
  'GET /api/session': ['remote', 'Sessão e CSRF do aparelho.'],
  'POST /api/logout': ['remote', 'Revoga a sessão do aparelho.'],
  'GET /api/projects': ['remote', 'Catálogo de projetos.'],
  'GET /api/search': ['remote', 'Localizador: busca o índice de metadados de todos os projetos.'],
  'GET /api/session-connections': ['remote', 'Sessões conectadas; o backend já serve sessões remotas.'],
  'GET /api/projects/{pid}': ['remote', 'Detalhe do projeto.'],
  'POST /api/projects/{pid}/attachments': ['remote', 'Print do celular; limite próprio do contrato de upload.'],
  'GET /api/projects/{pid}/attachments/{aid}': ['remote', 'Prévia do print anexado, confinada ao projeto.'],
  'GET /api/workspace': ['remote', 'Mesa salva.'],
  'GET /api/returns': ['remote', 'Resultados e retornos globais.'],
  'PUT /api/workspace': ['remote', 'Salvar a mesa.'],
  'GET /api/projects/{pid}/process': ['remote', 'Processo do projeto.'],
  'PUT /api/projects/{pid}/process': ['remote', 'Editar processo.'],
  'GET /api/projects/{pid}/routing': ['remote', 'Esteiras.'],
  'PUT /api/projects/{pid}/routing': ['remote', 'Editar esteiras.'],
  'POST /api/projects/{pid}/route-preview': ['remote', 'Prévia inerte de rota.'],
  'GET /api/projects/{pid}/code-files': ['remote', 'Lista de arquivos para pedido.'],
  'POST /api/projects/{pid}/comments': ['remote', 'Comentário no projeto.'],
  // 261021 F0b: rota criada pelo trabalho interrompido "responder comentário" (não validado).
  // Fica só no computador até aquela frente decidir; liberar escrita remota é decisão dela.
  'POST /api/projects/{pid}/comments/{cid}/replies': ['local', 'Resposta a comentário: decisão remota pendente da frente que criou a rota.'],
  'POST /api/projects/{pid}/references': ['remote', 'Referência HTTPS.'],
  'GET /api/events': ['remote', 'Eventos incrementais.'],
  'GET /api/reports/{fid}/note-receipts': ['remote', 'Recibos das notas do relatório.'],
  'GET /api/reports/{fid}/status': ['remote', 'Versão do relatório antes de abrir.'],
  'GET /api/reports/{fid}/view': ['remote', 'Envelope autenticado do relatório.'],
  'GET /api/reports/{fid}/render': ['remote', 'Relatório isolado com recursos embutidos.'],
  'POST /api/reports/{fid}/draft': ['remote', 'Rascunho das notas.'],
  'POST /api/reports/{fid}/feedback': ['remote', 'Comentários e decisões do relatório.'],
  'GET /api/bridge/vendors': ['remote', 'IAs disponíveis para a ponte.'],
  'GET /api/projects/{pid}/bridge': ['remote', 'Configuração da ponte (leitura).'],
  'PUT /api/projects/{pid}/bridge': ['remote', 'Configurar a ponte; a IA executa no PC, como jobs.'],
  'POST /api/projects/{pid}/bridge/send': ['remote', 'Enviar correção pela ponte.'],
  'POST /api/projects/{pid}/bridge/orders/{oid}/stop': ['remote', 'Parar uma ordem da ponte.'],
  'POST /api/dispatch/{fid}': ['local', 'Abre um terminal Windows no computador.',
    'O relatório recebe a recusa e mostra "Não consegui abrir o terminal: <mensagem>".'],
  'POST /api/reports/{fid}/resolve': ['remote', 'Link local dentro do relatório, confinado ao projeto.'],
  'POST /api/present': ['local', 'Integração da janela nativa; recebe caminho absoluto.',
    'Só é chamado por evento da janela nativa do PC; não dispara no celular.'],
  'GET /api/report-audit': ['local', 'Diagnóstico com raízes absolutas; sem consumidor remoto.'],
  'GET /api/files/{fid}': ['remote', 'Arquivo indexado do catálogo.'],
  'GET /api/jobs': ['remote', 'Lista de pedidos.'],
  'POST /api/jobs/{jid}/cancel': ['remote', 'Interromper pedido.'],
  'GET /api/jobs/{jid}/artifacts/{aid}': ['remote', 'Baixar resultado.'],
  'GET /api/jobs/{jid}/view/{aid}': ['remote', 'Resultado em texto.'],
  'GET /api/jobs/{jid}/preview/{aid}': ['remote', 'Prévia isolada.'],
  'GET /api/jobs/{jid}/render/{aid}': ['remote', 'Interface isolada.'],
  'GET /api/jobs/{jid}/resources/{aid}': ['remote', 'CSS/JS da prévia isolada.'],
  'POST /api/projects/{pid}/jobs': ['remote', 'Criar pedido.'],
  'GET /api/guide': ['remote', 'Guia.'],
  'GET /api/connection': ['remote', 'Conectar outro aparelho.'],
  'GET /api/quotas': ['remote', 'Cotas; remoto recebe local_controls=false.'],
  'POST /api/quotas/open-widget': ['local', 'Abre o widget Windows.',
    'Botões do widget só aparecem com local_controls=true (App.tsx openQuotas, QuotasPanel).'],
  'GET /api/quotas/widget-settings': ['local', 'Configura o widget Windows.',
    'QuotaSettings só monta com local_controls=true (QuotasPanel).'],
  'POST /api/quotas/widget-settings': ['local', 'Configura o widget Windows.',
    'QuotaSettings só monta com local_controls=true (QuotasPanel).'],
  'GET /api/quotas/widget-settings/requests/{request_id}': ['local', 'Recibo da configuração do widget.',
    'QuotaSettings só monta com local_controls=true (QuotasPanel).'],
  'GET /api/connection/qr': ['remote', 'QR de pareamento autenticado.'],
  'GET /{path:path}': ['static', 'Shell do app em web/dist; nunca /api/*.'],
};

const SAMPLES = { pid: 'd'.repeat(20), fid: 'e'.repeat(20), jid: 'a'.repeat(32), oid: '261020-061500-abcdef', request_id: 'req-fixture-1234' };
function sample(template) {
  // Attachment ids are sha256; job artifact ids are 24 hex.
  const aid = template.startsWith('/api/jobs/') ? 'b'.repeat(24) : 'f'.repeat(64);
  return template.replace(/\{(\w+)(?::path)?\}/g, (_, name) => name === 'aid' ? aid : SAMPLES[name] ?? 'x');
}

const EXTRACT = String.raw`
import ast, json, sys
tree = ast.parse(sys.stdin.buffer.read().decode('utf-8'))
routes, unsupported = [], []
VERBS = {'get', 'post', 'put', 'delete', 'patch', 'head', 'options'}
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == 'app':
        attr = node.func.attr
        if attr in VERBS:
            arg = node.args[0] if node.args else next((k.value for k in node.keywords if k.arg == 'path'), None)
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                routes.append({'method': attr.upper(), 'path': arg.value, 'line': node.lineno})
            else:
                unsupported.append({'call': attr, 'line': node.lineno})
        elif attr in {'api_route', 'route', 'add_api_route', 'add_route', 'mount', 'include_router', 'websocket', 'add_websocket_route'}:
            unsupported.append({'call': attr, 'line': node.lineno})
print(json.dumps({'routes': routes, 'unsupported': unsupported}))
`;
function extractRoutes(source) {
  const python = process.env.MB_PYTHON || 'python';
  const run = spawnSync(python, ['-I', '-c', EXTRACT], { input: source, encoding: 'utf-8' });
  if (run.error || run.status !== 0) throw new Error(`Python indisponível para ler os decorators (${python}): ${run.error?.message || run.stderr}`);
  return JSON.parse(run.stdout);
}
function classificationDiff(extracted, decisions) {
  const declared = new Set(extracted.routes.map(r => `${r.method} ${r.path}`));
  return {
    unclassified: [...declared].filter(key => !decisions[key]),
    stale: Object.keys(decisions).filter(key => !declared.has(key)),
    unsupported: extracted.unsupported,
    invalid: Object.entries(decisions).filter(([, d]) => !['remote', 'local', 'static'].includes(d[0]) || !d[1]).map(([key]) => key),
  };
}

function fixture() {
  const calls = [];
  const env = { PUBLIC_ORIGIN, MB_REMOTE_ENABLED: 'true', MB_GATEWAY_SECRET: SECRET,
    MEGABRAIN_ORIGIN: { fetch: async (url, options) => { calls.push({ url, method: options.method }); return new Response('{}', { headers: { 'Content-Type': 'application/json' } }); } } };
  return { env, calls };
}
function request(method, path) {
  const write = !['GET', 'HEAD'].includes(method);
  return new Request(PUBLIC_ORIGIN + path, { method, ...(write ? { body: '{}', headers: { origin: PUBLIC_ORIGIN, 'content-type': 'application/json' } } : {}) });
}
async function forwardingFailures(proxy, decisions) {
  const failures = [];
  for (const [key, [decision]] of Object.entries(decisions)) {
    if (decision === 'static') continue;
    const [method, template] = key.split(' ');
    const path = sample(template);
    const { env, calls } = fixture();
    const response = await proxy.fetch(request(method, path), env);
    if (decision === 'remote') {
      const reached = calls.length === 1 && calls[0].url === 'http://127.0.0.1:8767' + path && calls[0].method === method;
      if (!reached) failures.push(`${key}: esperado encaminhar, recebeu ${response.status}`);
    } else {
      const body = await response.json().catch(() => ({}));
      if (response.status !== 403 || body.error !== 'local_only' || typeof body.message !== 'string' || body.message.length < 20 || calls.length)
        failures.push(`${key}: esperado 403 local_only com mensagem, recebeu ${response.status} ${body.error}`);
    }
  }
  return failures;
}

const SOURCE = readFileSync(SERVER, 'utf-8');

test('every backend route has exactly one explicit remote/local decision', () => {
  const extracted = extractRoutes(SOURCE);
  assert.ok(extracted.routes.length >= 50, 'extração por AST encontrou poucas rotas');
  assert.deepEqual(classificationDiff(extracted, DECISIONS), { unclassified: [], stale: [], unsupported: [], invalid: [] });
});

test('the contract check catches a new backend route and a stale entry', () => {
  const mutated = SOURCE.replace("    @app.get('/api/report-audit')", "    @app.get('/api/ficticia-261020')\n    def ficticia(): return {}\n    @app.get('/api/report-audit')")
    .replace("@app.get('/api/guide')", "@app.get('/api/guia-renomeado')");
  const diff = classificationDiff(extractRoutes(mutated), DECISIONS);
  assert.deepEqual(diff.unclassified.sort(), ['GET /api/ficticia-261020', 'GET /api/guia-renomeado']);
  assert.deepEqual(diff.stale, ['GET /api/guide']);
  const dynamic = classificationDiff(extractRoutes(SOURCE + "\napp.add_api_route('/api/x', lambda: 1)\n"), DECISIONS);
  assert.equal(dynamic.unsupported.length, 1);
});

test('remote routes reach the fixed upstream with the declared method; local ones get a readable 403', async () => {
  assert.deepEqual(await forwardingFailures(gateway, DECISIONS), []);
});

test('the forwarding check fails when a remote route disappears from the gateway list', async () => {
  const narrowed = { fetch: (req, env) => /\/api\/reports\/[a-f0-9]{20}\/status$/.test(new URL(req.url).pathname)
    ? new Response('{"error":"not_found"}', { status: 404 }) : gateway.fetch(req, env) };
  assert.deepEqual(await forwardingFailures(narrowed, DECISIONS), ['GET /api/reports/{fid}/status: esperado encaminhar, recebeu 404']);
});

// 261021 F0b: o localizador é leitura pura de metadados — nunca escrito por fora
// e sujeito ao mesmo filtro de query dos demais endpoints.
test('/api/search is readable remotely, read-only and keeps the query filter', async () => {
  const { env, calls } = fixture();
  const read = await gateway.fetch(request('GET', '/api/search?q=relatorio&scope=atuais&kind=report&limit=50'), env);
  assert.equal(read.status, 200);
  assert.deepEqual(calls, [{ url: 'http://127.0.0.1:8767/api/search?q=relatorio&scope=atuais&kind=report&limit=50', method: 'GET' }]);
  const write = await gateway.fetch(request('POST', '/api/search'), env);
  assert.equal(write.status, 404);
  const filtered = await gateway.fetch(request('GET', '/api/search?path=outro-lugar'), env);
  assert.equal(filtered.status, 400);
  assert.equal((await filtered.json()).error, 'invalid_query');
  assert.equal(calls.length, 1);
});

test('methods the backend does not declare are never forwarded', async () => {
  const byPath = new Map();
  for (const key of Object.keys(DECISIONS)) {
    const [method, template] = key.split(' ');
    if (template.includes(':path')) continue;
    byPath.set(template, new Set([...(byPath.get(template) || []), method]));
  }
  const leaks = [];
  for (const [template, declared] of byPath) {
    for (const method of METHODS) {
      if (declared.has(method) || (method === 'HEAD' && declared.has('GET'))) continue;
      const { env, calls } = fixture();
      await gateway.fetch(request(method, sample(template)), env);
      if (calls.length) leaks.push(`${method} ${template}`);
    }
  }
  assert.deepEqual(leaks, []);
});

test('the static catch-all serves only shell assets and never opens /api/*', async () => {
  const { env, calls } = fixture();
  for (const path of ['/', '/index.html', '/assets/index-hash.js', '/manifest.webmanifest', '/cursor-ferramentas-v1.2.js'])
    assert.equal((await gateway.fetch(request('GET', path), env)).status, 200, path);
  const forwarded = calls.length;
  for (const path of ['/api/unknown', '/api/admin', '/.env', '/data/.private/native.key', '/central_server.py', '/cursor-ferramentas.js', '/cursor-ferramentas-v1.2.js/../x'])
    assert.ok((await gateway.fetch(request('GET', path), env)).status >= 400, path);
  assert.equal(calls.length, forwarded);
});

// Complementary layer: what the interface actually calls must be a declared backend
// route, and if that route is local the decision must say how the UI behaves remotely.
function frontendCalls() {
  const dir = join(APP, 'web/src');
  const calls = [];
  for (const name of readdirSync(dir).filter(n => /\.(ts|tsx)$/.test(n) && !n.endsWith('.check.ts'))) {
    const text = readFileSync(join(dir, name), 'utf-8');
    for (const m of text.matchAll(/\bapi\s*(?:<[^()]*?>)?\(\s*([`'"])(\/[^`'"]*)\1\s*(?:,\s*'([A-Z]+)')?/g))
      calls.push({ file: name, method: m[3] || 'GET', path: '/api' + m[2] });
    for (const m of text.matchAll(/[`'"](\/(?:api\/[^`'"\s]*|cursor-ferramentas-[^`'"\s]*))[`'"]/g))
      if (!m[1].startsWith('/api/${')) calls.push({ file: name, method: 'GET', path: m[1], raw: true });
  }
  return calls.map(c => ({ ...c, path: c.path.replace(/\$\{[^}]*\}/g, '{x}').split('?')[0] }));
}
function templateFor(method, path) {
  return Object.keys(DECISIONS).find(key => {
    const [verb, template] = key.split(' ');
    if (verb !== method || template.includes(':path')) return false;
    const pattern = new RegExp('^' + template.replace(/\{\w+\}/g, '[^/]+') + '$');
    return pattern.test(path);
  });
}

test('every route the frontend calls is declared, decided and usable remotely or explained', async () => {
  const calls = frontendCalls();
  assert.ok(calls.length >= 40, 'varredura do frontend encontrou poucas chamadas');
  const problems = [];
  for (const call of calls) {
    if (call.path.startsWith('/cursor-ferramentas-')) {
      const { env, calls: upstream } = fixture();
      await gateway.fetch(request('GET', call.path), env);
      if (upstream.length !== 1) problems.push(`${call.file}: ${call.path} não passa pelo gateway`);
      continue;
    }
    const key = templateFor(call.method, call.path);
    if (!key) { problems.push(`${call.file}: ${call.method} ${call.path} sem rota no backend`); continue; }
    const [decision, , ui] = DECISIONS[key];
    if (decision === 'local' && !ui) problems.push(`${call.file}: ${key} é local e não diz como a interface reage no celular`);
  }
  assert.deepEqual(problems, []);
});
