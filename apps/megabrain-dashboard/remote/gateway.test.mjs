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
