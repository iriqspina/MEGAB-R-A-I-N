// Chromium isolado; fontes sintéticas e host de upload em memória, sem API de produção.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFileSync, writeFileSync, mkdirSync, readdirSync, rmSync} from 'node:fs';
import {resolve, sep} from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {abrirNavegador, Aba, sleep} from '../../../../evidence/261017_cursor-harness/teste-cursor/cdp.mjs';

const root=fileURLToPath(new URL('../../../../',import.meta.url));
// Each invocation gets its own output; historical evidence is never a test target.
const outputRoot=process.env.MB_TEST_OUTPUT_ROOT ? pathToFileURL(resolve(process.env.MB_TEST_OUTPUT_ROOT)+sep) : new URL('../../../../evidence/test-runs/attachments-canonical/',import.meta.url);
const output=new URL(new Date().toISOString().replace(/[:.]/g,'-')+'-'+process.pid+'/',outputRoot);
mkdirSync(output,{recursive:true});
const previousProfiles=new Set(readdirSync(output));
const fid='abcdef0123456789abcd',token='canonical_attachment_ticket_261018';
// Print sintético raster visível (480×240), compartilhado com a prova isolada do app.
const png=readFileSync(new URL('../../../../evidence/261018_ponte-orquestradores/interface/fixture-print.png',import.meta.url)).toString('base64');
const fixtureCode=String.raw`
import sys,json,hashlib
from pathlib import Path
root=Path(sys.argv[1]);out=Path(sys.argv[2]);sys.path.insert(0,str(root/'apps/megabrain-dashboard'))
import central_reports as reports
current=(root/'motor/modelos/interacoes/261010_decisoes-respondiveis/decisoes-respondiveis.js').read_text(encoding='utf-8')
legacy=(root/'evidence/261018_ponte-orquestradores/interface/backup/motor/modelos/interacoes/261010_decisoes-respondiveis/decisoes-respondiveis.js').read_text(encoding='utf-8-sig')
values={}
for name,code in [('current',current),('legacy',legacy)]:
 source=out/(name+'-source.html')
 source.write_text('<!doctype html><html><head><meta charset="utf-8"><style>body{font:16px system-ui;background:#f1f0eb;color:#1c1c2b;margin:20px}#target{padding:24px;border:1px solid #888}textarea{width:95%}</style></head><body><h1>Teste isolado de prints</h1><div id="target">Âncora sintética para nota</div><textarea id="field" aria-label="Campo sintético"></textarea><div data-dr-sec="sec"></div><script>'+code+";window.fixtureDecisions=DecisoesRespondiveis.iniciar({cursor:false,chave:'fixture-decisions',titulo:'Decisão sintética',secoes:[{id:'sec',perguntas:[{id:'texto',tipo:'texto',titulo:'Explique com print'},{id:'opcao',tipo:'escolha',titulo:'Outra opção',rec:'outra',opcoes:[{v:'outra',t:'Outro',extra:'Explique'}]}]}]});window.fixtureCursor=CursorFerramentas.iniciar({modo:'local',chave:'fixture-notes',microfone:false,chip:true});window.fixtureRefs=[];window.fixtureHelper=CursorFerramentas.anexos.montarCampo({elemento:document.querySelector('#field'),getAnexos:()=>fixtureRefs,setAnexos:v=>fixtureRefs=v,aoEstado:s=>window.fixtureState=s});</script></body></html>",encoding='utf-8')
 source.write_text(source.read_text(encoding='utf-8').replace('<meta charset="utf-8">','<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'),encoding='utf-8')
 digest=hashlib.sha256(source.read_bytes()).hexdigest()
 values[name]={'wrapper':reports.wrapper_report('abcdef0123456789abcd','canonical_attachment_ticket_261018',expected_hash=digest),'render':reports.render_report(source,out,'abcdef0123456789abcd','canonical_attachment_ticket_261018'),'hash':digest}
values['headers']={'wrapper':reports.view_headers,'render':reports.render_headers}
print(json.dumps(values))
`;
const fixtures=JSON.parse(execFileSync('python',['-X','utf8','-c',fixtureCode,root,fileURLToPath(output)],{cwd:root,maxBuffer:8*1024*1024,encoding:'utf8'}));
let variant='current';
const parent=()=>`<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0}iframe{width:100vw;height:100vh;border:0}</style></head><body><iframe id="rel" sandbox="allow-scripts allow-same-origin allow-forms" src="/api/reports/${fid}/view"></iframe><script>
window.mesaCF={};window.observed=[];window.uploads=[];window.queued=[];window.pause=false;window.fail=false;window.counter=0;window.previewCount=0;
const fid=${JSON.stringify(fid)},token=${JSON.stringify(token)},hash=${JSON.stringify(fixtures[variant].hash)},png=${JSON.stringify(png)};
window.reply=m=>{let value;if(window.fail)value={error:'Falha sintética de upload'};else{const id='attachment'+(++counter);value={attachment:{id,path:'.mb-anexos/'+id+'.png',name:m.file.name,mime:m.file.mime,size:m.file.data.byteLength,url:'/api/projects/fixture/attachments/'+id}};}document.querySelector('#rel').contentWindow.postMessage({channel:'mb-attachment-result',token,fid,hash,requestId:m.requestId,...value},location.origin);};
addEventListener('message',e=>{const m=e.data;if(e.source!==document.querySelector('#rel').contentWindow||e.origin!==location.origin||m.token!==token||m.fid!==fid||m.hash!==hash)return;if(m.channel==='megabrain-report'){observed.push(m);return;}if(m.channel==='mb-attachment-request'){uploads.push({name:m.file.name,size:m.file.data.byteLength,mime:m.file.mime});if(window.pause)queued.push(m);else reply(m);}if(m.channel==='mb-attachment-preview-request'){previewCount++;e.source.postMessage({channel:'mb-attachment-preview-result',token,fid,hash,requestId:m.requestId,preview:'data:image/png;base64,'+png},location.origin);}});
</script></body></html>`;
const server=createServer((req,res)=>{let body,headers={'Content-Type':'text/html; charset=utf-8'};if(req.url==='/')body=parent();else if(req.url.startsWith(`/api/reports/${fid}/view`)){body=fixtures[variant].wrapper;headers={...headers,...fixtures.headers.wrapper};}else if(req.url.startsWith(`/api/reports/${fid}/render`)){body=fixtures[variant].render;headers={...headers,...fixtures.headers.render};}else{res.writeHead(404);res.end();return;}res.writeHead(200,headers);res.end(body);});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base='http://127.0.0.1:'+server.address().port,checks=[];let browser,exitCode=0;
const check=(name,value)=>{assert.ok(value,name);checks.push({name,ok:true});};
const wait=async(test)=>{for(let i=0;i<100;i++){if(await test())return;await sleep(30);}throw new Error('Espera excedida');};
const makeFile=`new File([Uint8Array.from(atob(${JSON.stringify(png)}),c=>c.charCodeAt(0))],'print.png',{type:'image/png'})`;
try{
 browser=await abrirNavegador(fileURLToPath(output));
 const page=await new Aba(browser).criar(1440,900);await page.ir(base+'/');
 check('CSP preserva connect-src none',fixtures.headers.render['Content-Security-Policy'].includes("connect-src 'none'"));
 check('sandbox impede acesso ao pai',await page.js('rel',`(()=>{try{parent.document.body;return false}catch{return true}})()`));
 check('fetch bloqueado no iframe',await page.js('rel',`fetch('/api/forbidden').then(()=>false,()=>true)`));
 check('Ctrl+V texto normal não interceptado',await page.js('rel',`(()=>{const d=new DataTransfer();d.setData('text/plain','texto normal');const e=new ClipboardEvent('paste',{clipboardData:d,bubbles:true,cancelable:true});document.querySelector('#field').dispatchEvent(e);return !e.defaultPrevented})()`));
 await page.js('topo','window.pause=true');
 await page.js('rel',`(()=>{const p=document.querySelector('#field + .mb-anexos input[type=file]'),d=new DataTransfer();d.items.add(${makeFile});p.files=d.files;p.dispatchEvent(new Event('change',{bubbles:true}));document.querySelector('#field').value='Rascunho mantido';})()`);
 await wait(()=>page.js('topo','uploads.length===1'));
 check('arquivo escolhido entra em upload pendente',await page.js('rel','fixtureState.pendente&&fixtureState.bloqueado&&fixtureRefs.length===0'));
 check('host recebe bloqueio agregado durante upload',await page.js('topo',`observed.some(m=>m.kind==='attachment-state'&&m.payload.blocked===true)`));
 await wait(()=>page.js('rel',`!!document.querySelector('#field + .mb-anexos img')`));
 check('prévia local aparece durante upload',true);
 await page.js('topo','window.pause=false;queued.splice(0).forEach(reply)');
 await wait(()=>page.js('rel','fixtureRefs.length===1&&!fixtureState.bloqueado'));
 check('host recebe liberação após upload',await page.js('topo',`observed.filter(m=>m.kind==='attachment-state').at(-1)?.payload.blocked===false`));
 check('referência final não contém bytes',await page.js('rel',`!JSON.stringify(fixtureRefs).includes('data:')&&!JSON.stringify(fixtureRefs).includes('base64')&&fixtureRefs[0].name==='print.png'`));
 check('escolha não apaga texto',await page.js('rel',`document.querySelector('#field').value==='Rascunho mantido'`));
 await page.js('rel',`document.querySelector('#field + .mb-anexos [aria-label^="Remover print"]').click()`);
 check('remoção retira referência e prévia',await page.js('rel',`fixtureRefs.length===0&&!document.querySelector('#field + .mb-anexos img')`));
 await page.js('topo','window.fail=true');
 await page.js('rel',`(()=>{const d=new DataTransfer();d.items.add(${makeFile});d.setData('text/plain',' com texto');const t=document.querySelector('#field');t.setSelectionRange(t.value.length,t.value.length);t.dispatchEvent(new ClipboardEvent('paste',{clipboardData:d,bubbles:true,cancelable:true}));})()`);
 await wait(()=>page.js('rel',`document.querySelector('#field + .mb-anexos').textContent.includes('Falha sintética')`));
 check('falha mantém arquivo removível e rascunho',await page.js('rel',`fixtureState.bloqueado&&document.querySelector('#field').value==='Rascunho mantido com texto'&&!!document.querySelector('#field + .mb-anexos img')`));
 await page.js('topo','window.fail=false');await page.js('rel',`[...document.querySelectorAll('#field + .mb-anexos button')].find(b=>b.textContent==='Tentar de novo').click()`);
 await wait(()=>page.js('rel','fixtureRefs.length===1&&!fixtureState.bloqueado'));
 check('retry conclui referência preservando texto',true);
 await page.js('rel',`fixtureHelper.adicionar([new File([new Uint8Array(8*1024*1024+1)],'grande.png',{type:'image/png'})])`);
 check('limite 8 MiB não apaga anexos existentes',await page.js('rel',`fixtureRefs.length===1&&fixtureState.bloqueado&&document.querySelector('#field + .mb-anexos').textContent.includes('até 8 MiB')`));
 await page.js('rel',`[...document.querySelectorAll('#field + .mb-anexos [aria-label^="Remover print"]')].find(b=>b.getAttribute('aria-label').includes('grande.png')).click()`);
 const before=await page.js('topo','uploads.length');
 await page.js('rel',`fixtureHelper.adicionar([new File(['<svg/>'],'inválido.svg',{type:'image/svg+xml'})])`);
 check('SVG é recusado antes do transporte',await page.js('topo',`uploads.length===${before}`));
 await page.js('rel',`[...document.querySelectorAll('#field + .mb-anexos [aria-label^="Remover print"]')].find(b=>b.getAttribute('aria-label').includes('inválido.svg')).click()`);
 await page.js('rel',`fixtureHelper.adicionar([new File([new Uint8Array(200000)],'transporte.png',{type:'image/png'})])`);
 await wait(()=>page.js('rel','fixtureRefs.length===2'));
 check('canal dedicado transporta imagem maior que160k',await page.js('topo',`uploads.some(u=>u.name==='transporte.png'&&u.size===200000)`));
 await page.js('rel',`fixtureHelper.adicionar([new File([new Uint8Array(8*1024*1024)],'limite-exato.png',{type:'image/png'})])`);
 await wait(()=>page.js('rel','fixtureRefs.length===3'));
 check('canal dedicado aceita o limite exato8MiB',await page.js('topo',`uploads.some(u=>u.name==='limite-exato.png'&&u.size===8*1024*1024)`));
 const oldCount=await page.js('topo',`observed.filter(m=>m.kind==='feedback').length`);
 await page.js('rel',`MegaBrainReport.saveFeedback({texto:'x'.repeat(160001)})`);await sleep(100);
 check('canal legado continua limitado a160k',await page.js('topo',`observed.filter(m=>m.kind==='feedback').length===${oldCount}`));
 await page.js('rel',`fixtureHelper.destruir();fixtureHelper=CursorFerramentas.anexos.montarCampo({elemento:document.querySelector('#field'),getAnexos:()=>fixtureRefs,setAnexos:v=>fixtureRefs=v,aoEstado:s=>window.fixtureState=s})`);
 await wait(()=>page.js('topo','previewCount>=3'));
 await wait(()=>page.js('rel',`document.querySelectorAll('#field + .mb-anexos img').length===3`));
 check('prévia de referência restaurada passa pelo pai',true);
 await page.js('rel',`(()=>{const t=document.createElement('textarea');t.id='offline';t.value='Texto offline preservado';document.body.appendChild(t);window.offline=CursorFerramentas.anexos.montarCampo({elemento:t,transporte:{},getAnexos:()=>[],setAnexos:()=>{}});offline.adicionar([${makeFile}]);})()`);
 await wait(()=>page.js('rel',`document.querySelector('#offline + .mb-anexos').textContent.includes('Abra no aplicativo MegaBrain')`));
 check('fora do app falha clara mantém texto e arquivo',await page.js('rel',`offline.bloqueado()&&document.querySelector('#offline').value==='Texto offline preservado'&&!!document.querySelector('#offline + .mb-anexos [aria-label^="Remover print"]')`));
 await page.js('rel',`offline.destruir();document.querySelector('#offline').remove()`);
 await page.js('rel',`fixtureCursor.usar('comentar')`);await page.clicar(await page.ponto('rel','#target'));
 check('editor de nota real abriu',await page.js('rel',`!!document.querySelector('.cf-editor textarea')`));
 await page.js('topo','window.pause=true');
 await page.js('rel',`(()=>{const d=new DataTransfer();d.items.add(${makeFile});document.querySelector('.cf-editor textarea').dispatchEvent(new ClipboardEvent('paste',{clipboardData:d,bubbles:true,cancelable:true}));})()`);
 await wait(()=>page.js('topo','queued.length===1'));
 await page.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});await page.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
 check('nota não fecha nem envia durante upload',await page.js('rel',`!!document.querySelector('.cf-editor')&&document.querySelector('.cf-salvar').disabled`));
 await page.js('topo','window.pause=false;queued.splice(0).forEach(reply)');
 await wait(()=>page.js('rel',`!document.querySelector('.cf-salvar').disabled&&!!document.querySelector('.cf-editor .mb-anexo')`));
 await page.js('rel',`document.querySelector('.cf-salvar').click()`);
 check('nota somente imagem é salva sem apagar',await page.js('rel',`!document.querySelector('.cf-editor')&&fixtureCursor.notas().length===1&&fixtureCursor.notas()[0].texto===''&&fixtureCursor.notas()[0].anexos.length===1`));
 await wait(()=>page.js('topo',`observed.some(m=>m.kind==='feedback'&&m.payload.kind==='notes'&&m.payload.notas.some(n=>n.anexos?.length))`));
 check('BOOTSTRAP preserva anexo no feedback de nota',true);
 check('rascunho de nota contém só referência curta',await page.js('rel',`(()=>{const saved=localStorage.getItem('fixture-notes');return saved.includes('.mb-anexos/')&&!saved.includes('data:image')})()`));
 await page.js('rel',`fixtureCursor.usar('interagir')`);
 await page.js('topo','window.pause=true');
 await page.js('rel',`(()=>{const d=new DataTransfer();d.items.add(${makeFile});document.querySelector('#dr_texto').dispatchEvent(new ClipboardEvent('paste',{clipboardData:d,bubbles:true,cancelable:true}));})()`);
 await wait(()=>page.js('topo','queued.length===1'));
 check('decisão não finaliza durante upload',await page.js('rel',`document.querySelector('#dr-finalizar').disabled&&fixtureDecisions.anexosPendentes()`));
 await page.js('topo','window.pause=false;queued.splice(0).forEach(reply)');
 await wait(()=>page.js('rel',`fixtureDecisions.respostas().texto.anexos.length===1`));
 check('decisão textual aceita imagem sem texto',await page.js('rel',`fixtureDecisions.respostas().texto.valor===''&&fixtureDecisions.respostas().texto.anexos.length===1`));
 await page.js('rel',`document.querySelector('#dr-finalizar').click();document.querySelector('#dr-enviar').click()`);
 await wait(()=>page.js('topo',`observed.some(m=>m.kind==='feedback'&&m.payload.kind==='decisions'&&m.payload.respostas.texto.anexos?.length)`));
 check('decisão entrega associação por pergunta',true);
 await page.js('rel',`(()=>{const d=new DataTransfer();d.items.add(${makeFile});document.querySelector('[data-dr-extra="opcao"]').dispatchEvent(new ClipboardEvent('paste',{clipboardData:d,bubbles:true,cancelable:true}));})()`);
 await wait(()=>page.js('rel',`fixtureDecisions.respostas().opcao.anexos.length===1`));
 check('complemento textual de opção aceita print',true);
 await page.js('rel',`(()=>{const d=new DataTransfer();for(let i=0;i<6;i++)d.items.add(new File([Uint8Array.from(atob(${JSON.stringify(png)}),c=>c.charCodeAt(0))],'extra'+i+'.png',{type:'image/png'}));const p=document.querySelector('#dr_f_texto .mb-anexos input[type=file]');p.files=d.files;p.dispatchEvent(new Event('change',{bubbles:true}));})()`);
 await wait(()=>page.js('rel',`fixtureDecisions.respostas().texto.anexos.length===6`));
 check('campo preserva seis e explica excedente',await page.js('rel',`document.querySelector('#dr_f_texto .mb-anexos').textContent.includes('Limite de 6 prints')`));
 check('decisões bloqueiam agregado maior que seis',await page.js('rel',`fixtureDecisions.anexosPendentes()&&document.querySelector('#dr-finalizar').disabled&&document.querySelector('#dr-anexos-aviso').textContent.includes('no total')`));
 await page.js('rel',`document.querySelector('#dr_f_texto .mb-anexos [aria-label^="Remover print"]').click()`);
 check('remoção libera agregado seis sem perder rascunho',await page.js('rel',`!fixtureDecisions.anexosPendentes()&&fixtureDecisions.respostas().texto.anexos.length===5&&fixtureDecisions.respostas().opcao.anexos.length===1`));
 await wait(()=>page.js('rel',`[...document.querySelectorAll('.mb-anexos img')].every(img=>img.complete&&img.naturalWidth>0)`));
 await page.js('rel',`document.querySelector('#dr_f_texto').scrollIntoView({block:'start'});`);
 await page.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false}).then(r=>writeFileSync(new URL('desktop.png',output),Buffer.from(r.data,'base64')));
 await page.tamanho(390,844,true);await sleep(100);
 check('layout móvel390 real sem largura excedida',await page.js('rel',`innerWidth===390&&document.documentElement.scrollWidth<=innerWidth+1`));
 await page.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false}).then(r=>writeFileSync(new URL('mobile.png',output),Buffer.from(r.data,'base64')));
 variant='legacy';await page.ir(base+'/');
 await page.js('rel',`(()=>{const d=new DataTransfer();d.items.add(${makeFile});document.querySelector('#dr_texto').dispatchEvent(new ClipboardEvent('paste',{clipboardData:d,bubbles:true,cancelable:true}));})()`);
 await wait(()=>page.js('rel',`fixtureDecisions.respostas().texto.anexos?.length===1`));
 check('decisão legada recebe adaptador sem editar HTML',true);
 check('rascunho legado não guarda bytes',await page.js('rel',`(()=>{const keys=Array.from({length:localStorage.length},(_,i)=>localStorage.key(i)).filter(k=>k.startsWith('mb-report-decision-attachments:'));return keys.length===1&&!localStorage.getItem(keys[0]).includes('data:image')})()`));
 await page.js('rel',`MegaBrainReport.dispatch({titulo:'Teste legado',respostas:{texto:{valor:''}}})`);
 await wait(()=>page.js('topo',`observed.some(m=>m.kind==='dispatch'&&m.payload.respostas.texto.anexos?.length===1)`));
 check('despacho legado conserva anexos associados',true);
 await page.js('topo','window.pause=true');await page.js('rel',`fixtureHelper.adicionar([${makeFile}])`);await wait(()=>page.js('topo','queued.length===1'));
 const requestId=await page.js('topo','queued[0].requestId');
 await page.js('env',`dispatchEvent(new MessageEvent('message',{source:parent,origin:'https://outro.invalid',data:{channel:'mb-attachment-result',token:${JSON.stringify(token)},fid:${JSON.stringify(fid)},hash:${JSON.stringify(fixtures.legacy.hash)},requestId:${JSON.stringify(requestId)},error:'forjado'}}))`);
 check('origem de resposta forjada é rejeitada',await page.js('rel','fixtureState.pendente&&fixtureState.bloqueado'));
 await page.js('topo','window.pause=false;queued.splice(0).forEach(reply)');await wait(()=>page.js('rel','!fixtureState.bloqueado'));
 check('sem erros JavaScript do teste',page.log.filter(v=>v.startsWith('EXC')).length===0);
 writeFileSync(new URL('resultado.json',output),JSON.stringify({ok:true,checks,logs:page.log},null,2));
 console.log(JSON.stringify({ok:true,total:checks.length,evidence:fileURLToPath(output)}));
}catch(error){exitCode=1;writeFileSync(new URL('resultado.json',output),JSON.stringify({ok:false,error:String(error.stack||error),checks},null,2));console.error(error);}
finally{if(browser)await browser.fechar();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));const baseDir=resolve(fileURLToPath(output));for(const name of readdirSync(output)){const target=resolve(baseDir,name);if(!previousProfiles.has(name)&&name.startsWith('p-')&&target.startsWith(baseDir+sep)){try{rmSync(target,{recursive:true,force:true,maxRetries:3,retryDelay:100});}catch{}}}process.exit(exitCode);}
