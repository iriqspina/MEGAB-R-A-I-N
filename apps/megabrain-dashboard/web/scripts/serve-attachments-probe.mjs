// Isolated development fixture. Never mounts the real app or contacts its API.
import {createServer} from 'vite';
import {readFileSync} from 'node:fs';
const png=readFileSync(new URL('../../../../evidence/261018_ponte-orquestradores/interface/fixture-print.png',import.meta.url));
const server=await createServer({server:{host:'127.0.0.1',port:8792,strictPort:true},plugins:[{name:'attachments-fixture',configureServer(v){v.middlewares.use(async(req,res,next)=>{
if(/^\/api\/projects\/p\/attachments\/print\d+$/.test(req.url||'')){res.setHeader('Content-Type','image/png');res.end(png);return;}
if(req.url!=='/attachments-probe')return next();res.setHeader('Content-Type','text/html; charset=utf-8');res.end(await v.transformIndexHtml('/attachments-probe','<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>Prova isolada de prints</title><script>window.PROBE_PNG='+JSON.stringify(png.toString('base64'))+'</script><style>body{font:15px system-ui;margin:24px;background:#181921;color:#eee}button{cursor:pointer}textarea{font:inherit;min-height:80px}main{max-width:800px}#checks{white-space:pre-wrap}</style><div id="root"></div><script type="module" src="/scripts/attachments-probe-entry.js"></script>'));
});}}]});
await server.listen();console.log('Fixture isolada em http://127.0.0.1:8792/attachments-probe');
