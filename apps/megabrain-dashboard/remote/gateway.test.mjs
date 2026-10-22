import test from 'node:test';
import assert from 'node:assert/strict';
import gateway from './gateway.mjs';

const PUBLIC_ORIGIN = 'https://gateway.example.test';
const SECRET = 'a'.repeat(64); // Test fixture only; never accepted by a configured real backend.
function fixture(impl = () => new Response('{}', { headers: { 'Content-Type': 'application/json' } })) {
  const calls = [];
  const env = { PUBLIC_ORIGIN, MB_REMOTE_ENABLED: 'true', MB_GATEWAY_SECRET: SECRET,
    MEGABRAIN_ORIGIN: { fetch: async (...args) => { calls.push(args); return impl(...args); } } };
  return { env, calls };
}
function req(path = '/api/projects', init = {}) { return new Request(PUBLIC_ORIGIN + path, init); }
function write(path, init = {}) {
  return req(path, { method: 'POST', body: '{}', ...init,
    headers: { origin: PUBLIC_ORIGIN, 'content-type': 'application/json', ...(init.headers || {}) } });
}

test('disabled/incomplete configuration fails closed without contacting backend', async () => {
  for (const bad of [{MB_REMOTE_ENABLED:'false'}, {MB_GATEWAY_SECRET:''}, {PUBLIC_ORIGIN:'http://example.test'}, {PUBLIC_ORIGIN:'https://unconfigured.invalid'}, {MEGABRAIN_ORIGIN:null}]) {
    const {env,calls}=fixture(); Object.assign(env,bad);
    assert.equal((await gateway.fetch(req(),env)).status,503); assert.equal(calls.length,0);
  }
});
test('wrong public host, methods, arbitrary path and query credentials are denied', async () => {
  const {env,calls}=fixture();
  const inputs = [new Request('https://other.example.test/api/projects'), req('/api/projects',{method:'PATCH'}),
    req('/api/admin'), req('/api/files/abc?path=private'), req('/api/pair?code=secret'), req('/api/projects?target=https://other.test'), req('/api/files/a%2fb')];
  for (const request of inputs) assert.ok((await gateway.fetch(request,env)).status>=400);
  assert.equal(calls.length,0);
});
test('a request cannot change destination or smuggle gateway/forwarding headers', async () => {
  const {env,calls}=fixture();
  await gateway.fetch(req('/api/events?after=2',{headers:{'x-mb-gateway':'spoof','x-mb-public-origin':'https://evil.test',
    forwarded:'for=bad','x-forwarded-host':'evil.test','cf-access-jwt-assertion':'fake','cookie':'mb_session=opaque','x-mb-csrf':'csrf','idempotency-key':'fixture-repeat-1234','x-mb-client-ip':'spoof','cf-connecting-ip':'192.0.2.15'}}),env);
  const [url,options]=calls[0];
  assert.equal(url,'http://127.0.0.1:8767/api/events?after=2'); assert.equal(options.redirect,'manual');
  assert.equal(options.headers.get('X-MB-Gateway'),SECRET); assert.equal(options.headers.get('X-MB-Public-Origin'),PUBLIC_ORIGIN);
  assert.equal(options.headers.get('X-Forwarded-Host'),'gateway.example.test'); assert.equal(options.headers.get('forwarded'),null);
  assert.equal(options.headers.get('cf-access-jwt-assertion'),null); assert.equal(options.headers.get('Cookie'),'mb_session=opaque');
  assert.equal(options.headers.get('x-mb-csrf'),'csrf');
  assert.equal(options.headers.get('idempotency-key'),'fixture-repeat-1234');
  assert.equal(options.headers.get('x-mb-client-ip'),'192.0.2.15');
});
test('all mutations require same-origin JSON before the backend', async () => {
  const {env,calls}=fixture();
  for (const request of [req('/api/pair',{method:'POST',body:'{}'}),write('/api/pair',{headers:{origin:'https://evil.test'}}),
    write('/api/pair',{headers:{origin:'null'}}),write('/api/pair',{headers:{'content-type':'text/plain'}}),write('/api/pair',{headers:{'sec-fetch-site':'cross-site'}})]) {
    assert.ok((await gateway.fetch(request,env)).status>=400);
  }
  assert.equal(calls.length,0);
});
test('pairing accepts JSON in body and forwards it unchanged', async () => {
  const {env,calls}=fixture(); const payload=JSON.stringify({code:'pair-fixture'});
  assert.equal((await gateway.fetch(write('/api/pair',{body:payload}),env)).status,200);
  assert.equal(new TextDecoder().decode(calls[0][1].body),payload);
});
test('cookie security attributes and 401 are preserved; credentials never become response headers', async () => {
  const cookie='mb_session=opaque; Path=/; HttpOnly; Secure; SameSite=Strict';
  const {env}=fixture(()=>new Response('{"error":"unauthorized"}',{status:401,headers:{'Set-Cookie':cookie,'X-MB-Gateway':SECRET,'Cache-Control':'public,max-age=3600','Access-Control-Allow-Origin':'*'}}));
  const response=await gateway.fetch(req(),env);
  assert.equal(response.status,401); assert.equal(response.headers.get('set-cookie'),cookie);
  assert.match(response.headers.get('cache-control'),/no-store/); assert.equal(response.headers.get('x-mb-gateway'),null);
  assert.equal(response.headers.get('access-control-allow-origin'),null);
});
test('response body is streamed, including media range response', async () => {
  const content=new Uint8Array([1,2,3]);
  const {env,calls}=fixture(()=>new Response(content,{status:206,headers:{'Content-Type':'audio/mpeg','Content-Range':'bytes 0-2/3'}}));
  const response=await gateway.fetch(req('/api/files/known',{headers:{range:'bytes=0-2'}}),env);
  assert.equal(response.status,206); assert.equal(response.headers.get('content-range'),'bytes 0-2/3');
  assert.deepEqual(new Uint8Array(await response.arrayBuffer()),content); assert.equal(calls[0][1].headers.get('range'),'bytes=0-2');
});
test('origin redirects do not forward secrets to a second host', async () => {
  const {env,calls}=fixture(()=>new Response(null,{status:302,headers:{Location:'https://other.test'}}));
  const response=await gateway.fetch(req(),env);
  assert.equal(response.status,502); assert.equal(response.headers.get('location'),null); assert.equal(calls.length,1);
});
test('unreachable computer returns generic 503, no private exception detail', async () => {
  const {env}=fixture(()=>{throw Error('private-host '+SECRET);});
  const response=await gateway.fetch(req(),env); const text=await response.text();
  assert.equal(response.status,503); assert.equal(response.headers.get('retry-after'),'30'); assert.ok(!text.includes(SECRET)); assert.ok(!text.includes('private-host'));
});
test('body limit catches real streamed size without trusting content-length', async () => {
  const {env,calls}=fixture();
  const response=await gateway.fetch(write('/api/pair',{body:'x'.repeat(350_001)}),env);
  assert.equal(response.status,413); assert.equal(calls.length,0);
});
test('read-only public app navigation may originate from a clicked external link', async () => {
  const {env,calls}=fixture();
  assert.equal((await gateway.fetch(req('/',{headers:{'sec-fetch-site':'cross-site'}}),env)).status,200);
  assert.equal((await gateway.fetch(req('/api/projects',{headers:{'sec-fetch-site':'cross-site'}}),env)).status,403);
  assert.equal(calls.length,1);
});
test('HEAD strips upstream body and known contract routes pass', async () => {
  const {env}=fixture();
  const response=await gateway.fetch(req('/api/files/a',{method:'HEAD'}),env);
  assert.equal(await response.text(),'');
  for(const path of ['/manifest.webmanifest','/sw.js','/assets/main-hash.js','/icons/icon-192.png','/api/connection','/api/connection/qr','/api/health','/brand.png','/icon-192.png','/icon-512.png','/api/projects/abc/process','/api/projects/abc/routing']) {
    assert.equal((await gateway.fetch(req(path),env)).status,200,path);
  }
  for(const path of ['/api/projects/abc/comments','/api/projects/abc/references','/api/projects/abc/jobs','/api/projects/abc/route-preview','/api/logout']) {
    assert.equal((await gateway.fetch(write(path),env)).status,200,path);
  }
  assert.equal((await gateway.fetch(write('/api/workspace',{method:'PUT'}),env)).status,200);
  assert.equal((await gateway.fetch(write('/api/projects/abc/routing',{method:'PUT'}),env)).status,200);
});
// 261020: routes the app gained after 261011 (reports, returns, attachments, bridge).
const FID = 'e'.repeat(20), PID = 'd'.repeat(20), AID = 'f'.repeat(64), OID = '261020-061500-abcdef';
const UPLOAD_LIMIT = 4 * Math.floor((8 * 1024 * 1024 + 2) / 3) + 8192; // central_attachments.MAX_UPLOAD_BODY
test('report, returns and bridge routes pass only with exact backend ids and methods', async () => {
  const {env,calls}=fixture();
  for(const path of [`/api/reports/${FID}/status`,`/api/reports/${FID}/view?ticket=t-123`,`/api/reports/${FID}/render?ticket=t-123&version=${'a'.repeat(64)}`,
    `/api/reports/${FID}/note-receipts?hash=${'a'.repeat(64)}`,'/api/returns?after=3','/api/quotas','/api/session-connections','/api/bridge/vendors',
    `/api/projects/${PID}/attachments/${AID}`,`/api/projects/${PID}/bridge`,'/cursor-ferramentas-v1.2.js?v=261018-anexos']) {
    assert.equal((await gateway.fetch(req(path),env)).status,200,path);
  }
  for(const path of [`/api/reports/${FID}/draft`,`/api/reports/${FID}/feedback`,`/api/reports/${FID}/resolve`,`/api/projects/${PID}/attachments`,
    `/api/projects/${PID}/bridge/send`,`/api/projects/${PID}/bridge/orders/${OID}/stop`]) {
    assert.equal((await gateway.fetch(write(path),env)).status,200,path);
  }
  assert.equal((await gateway.fetch(write(`/api/projects/${PID}/bridge`,{method:'PUT'}),env)).status,200);
  const forwarded=calls.length;
  for(const [method,path] of [['GET','/api/reports/abc/status'],['GET',`/api/reports/${'E'.repeat(20)}/status`],['GET',`/api/reports/${FID}/feedback`],
    ['GET',`/api/reports/${FID}/logs`],['POST',`/api/reports/${FID}/status`],['GET',`/api/projects/${PID}/attachments/${'f'.repeat(24)}`],
    ['GET',`/api/projects/${PID}/attachments/../../.env`],['POST',`/api/projects/${PID}/bridge/orders/x/stop`],['POST',`/api/projects/${PID}/bridge/orders/${OID}`],
    ['DELETE',`/api/projects/${PID}/bridge`],['GET','/api/returns/x'],['GET','/cursor-ferramentas.js'],['GET','/cursor-ferramentas-v1.2.js.map']]) {
    const request=method==='GET'?req(path):write(path,{method});
    assert.ok((await gateway.fetch(request,env)).status>=400,`${method} ${path}`);
  }
  for(const path of [`/api/reports/${FID}/render?ticket=t&path=../x`,`/api/reports/${FID}/view?url=https://evil.test`,`/api/files/${FID}?target=x`])
    assert.equal((await gateway.fetch(req(path),env)).status,400,path);
  assert.equal(calls.length,forwarded);
});
test('report writes keep same-origin JSON before the backend', async () => {
  const {env,calls}=fixture();
  for(const request of [req(`/api/reports/${FID}/feedback`,{method:'POST',body:'{}',headers:{'content-type':'application/json'}}),
    write(`/api/reports/${FID}/feedback`,{headers:{origin:'https://evil.test'}}),write(`/api/projects/${PID}/attachments`,{headers:{'content-type':'text/plain'}}),
    write(`/api/projects/${PID}/bridge/send`,{headers:{'sec-fetch-site':'cross-site'}})]) {
    assert.ok((await gateway.fetch(request,env)).status>=400);
  }
  assert.equal(calls.length,0);
});
test('only the exact upload route accepts the attachment body size, measured on the stream', async () => {
  const {env,calls}=fixture();
  const big='x'.repeat(2_000_000);
  const upload=await gateway.fetch(write(`/api/projects/${PID}/attachments`,{body:big}),env);
  assert.equal(upload.status,200); assert.equal(calls.length,1); assert.equal(calls[0][1].body.byteLength,big.length);
  for(const path of [`/api/reports/${FID}/feedback`,'/api/pair',`/api/projects/${PID}/comments`,`/api/projects/${PID}/attachments/extra`])
    assert.ok([404,413].includes((await gateway.fetch(write(path,{body:big}),env)).status),path);
  // Streamed without Content-Length: the real byte count decides.
  const stream=new ReadableStream({start(c){c.enqueue(new Uint8Array(UPLOAD_LIMIT));c.enqueue(new Uint8Array(1));c.close();}});
  const over=await gateway.fetch(new Request(PUBLIC_ORIGIN+`/api/projects/${PID}/attachments`,{method:'POST',body:stream,duplex:'half',headers:{origin:PUBLIC_ORIGIN,'content-type':'application/json'}}),env);
  assert.equal(over.status,413);
  const declared=await gateway.fetch(write(`/api/projects/${PID}/attachments`,{body:'{}',headers:{'content-length':String(UPLOAD_LIMIT+1)}}),env);
  assert.equal(declared.status,413);
  assert.equal(calls.length,1);
});
test('computer-only actions get a readable 403 and never reach the backend', async () => {
  const {env,calls}=fixture();
  for(const [method,path] of [['POST',`/api/dispatch/${FID}`],['POST','/api/present'],['GET','/api/report-audit'],['HEAD','/api/report-audit'],
    ['POST','/api/quotas/open-widget'],['GET','/api/quotas/widget-settings'],['POST','/api/quotas/widget-settings'],['GET','/api/quotas/widget-settings/requests/req-1234']]) {
    const response=await gateway.fetch(method==='POST'?write(path):req(path,{method}),env);
    assert.equal(response.status,403,`${method} ${path}`);
    if(method!=='HEAD'){const body=await response.json();assert.equal(body.error,'local_only');assert.match(body.message,/computador|PC/);}
  }
  for(const [method,path] of [['GET','/api/present'],['GET',`/api/dispatch/${FID}`],['POST','/api/dispatch/abc'],['DELETE','/api/report-audit']]) {
    assert.equal((await gateway.fetch(method==='GET'?req(path):write(path,{method}),env)).status,404,`${method} ${path}`);
  }
  assert.equal(calls.length,0);
});
test('execution routes require fixed opaque ids and do not expose job logs or paths', async () => {
  const {env,calls}=fixture();const job='a'.repeat(32);const artifact='b'.repeat(24);
  for(const kind of ['artifacts','preview','render','resources','view']){
    assert.equal((await gateway.fetch(req(`/api/jobs/${job}/${kind}/${artifact}`),env)).status,200);
  }
  assert.equal((await gateway.fetch(req('/api/projects/abc/code-files'),env)).status,200);
  assert.equal((await gateway.fetch(write(`/api/jobs/${job}/cancel`),env)).status,200);
  const successful=calls.length;
  for(const path of [`/api/jobs/${job}/logs/stdout.log`,`/api/jobs/${job}/artifacts/../secret`,
    `/api/jobs/${job}/artifacts/${artifact}?path=secret`,`/api/jobs/bad/preview/${artifact}`,`/api/jobs/${job}/resources/main.js`]){
    assert.ok((await gateway.fetch(req(path),env)).status>=400,path);
  }
  assert.equal((await gateway.fetch(req(`/api/jobs/${job}/cancel`),env)).status,404);
  assert.equal(calls.length,successful);
});
