#!/usr/bin/env node
/* mb-verificar-pop-tema.mjs — prova funcional do tema claro do POP v1.2
   em Chrome headless real (CDP), fora da suíte unittest.

   Cenários (proposta V6 aprovada, run 260915_165420_548975f0):
   6.1 default escuro · 6.3 clique → claro + persistido · 6.4 recarga mantém
   6.5 Enter/Espaço: exatamente uma troca · 6.6 precedência (salvo > doc; inválido ignorado)
   6.7 falha de leitura e de escrita de storage · varredura de cliques nos 2 temas
   contraste AA computado · zero requisição http/https

   Uso: node bin/mb-verificar-pop-tema.mjs <caminho-do-html> [saida.json]
*/
import { accessSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const ALVO = process.argv[2];
const SAIDA = process.argv[3] ?? null;
if (!ALVO) { console.error('uso: node mb-verificar-pop-tema.mjs <html> [saida.json]'); process.exit(2); }
const URL_ALVO = pathToFileURL(ALVO).href;

const CANDIDATOS = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  join(process.env.LOCALAPPDATA ?? '', 'Google/Chrome/Application/chrome.exe'),
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
];
const NAVEGADOR = CANDIDATOS.find(p => { try { accessSync(p); return true; } catch { return false; } }) ?? null;
if (!NAVEGADOR) { console.error('Chrome/Edge não encontrado'); process.exit(2); }

const PERFIL = mkdtempSync(join(tmpdir(), 'pop-tema-'));
const proc = spawn(NAVEGADOR, [
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  `--remote-debugging-port=0`, `--user-data-dir=${PERFIL}`, 'about:blank',
], { stdio: ['ignore', 'pipe', 'pipe'] });

const porta = await new Promise((resolve, reject) => {
  const t0 = Date.now();
  proc.stderr.on('data', d => {
    const m = d.toString().match(/DevTools listening on ws:\/\/127\.0\.0\.1:(\d+)/);
    if (m) resolve(Number(m[1]));
  });
  const espera = setInterval(() => {
    if (Date.now() - t0 > 15000) { clearInterval(espera); reject(new Error('Chrome não abriu a porta DevTools')); }
  }, 200);
});

await new Promise(r => setTimeout(r, 400));
const versao = await (await fetch(`http://127.0.0.1:${porta}/json/version`)).json();
const ws = new WebSocket(versao.webSocketDebuggerUrl);
await new Promise(r => { ws.onopen = r; });

let seq = 0;
const pendentes = new Map();
const eventos = [];
ws.onmessage = ev => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pendentes.has(msg.id)) { pendentes.get(msg.id)(msg); pendentes.delete(msg.id); }
  else if (msg.method) eventos.push(msg);
};
function enviar(method, params = {}, sessionId) {
  const id = ++seq;
  return new Promise((resolve, reject) => {
    pendentes.set(id, m => m.error ? reject(new Error(m.error.message)) : resolve(m.result));
    ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
  });
}
async function esperarEvento(method, ms = 15000) {
  const t0 = Date.now();
  for (;;) {
    const i = eventos.findIndex(e => e.method === method);
    if (i >= 0) return eventos.splice(i, 1)[0];
    if (Date.now() - t0 > ms) throw new Error(`timeout esperando ${method}`);
    await new Promise(r => setTimeout(r, 50));
  }
}

const { targetId } = await enviar('Target.createTarget', { url: 'about:blank' });
const { sessionId } = await enviar('Target.attachToTarget', { targetId, flatten: true });
const S = sessionId;
await enviar('Page.enable', {}, S);
await enviar('Runtime.enable', {}, S);
await enviar('Network.enable', {}, S);

async function avaliar(expr) {
  const r = await enviar('Runtime.evaluate', {
    expression: expr, returnByValue: true, awaitPromise: true,
  }, S);
  if (r.exceptionDetails) throw new Error('JS: ' + JSON.stringify(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text).slice(0, 400));
  return r.result.value;
}

let injecaoAtiva = null;
async function navegar(injecao = null) {
  eventos.length = 0;
  if (injecaoAtiva) {
    try { await enviar('Page.removeScriptToEvaluateOnNewDocument', { identifier: injecaoAtiva }, S); } catch {}
    injecaoAtiva = null;
  }
  if (injecao) {
    const r = await enviar('Page.addScriptToEvaluateOnNewDocument', { source: injecao }, S);
    injecaoAtiva = r.identifier;
  }
  await enviar('Page.navigate', { url: URL_ALVO }, S);
  await esperarEvento('Page.loadEventFired');
  await new Promise(r => setTimeout(r, 250));
}

const resultados = [];
function registrar(nome, ok, detalhe) {
  resultados.push({ nome, ok, detalhe });
  console.log(`${ok ? '✓' : '✗'} ${nome} — ${detalhe}`);
}

/* ── 6.1 default: sem preferência e sem flag → escuro ── */
await navegar();
{
  const d = await avaliar(`({
    tema: document.documentElement.getAttribute('data-tema'),
    pressed: document.getElementById('btn-tema').getAttribute('aria-pressed'),
    texto: document.getElementById('btn-tema-txt').textContent,
    habilitado: !document.getElementById('btn-tema').disabled,
    visivel: document.getElementById('btn-tema').offsetWidth > 0 && document.getElementById('btn-tema').offsetHeight > 0,
    storage: localStorage.getItem('megabrain.pop.tema'),
  })`);
  registrar('6.1 default escuro',
    d.tema !== 'claro' && d.pressed === 'false' && /escuro/.test(d.texto) && d.habilitado && d.visivel && d.storage === null,
    JSON.stringify(d));
}

/* ── 6.3 clique: muda pra claro, aria-pressed, status, localStorage ── */
{
  const d = await avaliar(`(async () => {
    const antes = document.documentElement.getAttribute('data-tema');
    document.getElementById('btn-tema').click();
    await new Promise(r => setTimeout(r, 60));
    return {
      antes,
      tema: document.documentElement.getAttribute('data-tema'),
      pressed: document.getElementById('btn-tema').getAttribute('aria-pressed'),
      texto: document.getElementById('btn-tema-txt').textContent,
      status: document.getElementById('tema-status').textContent,
      storage: localStorage.getItem('megabrain.pop.tema'),
      fundo: getComputedStyle(document.body).backgroundColor,
    };
  })()`);
  const ok = d.antes !== 'claro' && d.tema === 'claro' && d.pressed === 'true' &&
    /claro/.test(d.texto) && /Prefer[êe]ncia salva/.test(d.status) && d.storage === 'claro';
  registrar('6.3 clique → claro persistido', ok, JSON.stringify(d));
}

/* ── 6.4 recarga mantém claro; nova troca salva escuro; recarga mantém escuro ── */
await navegar();
{
  const d = await avaliar(`({
    tema: document.documentElement.getAttribute('data-tema'),
    pressed: document.getElementById('btn-tema').getAttribute('aria-pressed'),
  })`);
  await avaliar(`document.getElementById('btn-tema').click(); 'ok'`);
  await navegar();
  const d2 = await avaliar(`({
    tema: document.documentElement.getAttribute('data-tema'),
    texto: document.getElementById('btn-tema-txt').textContent,
    storage: localStorage.getItem('megabrain.pop.tema'),
  })`);
  registrar('6.4 recarga mantém a escolha (claro→troca→escuro mantido)',
    d.tema === 'claro' && d.pressed === 'true' && d2.tema === 'escuro' && d2.storage === 'escuro',
    JSON.stringify({ aposRecarga1: d, aposRecarga2: d2 }));
}

/* ── 6.5 Enter e Espaço: exatamente uma troca por acionamento ── */
{
  const d = await avaliar(`(async () => {
    let trocas = 0;
    const obs = new MutationObserver(() => trocas++);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-tema'] });
    const btn = document.getElementById('btn-tema');
    btn.focus();
    btn.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true }));
    btn.click(); // ativação nativa do Enter dispara click no <button>
    await new Promise(r => setTimeout(r, 60));
    const aposEnter = trocas; const temaAposEnter = document.documentElement.getAttribute('data-tema');
    trocas = 0;
    btn.dispatchEvent(new KeyboardEvent('keydown', { key: ' ', bubbles: true, cancelable: true }));
    btn.click();
    await new Promise(r => setTimeout(r, 60));
    const aposEspaco = trocas; const temaAposEspaco = document.documentElement.getAttribute('data-tema');
    obs.disconnect();
    return { aposEnter, temaAposEnter, aposEspaco, temaAposEspaco, foco: document.activeElement === btn };
  })()`);
  registrar('6.5 Enter/Espaço = 1 troca cada, foco permanece',
    d.aposEnter === 1 && d.aposEspaco === 1 && d.foco === true &&
    d.temaAposEnter !== d.temaAposEspaco, JSON.stringify(d));
}

/* ── 6.6 precedência: salvo vence documento; inválido é ignorado ── */
await navegar(`try{localStorage.setItem('megabrain.pop.tema','claro')}catch(e){}`);
{
  const d = await avaliar(`document.documentElement.getAttribute('data-tema')`);
  registrar('6.6a preferência clara vence documento escuro', d === 'claro', `data-tema=${d}`);
}
await navegar(`try{localStorage.setItem('megabrain.pop.tema','rosa')}catch(e){}`);
{
  const d = await avaliar(`({
    tema: document.documentElement.getAttribute('data-tema'),
    storage: localStorage.getItem('megabrain.pop.tema'),
  })`);
  registrar('6.6b valor salvo inválido é ignorado (fica no tema do documento)',
    d.tema !== 'claro' && d.storage === 'rosa', JSON.stringify(d));
}

/* ── 6.7a falha de ESCRITA: alterna e avisa sem prometer persistência ── */
await navegar(`(function(){
  const orig = Storage.prototype.setItem;
  Storage.prototype.setItem = function(k, v){ if (k === 'megabrain.pop.tema') throw new Error('simulação: gravação bloqueada'); return orig.call(this, k, v); };
})();`);
{
  const d = await avaliar(`(async () => {
    document.getElementById('btn-tema').click();
    await new Promise(r => setTimeout(r, 60));
    return {
      tema: document.documentElement.getAttribute('data-tema'),
      status: document.getElementById('tema-status').textContent,
    };
  })()`);
  registrar('6.7a escrita bloqueada: alterna e avisa honestamente',
    d.tema === 'claro' && /Não foi poss[íi]vel salvar/.test(d.status), JSON.stringify(d));
}

/* ── 6.7b falha de LEITURA: abre no tema do documento, botão funciona ── */
await navegar(`(function(){
  const orig = Storage.prototype.getItem;
  Storage.prototype.getItem = function(k){ if (k === 'megabrain.pop.tema') throw new Error('simulação: leitura bloqueada'); return orig.call(this, k); };
})();`);
{
  const d = await avaliar(`(async () => {
    const inicial = document.documentElement.getAttribute('data-tema');
    document.getElementById('btn-tema').click();
    await new Promise(r => setTimeout(r, 60));
    return { inicial, apos: document.documentElement.getAttribute('data-tema'),
      habilitado: !document.getElementById('btn-tema').disabled };
  })()`);
  registrar('6.7b leitura bloqueada: página utilizável e alternância funciona',
    d.inicial !== 'claro' && d.apos === 'claro' && d.habilitado, JSON.stringify(d));
}

/* ── varredura de cliques nos dois temas + contraste + rede ── */
const VARREDURA = `(() => {
  const temas = {};
  for (const forcar of ['escuro', 'claro']) {
    try { localStorage.setItem('megabrain.pop.tema', forcar); } catch(e) {}
    if (forcar === 'claro') { location.hash = ''; }
  }
  return 'recarregue';
})()`;

async function varredura(tema) {
  await navegar(`try{localStorage.setItem('megabrain.pop.tema','${tema}')}catch(e){}`);
  return avaliar(`(async () => {
    let toasts = 0;
    const fila = document.getElementById('toasts');
    const obs = new MutationObserver(() => { toasts++; });
    obs.observe(fila, { childList: true });
    window.addEventListener('click', e => e.preventDefault(), true); // <a> real não navega na prova
    const clicaveis = [...document.querySelectorAll('button:not([disabled]), a[href], [role="button"], summary')]
      .filter(el => el.id !== 'btn-tema'); // botão de tema: coberto pelos cenários 6.1–6.7
    const linhas = []; let semResposta = 0;
    for (const el of clicaveis) {
      const antesToasts = toasts;
      const antesTema = document.documentElement.getAttribute('data-tema');
      const antesPressed = el.getAttribute('aria-pressed');
      const detailsPai = el.closest('details');
      const antesOpen = detailsPai ? detailsPai.open : null;
      const rotulo = (el.id ? '#' + el.id : '') + '.' + (el.className && el.className.baseVal === undefined ? String(el.className).split(' ')[0] : el.tagName);
      el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
      await new Promise(r => setTimeout(r, 8));
      const mudou = toasts > antesToasts
        || el.getAttribute('aria-pressed') !== antesPressed
        || (detailsPai && detailsPai.open !== antesOpen)
        || document.documentElement.getAttribute('data-tema') !== antesTema;
      if (!mudou) { semResposta++; linhas.push({ rotulo, resposta: 'NENHUMA' }); }
    }
    // reabrir todos os details fechados que ficaram fechados pela varredura
    obs.disconnect();
    return { tema: document.documentElement.getAttribute('data-tema'),
      total: clicaveis.length, semResposta, amostraFalhas: linhas.slice(0, 12) };
  })()`);
}
{
  const escuro = await varredura('escuro');
  registrar(`varredura de cliques · ESCURO (${escuro.total} elementos)`,
    escuro.semResposta === 0, JSON.stringify(escuro));
  const claro = await varredura('claro');
  registrar(`varredura de cliques · CLARO (${claro.total} elementos)`,
    claro.semResposta === 0, JSON.stringify(claro));
}

/* ── contraste AA computado (tema claro) ── */
{
  await navegar(`try{localStorage.setItem('megabrain.pop.tema','claro')}catch(e){}`);
  const d = await avaliar(`(() => {
    function canais(c){
      if (c.startsWith('#')) {
        const h = c.length === 4 ? c.split('').slice(1).flatMap(x => [x, x]).join('') : c.slice(1);
        return [0, 2, 4].map(k => parseInt(h.slice(k, k + 2), 16));
      }
      return c.match(/\\d+(\\.\\d+)?/g).slice(0, 3).map(Number);
    }
    function lum(c){
      const [r, g, b] = canais(c).map(v => { v /= 255; return v <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); });
      return 0.2126*r + 0.7152*g + 0.0722*b;
    }
    function razao(a, b){ const [x,y] = [lum(a), lum(b)].sort((p,q)=>q-p); return (x+0.05)/(y+0.05); }
    const cs = getComputedStyle(document.documentElement);
    const fundo = cs.getPropertyValue('--fundo').trim() ? '#F5F3EE' : '#F5F3EE';
    // cores computadas de amostras reais, sobre o fundo declarado do tema
    const pares = [];
    const alvo = (sel, prop) => { const el = document.querySelector(sel); return el ? getComputedStyle(el)[prop] : null; };
    const corpo = getComputedStyle(document.body);
    const visivel = c => c && !/rgba\\([^)]*,\\s*0\\)/.test(c); // transparente = clip de gradiente
    const amostras = {
      'sub': alvo('.hero .sub', 'color'),
      'desc': alvo('.setor .desc', 'color'), 'td': alvo('td', 'color'),
      'cota small': alvo('.cota small', 'color'), 'tema-btn': alvo('.tema-btn', 'color'),
      'run small': alvo('.run small', 'color'),
      // textos coloridos por acento — precisam da versão -tx no claro
      'gate ok b': alvo('.gate--ok b', 'color'),
      'run ok q': alvo('.run--ok .q', 'color'),
      'ritmo': alvo('.cota--ok .ritmo', 'color'),
      'papel b': alvo('.papel b', 'color'),
      'acao n': alvo('.acao .n', 'color'),
    };
    const fundos = { 'fundo página': '#F5F3EE', 'card': getComputedStyle(document.querySelector('.setor')).backgroundColor };
    for (const [tn, cor] of Object.entries(amostras)) {
      for (const [fn, fc] of Object.entries(fundos)) {
        if (!cor || !fc) continue;
        let r;
        try { r = Math.round(razao(cor, fc) * 100) / 100; }
        catch (e) { pares.push({ texto: tn, fundo: fn, cor, fundoCor: fc, razao: 'ERRO:' + e.message }); continue; }
        pares.push({ texto: tn, fundo: fn, cor, fundoCor: fc, razao: r });
      }
    }
    return pares;
  })()`);
  const ruins = d.filter(p => p.razao < 4.5);
  registrar('contraste AA computado (claro): textos reais × fundo/cartão', ruins.length === 0,
    ruins.length ? JSON.stringify(ruins) : JSON.stringify(d));
}

/* ── zero requisição externa ── */
{
  const http = eventos.filter(e => e.method === 'Network.requestWillBeSent')
    .map(e => e.params.request.url)
    .filter(u => /^https?:/i.test(u));
  registrar('zero recurso remoto (requisições observadas durante a sessão)', http.length === 0,
    http.length ? http.slice(0, 5).join(' | ') : 'nenhuma requisição http/https');
}

ws.close(); proc.kill();
try { rmSync(PERFIL, { recursive: true, force: true, maxRetries: 3, retryDelay: 500 }); } catch {}

const falhas = resultados.filter(r => !r.ok);
const relatorio = { alvo: ALVO, navegador: NAVEGADOR, data: new Date().toISOString(), resultados, falhas: falhas.length };
if (SAIDA) writeFileSync(SAIDA, JSON.stringify(relatorio, null, 1), 'utf-8');
console.log(`\n${resultados.length - falhas.length}/${resultados.length} verificações OK${SAIDA ? ` · relatório: ${SAIDA}` : ''}`);
process.exit(falhas.length ? 1 : 0);
