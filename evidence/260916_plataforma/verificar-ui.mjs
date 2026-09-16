import {spawn} from 'node:child_process';
import {existsSync,mkdirSync,writeFileSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
const here=resolve(fileURLToPath(new URL('.',import.meta.url))),root=resolve(here,'../..');
const chrome=['C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(existsSync);
if(!chrome)throw Error('Navegador não encontrado');
const profile=join(root,'.scratch','260916-plataforma-ui-'+Date.now());mkdirSync(profile,{recursive:true});
const proc=spawn(chrome,['--headless=new','--no-first-run','--no-default-browser-check','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{windowsHide:true,stdio:['ignore','pipe','pipe']});
const port=await new Promise((res,rej)=>{let t=setTimeout(()=>rej(Error('Chrome timeout')),15000);proc.stderr.on('data',b=>{let m=b.toString().match(/DevTools listening on ws:\/\/127\.0\.0\.1:(\d+)/);if(m){clearTimeout(t);res(Number(m[1]))}});proc.on('error',rej)});
const version=await(await fetch('http://127.0.0.1:'+port+'/json/version')).json();
const ws=new WebSocket(version.webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);let next=0;const pending=new Map(),events=[];
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result)}}else events.push(m)};
function send(method,params={},sessionId){return new Promise((resolve,reject)=>{const id=++next;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params,...(sessionId?{sessionId}:{})}))})}
let session;
const results=[];function check(name,condition,details){results.push({name,pass:!!condition,details});if(!condition)console.error('FAIL',name,details)}
async function evalJS(expression){const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true},session);if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value}
const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function navigate(path){await send('Page.navigate',{url:pathToFileURL(path).href},session);for(let i=0;i<60;i++){await pause(50);if(await evalJS("document.readyState==='complete'"))return}throw Error('load timeout')}
async function screenshot(name,width,height){await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false},session);await pause(150);const s=await send('Page.captureScreenshot',{format:'png'},session);writeFileSync(join(here,name+'.png'),Buffer.from(s.data,'base64'));}
try{
 const t=await send('Target.createTarget',{url:'about:blank'});session=(await send('Target.attachToTarget',{targetId:t.targetId,flatten:true})).sessionId;await send('Page.enable',{},session);await send('Runtime.enable',{},session);await send('Network.enable',{},session);
 await navigate(join(root,'00_painel','RELATORIO.html'));await screenshot('painel-tecnico-atual',1440,900);
 const path=join(root,'00_PARA-VOCE','INICIO.html');await navigate(path);await screenshot('inicio-escuro-1440',1440,900);
 check('entrada carregada',await evalJS("document.title==='MEGABRAIN · Início'"));
 check('nenhum overflow desktop',await evalJS('document.documentElement.scrollWidth<=innerWidth'));
 check('legado começa recolhido',await evalJS("!document.querySelector('#legacy').open"));
 check('bussola explicita aparece',await evalJS("document.querySelector('.compass').textContent.includes('Começou:')&&document.querySelector('.compass').textContent.includes('Agora:')"));
 const links=await evalJS("[...document.querySelectorAll('a[href]')].map(a=>a.href)");let missing=[];for(const l of links)if(l.startsWith('file:')){const p=fileURLToPath(l);if(!existsSync(p))missing.push(p)}check('destinos locais existem',missing.length===0,{links:links.length,missing});
 await evalJS("document.querySelector('#theme').click()");check('tema claro',await evalJS("document.documentElement.dataset.tema==='claro'"));await screenshot('inicio-claro-1440',1440,900);
 await send('Page.reload',{},session);await pause(300);check('tema persiste',await evalJS("document.documentElement.dataset.tema==='claro'"));
 await evalJS("document.querySelector('#q').value='nenhuma-entrega-zzzzz';document.querySelector('#q').dispatchEvent(new Event('input'))");check('busca vazia',await evalJS("!document.querySelector('#empty').hidden&&document.querySelector('#count').textContent.startsWith('0 ' )"));
 await evalJS("document.querySelector('#q').value='plataforma';document.querySelector('#q').dispatchEvent(new Event('input'))");check('busca encontra tarefa',await evalJS("document.querySelectorAll('article:not([hidden])').length>=1"));
 await evalJS("document.querySelector('#q').value='';document.querySelector('#q').dispatchEvent(new Event('input'));document.querySelector('#legacy').open=false");
 await evalJS("Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async(t)=>{window.copiado=t}}});document.querySelector('[data-copy]').click()");await pause(100);check('copia caminho absoluto',await evalJS("typeof window.copiado==='string'&&/^[A-Z]:/.test(window.copiado)&&document.querySelector('#toast').textContent.includes('copiado')"));
 await evalJS("navigator.clipboard.writeText=async()=>{throw Error('blocked')};document.execCommand=()=>false;document.querySelector('[data-copy]').click()");await pause(100);check('falha copia nao mente',await evalJS("document.querySelector('#toast').textContent.includes('indisponível')&&document.querySelector('textarea').value.length>10"));await evalJS("document.querySelector('textarea').remove();document.querySelector('#toast').textContent='' ");
 await screenshot('inicio-claro-390',390,844);check('nenhum overflow 390',await evalJS('document.documentElement.scrollWidth<=innerWidth'));
 await send('Page.bringToFront',{},session);await evalJS("document.querySelector('#theme').focus()");await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',text:'\r',unmodifiedText:'\r',windowsVirtualKeyCode:13},session);await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13},session);check('teclado ativa tema',await evalJS("document.documentElement.dataset.tema==='escuro'"));
 await screenshot('inicio-escuro-390',390,844);
 await navigate(join(root,'00_PARA-VOCE','260916_plataforma','260916_ANALISE.html'));await screenshot('analise-1440',1440,900);check('analise abre',await evalJS("document.title.includes('análise')"));
 const analysisLinks=await evalJS("[...document.querySelectorAll('a[href]')].map(a=>a.href)");let absent=[];for(const l of analysisLinks)if(l.startsWith('file:')&&!existsSync(fileURLToPath(l)))absent.push(fileURLToPath(l));check('fontes da analise existem',absent.length===0,{links:analysisLinks.length,missing:absent});
 const remote=events.filter(e=>e.method==='Network.requestWillBeSent'&&/^https?:/.test(e.params.request.url));check('zero recurso remoto',remote.length===0,{requests:remote.length});
 writeFileSync(join(here,'ui-browser.json'),JSON.stringify({date:new Date().toISOString(),tests:results,pass:results.every(x=>x.pass)},null,2));
 console.log(JSON.stringify(results,null,2));
}finally{await send('Browser.close').catch(()=>{});ws.close();}
process.exitCode=results.every(x=>x.pass)?0:1;
