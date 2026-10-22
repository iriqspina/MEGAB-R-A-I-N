// A single-destination proxy. The local application owns pairing, sessions and CSRF.
// No project data, cookies, request URLs or bodies are written to cloud storage/logs.
const MAX_BODY_BYTES = 350_000;
// Same contract as central_attachments.MAX_UPLOAD_BODY (one 8 MiB image in base64 plus
// the JSON envelope). Only the exact upload route gets it; every other write keeps 350 kB.
const MAX_UPLOAD_BYTES = 4 * Math.floor((8 * 1024 * 1024 + 2) / 3) + 8192;
const METHODS = new Set(['GET', 'HEAD', 'POST', 'PUT', 'DELETE']);
// Opaque ids issued by the backend: central_store.ident (project, file, report),
// sha256 of an attachment, and central_bridge order names.
const HEX20 = '[a-f0-9]{20}';
const HEX64 = '[a-f0-9]{64}';
const ORDER = '\\d{6}-\\d{6}-[a-f0-9]{6}';
const UPLOAD = new RegExp(`^/api/projects/${HEX20}/attachments$`);
const REPORT_READ = new RegExp(`^/api/reports/${HEX20}/(status|view|render|note-receipts)$`);
const REPORT_WRITE = new RegExp(`^/api/reports/${HEX20}/(draft|feedback|resolve)$`);
const PROJECT_READ = new RegExp(`^/api/projects/${HEX20}/(attachments/${HEX64}|bridge|control)$`);
const BRIDGE_CONFIG = new RegExp(`^/api/projects/${HEX20}/(?:bridge|control)$`);
const BRIDGE_ACTION = new RegExp(`^/api/projects/${HEX20}/bridge/(send|orders/${ORDER}/stop)$`);
// These open or configure something on the Windows computer itself. The phone gets a
// readable refusal instead of a silent 404; the backend is never contacted.
const LOCAL_ONLY = [
  ['POST', new RegExp(`^/api/dispatch/${HEX20}$`), 'O despacho abre um terminal neste computador. Use o MegaBrain no PC.'],
  ['POST', /^\/api\/present$/, 'Apresentar abre a janela do MegaBrain no computador. Use o MegaBrain no PC.'],
  ['GET', /^\/api\/report-audit$/, 'O diagnóstico de relatórios mostra as pastas do computador. Consulte no MegaBrain do PC.'],
  ['POST', /^\/api\/quotas\/open-widget$/, 'A janela do widget abre somente no aplicativo deste computador.'],
  ['GET', /^\/api\/quotas\/widget-settings$/, 'Configure o widget pelo MegaBrain deste computador.'],
  ['POST', /^\/api\/quotas\/widget-settings$/, 'Configure o widget pelo MegaBrain deste computador.'],
  ['GET', /^\/api\/quotas\/widget-settings\/requests\/[A-Za-z0-9_-]{1,100}$/, 'Consulte a aplicação pelo MegaBrain deste computador.'],
  // 261021: rota do trabalho interrompido "responder comentário"; remoto só depois da decisão daquela frente.
  ['POST', /^\/api\/projects\/[a-zA-Z0-9_-]+\/comments\/[a-zA-Z0-9_-]+\/replies$/, 'Responder a um comentário ainda funciona só no MegaBrain deste computador.'],
];
const FORWARDED_HEADERS = [
  'accept', 'accept-language', 'content-type', 'cookie', 'origin',
  'range', 'if-range', 'x-mb-csrf', 'idempotency-key',
];

function safeHeaders(headers = undefined) {
  const result = new Headers(headers);
  result.set('Cache-Control', 'no-store, private, max-age=0');
  result.set('CDN-Cache-Control', 'no-store');
  result.set('Cloudflare-CDN-Cache-Control', 'no-store');
  result.set('Pragma', 'no-cache');
  result.set('X-Content-Type-Options', 'nosniff');
  result.set('Referrer-Policy', 'no-referrer');
  result.set('X-Frame-Options', 'SAMEORIGIN');
  result.set('Strict-Transport-Security', 'max-age=31536000');
  result.delete('Access-Control-Allow-Origin');
  result.delete('Access-Control-Allow-Credentials');
  result.delete('Server');
  result.delete('X-Powered-By');
  return result;
}

function fail(status, code, message) {
  const headers = safeHeaders({ 'Content-Type': 'application/json; charset=utf-8' });
  if (status === 503) headers.set('Retry-After', '30');
  return new Response(JSON.stringify({ error: code, message }), { status, headers });
}

function configuredOrigin(value) {
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.username || url.password || url.pathname !== '/' || url.search || url.hash) return null;
    if (url.hostname.endsWith('.invalid')) return null;
    return url.origin;
  } catch { return null; }
}

function permittedRoute(path, method) {
  if (/%2f|%5c|%00|%2e/i.test(path) || path.includes('\\')) return false;
  const read = method === 'GET' || method === 'HEAD';
  if (read && (['/', '/index.html', '/manifest.webmanifest', '/manifest.json', '/sw.js', '/favicon.ico', '/brand.png', '/icon-192.png', '/icon-512.png'].includes(path) || /^\/(assets|icons)\/[a-zA-Z0-9_./-]+$/.test(path))) return true;
  // Comment tools of the app shell (web/public), loaded by CursorTools.tsx.
  if (read && /^\/cursor-ferramentas-v\d+(?:\.\d+)*\.js$/.test(path)) return true;
  if (read && /^\/api\/(health|session|search|projects|workspace|events|jobs|guide|connection)$/.test(path)) return true;
  // 261020: reads the app added after 261011; the backend serves them to remote sessions
  // (quotas reports local_controls=false there, so the widget buttons stay hidden).
  if (read && /^\/api\/(returns|session-connections|quotas|bridge\/vendors)$/.test(path)) return true;
  // Interactive reports: status, authenticated wrapper, isolated render, note receipts.
  if (read && (REPORT_READ.test(path) || PROJECT_READ.test(path))) return true;
  if (method === 'POST' && (REPORT_WRITE.test(path) || UPLOAD.test(path))) return true;
  // Correction bridge runs on the computer, like jobs and report feedback already do.
  if (method === 'PUT' && BRIDGE_CONFIG.test(path)) return true;
  if (method === 'POST' && BRIDGE_ACTION.test(path)) return true;
  if (read && path === '/api/connection/qr') return true;
  if (read && /^\/api\/(projects|files)\/[a-zA-Z0-9_-]+$/.test(path)) return true;
  if (read && /^\/api\/projects\/[a-zA-Z0-9_-]+\/(process|routing|code-files)$/.test(path)) return true;
  if (read && /^\/api\/jobs\/[a-f0-9]{32}\/(artifacts|preview|render|resources|view)\/[a-f0-9]{24}$/.test(path)) return true;
  if (method === 'POST' && /^\/api\/jobs\/[a-f0-9]{32}\/cancel$/.test(path)) return true;
  if (method === 'POST' && ['/api/pair', '/api/logout'].includes(path)) return true;
  if (method === 'PUT' && path === '/api/workspace') return true;
  if (method === 'PUT' && /^\/api\/projects\/[a-zA-Z0-9_-]+\/(process|routing)$/.test(path)) return true;
  return method === 'POST' && /^\/api\/projects\/[a-zA-Z0-9_-]+\/(comments|references|jobs|route-preview)$/.test(path);
}

function localOnly(path, method) {
  const verb = method === 'HEAD' ? 'GET' : method;
  return LOCAL_ONLY.find(([wanted, pattern]) => wanted === verb && pattern.test(path))?.[2] ?? null;
}

function bodyLimit(path, method) {
  return method === 'POST' && UPLOAD.test(path) ? MAX_UPLOAD_BYTES : MAX_BODY_BYTES;
}

async function boundedBody(request, limit) {
  const length = request.headers.get('content-length');
  if (length !== null && (!/^\d+$/.test(length) || Number(length) > limit)) throw new RangeError('body_limit');
  if (!request.body) return null;
  const reader = request.body.getReader();
  const chunks = [];
  let bytes = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > limit) { await reader.cancel(); throw new RangeError('body_limit'); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const body = new Uint8Array(bytes);
  let offset = 0;
  for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.byteLength; }
  return body;
}

export default {
  async fetch(request, env) {
    const publicOrigin = configuredOrigin(env.PUBLIC_ORIGIN);
    if (env.MB_REMOTE_ENABLED !== 'true' || !publicOrigin || !/^[a-f0-9]{64}$/.test(env.MB_GATEWAY_SECRET ?? '') || !env.MEGABRAIN_ORIGIN?.fetch) {
      return fail(503, 'remote_unavailable', 'A conexão remota ainda não está disponível.');
    }
    const incoming = new URL(request.url);
    if (incoming.origin !== publicOrigin) return fail(421, 'invalid_host', 'Endereço não permitido.');
    if (!METHODS.has(request.method)) return fail(405, 'method_not_allowed', 'Método não permitido.');
    const local = localOnly(incoming.pathname, request.method);
    if (local) return fail(403, 'local_only', local);
    if (!permittedRoute(incoming.pathname, request.method)) return fail(404, 'not_found', 'Recurso não encontrado.');
    // Pairing credentials are accepted in a JSON body; URL query credentials never pass.
    for (const key of incoming.searchParams.keys()) {
      if (/(token|secret|password|code|pair|session|csrf|path|url|target)/i.test(key)) return fail(400, 'invalid_query', 'Parâmetro não permitido.');
    }
    const write = !['GET', 'HEAD'].includes(request.method);
    const origin = request.headers.get('origin');
    if ((origin && origin !== publicOrigin) || (write && origin !== publicOrigin)) return fail(403, 'invalid_origin', 'Origem não permitida.');
    if (request.headers.get('sec-fetch-site') === 'cross-site' && (write || incoming.pathname.startsWith('/api/'))) return fail(403, 'cross_site', 'Origem não permitida.');
    if (write && !/^application\/json(?:\s*;|$)/i.test(request.headers.get('content-type') ?? '')) return fail(415, 'json_required', 'Envie os dados no formato JSON.');

    let body = null;
    try { if (write) body = await boundedBody(request, bodyLimit(incoming.pathname, request.method)); }
    catch { return fail(413, 'body_too_large', 'Pedido acima do limite permitido.'); }
    const headers = new Headers();
    for (const name of FORWARDED_HEADERS) {
      const value = request.headers.get(name);
      if (value !== null) headers.set(name, value);
    }
    // Never trust caller-supplied forwarding or gateway headers.
    headers.set('X-MB-Gateway', env.MB_GATEWAY_SECRET);
    headers.set('X-MB-Public-Origin', publicOrigin);
    headers.set('X-Forwarded-Proto', 'https');
    headers.set('X-Forwarded-Host', new URL(publicOrigin).host);
    // Cloudflare sets this header at the edge; never forward caller X-MB-Client-IP.
    const clientIP = request.headers.get('CF-Connecting-IP');
    if (clientIP && /^[0-9a-fA-F:.]{3,45}$/.test(clientIP)) headers.set('X-MB-Client-IP', clientIP);
    const target = new URL('http://127.0.0.1:8767');
    target.pathname = incoming.pathname;
    target.search = incoming.search;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15_000);
    try {
      // VPC Service configuration fixes the actual host/port independently of this URL.
      const response = await env.MEGABRAIN_ORIGIN.fetch(target.toString(), {
        method: request.method, headers, body, redirect: 'manual',
        signal: controller.signal,
      });
      if (response.status >= 300 && response.status < 400) return fail(502, 'unexpected_redirect', 'Resposta inesperada do aplicativo.');
      const responseHeaders = safeHeaders(response.headers);
      responseHeaders.delete('X-MB-Gateway');
      responseHeaders.delete('X-MB-Public-Origin');
      // Preserve the backend's Secure/HttpOnly/SameSite session cookie verbatim.
      return new Response(request.method === 'HEAD' ? null : response.body, {
        status: response.status, statusText: response.statusText, headers: responseHeaders,
      });
    } catch {
      return fail(503, 'computer_unavailable', 'O computador está desconectado ou o MegaBrain está fechado.');
    } finally { clearTimeout(timeout); }
  },
};
