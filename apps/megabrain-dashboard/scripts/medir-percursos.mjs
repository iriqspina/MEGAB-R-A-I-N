#!/usr/bin/env node
/* medir-percursos.mjs — B-APP F0d · baseline de percursos (PLANO_FINAL §6.1, gate de paridade).
   Mede, em Chrome headless real (CDP), ações deliberadas e tempo até o conteúdo ficar utilizável
   nas portas atuais, em 1440 e 390 CSS px, frio (logo após recarregar sem cache) e quente (repetições).
   Rode SÓ contra a cópia isolada (scripts/isolated_server.py, porta 8768): abrir/fechar painéis grava
   o workspace da cópia. A mesma execução depois da F1 dá a comparação.

   Uso: node scripts/medir-percursos.mjs --link "http://localhost:8768/#pair=..." --saida <arquivo.json> [--n 5] [--termo planejamento]
   "Utilizável" = corpo do painel visível (sem hidden, altura > 40 px) ou moldura do relatório na tela;
   não mede pintura do conteúdo dentro do iframe isolado.
*/
import { accessSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { spawn } from 'node:child_process';
import os, { tmpdir } from 'node:os';
import { join } from 'node:path';

const arg = (nome, padrao) => { const i = process.argv.indexOf(`--${nome}`); return i > 0 ? process.argv[i + 1] : padrao; };
const LINK = arg('link'); const SAIDA = arg('saida'); const N = Number(arg('n', '5')); const TERMO = arg('termo', 'planejamento');
if (!LINK || !SAIDA || !/^http:\/\/(localhost|127\.0\.0\.1):8768\//.test(LINK)) {
  console.error('uso: --link http://localhost:8768/#pair=... --saida arquivo.json (somente a cópia isolada 8768)'); process.exit(2);
}
const BASE = new URL(LINK).origin + '/';
// A porta sozinha não prova a cópia: o servidor isolado marca toda resposta com x-mb-instancia: isolada.
const marca = (await fetch(BASE + 'api/health').catch(() => null))?.headers.get('x-mb-instancia');
if (marca !== 'isolada') { console.error('recusa: 8768 não respondeu como cópia isolada (sem x-mb-instancia: isolada)'); process.exit(2); }
const NAVEGADOR = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  join(process.env.LOCALAPPDATA ?? '', 'Google/Chrome/Application/chrome.exe'), 'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => { try { accessSync(p); return true; } catch { return false; } });
if (!NAVEGADOR) { console.error('Chrome/Edge não encontrado'); process.exit(2); }

const PERFIL = mkdtempSync(join(tmpdir(), 'mb-percursos-'));
const proc = spawn(NAVEGADOR, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-port=0', `--user-data-dir=${PERFIL}`, 'about:blank'], { stdio: ['ignore', 'pipe', 'pipe'] });
const porta = await new Promise((resolve, reject) => {
  const limite = setTimeout(() => reject(new Error('Chrome não abriu a porta DevTools')), 15000);
  proc.stderr.on('data', d => { const m = d.toString().match(/DevTools listening on ws:\/\/127\.0\.0\.1:(\d+)/); if (m) { clearTimeout(limite); resolve(Number(m[1])); } });
});
const alvo = (await (await fetch(`http://127.0.0.1:${porta}/json/list`)).json()).find(t => t.type === 'page');
const ws = new WebSocket(alvo.webSocketDebuggerUrl);
await new Promise(r => { ws.onopen = r; });
let seq = 0; const pendentes = new Map();
ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.id && pendentes.has(m.id)) { pendentes.get(m.id)(m); pendentes.delete(m.id); } };
const cdp = (method, params = {}) => new Promise((resolve, reject) => { const id = ++seq; pendentes.set(id, m => m.error ? reject(new Error(`${method}: ${m.error.message}`)) : resolve(m.result)); ws.send(JSON.stringify({ id, method, params })); });
const avaliar = async expr => { const r = await cdp('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || 'erro na página'); return r.result.value; };
const espera = ms => new Promise(r => setTimeout(r, ms));

// Ajudantes injetados na página: esperar visível e medir do clique até o alvo.
const AJUDA = `window.__mbMede={
  vis:e=>!!e&&!e.hidden&&!e.closest('[hidden]')&&e.getBoundingClientRect().height>40,
  ate:async(cond,limite=8000)=>{const t0=performance.now();while(performance.now()-t0<limite){const v=cond();if(v)return performance.now()-t0;await new Promise(r=>requestAnimationFrame(r));}return null;},
  fechar:async(btn)=>{if(btn&&btn.getAttribute('aria-pressed')==='true'){btn.click();await new Promise(r=>setTimeout(r,500));}},
};true`;

const FLUXOS = {
  abrir_app: { acoes: 0, porta: 'carregar o app até o catálogo de projetos', medir: null },
  abrir_projeto_cartao: { acoes: 1, porta: 'cartão em Seus projetos (home)', expr: `(async()=>{const M=window.__mbMede;const c=[...document.querySelectorAll('.home-card[data-cf-project]')][1];if(!c)return {erro:'sem cartão'};await M.fechar(c);const pid=c.dataset.cfProject;const t0=performance.now();c.click();const ms=await M.ate(()=>M.vis(document.querySelector('[data-home-body-key="project:'+pid+':"]')));return {ms,alvo:pid,fechou_no_segundo_clique:true};})()` },
  ler_novidade_recentes: { acoes: 1, porta: 'linha em Entregas e relatórios recentes (home)', expr: `(async()=>{const M=window.__mbMede;const b=document.querySelector('[data-cf-module="home-recent"]');if(!b)return {erro:'sem linha de recentes'};await M.fechar(b);const pid=b.dataset.cfProject;const antes=new Set([...document.querySelectorAll('[data-home-body-key^="report:'+pid+':"]')].filter(M.vis));b.click();const ms=await M.ate(()=>[...document.querySelectorAll('[data-home-body-key^="report:'+pid+':"]')].some(e=>M.vis(e)&&!antes.has(e)&&e.querySelector('iframe')));return {ms,alvo:b.getAttribute('aria-label')?.slice(0,60)};})()` },
  acompanhar_pedido: { acoes: 1, porta: 'linha em Pedidos e últimos registros (home)', expr: `(async()=>{const M=window.__mbMede;const b=document.querySelector('[data-cf-module^="home-process:"]');if(!b)return {erro:'sem pedido'};await M.fechar(b);const jid=b.dataset.cfModule.split(':')[1];b.click();const ms=await M.ate(()=>[...document.querySelectorAll('[data-home-body-key^="process:"]')].some(e=>e.dataset.homeBodyKey.endsWith(':'+jid)&&M.vis(e)));return {ms,alvo:jid};})()` },
  achar_antigo_localizador: { acoes: 3, porta: 'Ctrl+K → digitar → escolher (localizador F0b)', expr: `(async()=>{const M=window.__mbMede;document.dispatchEvent(new KeyboardEvent('keydown',{key:'k',ctrlKey:true,bubbles:true}));const t0=performance.now();const campo=await (async()=>{for(let i=0;i<100;i++){const c=document.querySelector('input[aria-label="Buscar em tudo"]');if(c)return c;await new Promise(r=>setTimeout(r,30));}})();if(!campo)return {erro:'busca não abriu'};const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;set.call(campo,${JSON.stringify(TERMO)});campo.dispatchEvent(new Event('input',{bubbles:true}));let item=null;for(let i=0;i<200&&!item;i++){item=[...document.querySelectorAll('.locator-list:not(.stale) li button')].find(b=>/relatório/i.test(b.innerText));if(!item)await new Promise(r=>setTimeout(r,25));}if(!item)return {erro:'nenhum relatório no resultado'};const titulo=item.querySelector('strong').innerText;item.click();const ms=await M.ate(()=>[...document.querySelectorAll('iframe')].some(f=>(f.title||'').startsWith(titulo)&&f.getBoundingClientRect().height>100));return {ms:ms===null?null:performance.now()-t0,alvo:titulo,fechar:titulo};})()` },
};
// F1a: porta antiga para achar item antigo — cartão do projeto → Biblioteca → Histórico → buscar → abrir.
// Preparo fora do tempo: /api/search escolhe um relatório histórico e o projeto dele (o usuário precisa lembrar qual é).
FLUXOS.achar_antigo_porta_antiga = { acoes: 4, porta: 'cartão do projeto → Biblioteca → Histórico → buscar → abrir', expr: `(async()=>{const M=window.__mbMede;
  const alvo=(await (await fetch('/api/search?scope=historico&kind=report&limit=1',{credentials:'include'})).json()).items?.[0];if(!alvo)return {erro:'sem relatório histórico no índice'};
  let acoes=4;const corpo=()=>document.querySelector('[data-home-body-key="project:'+alvo.project_id+':"]');
  let card=document.querySelector('.home-card[data-cf-project="'+alvo.project_id+'"]');
  if(!card){const todos=[...document.querySelectorAll('.home-more')].find(b=>/Ver todos/.test(b.innerText));if(todos){todos.click();acoes++;await new Promise(r=>setTimeout(r,300));card=document.querySelector('.home-card[data-cf-project="'+alvo.project_id+'"]');}}
  if(!card)return {erro:'cartão do projeto não encontrado'};await M.fechar(card);
  const t0=performance.now();card.click();
  if(await M.ate(()=>M.vis(corpo())&&corpo().querySelector('aside.report-library'))===null)return {erro:'biblioteca não apareceu'};
  const lib=corpo().querySelector('aside.report-library');[...lib.querySelectorAll('.library-tabs button')].find(b=>/Histórico/.test(b.innerText))?.click();
  const campo=lib.querySelector('input');const termo=alvo.title.slice(0,10);const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;set.call(campo,termo);campo.dispatchEvent(new Event('input',{bubbles:true}));
  let item=null;for(let i=0;i<120&&!item;i++){item=[...lib.querySelectorAll('.library-items article > button:first-of-type')].find(b=>b.innerText.startsWith(alvo.title.slice(0,10)));if(!item)await new Promise(r=>setTimeout(r,25));}
  if(!item)return {erro:'item não apareceu no Histórico da Biblioteca'};item.click();
  const ms=await M.ate(()=>[...document.querySelectorAll('iframe')].some(f=>(f.title||'').startsWith(alvo.title.slice(0,10))&&f.getBoundingClientRect().height>100));
  return {ms:ms===null?null:performance.now()-t0,alvo:alvo.title.slice(0,60),acoes,fechar:alvo.title};})()` };

// F1a revisão GLM: par justo com a porta antiga — mesmo alvo histórico e mesmo termo (10 primeiros caracteres do título).
FLUXOS.achar_antigo_localizador_mesmo_alvo = { acoes: 3, porta: 'Ctrl+K → digitar o mesmo termo da porta antiga → escolher o mesmo alvo', expr: `(async()=>{const M=window.__mbMede;
  const alvo=(await (await fetch('/api/search?scope=historico&kind=report&limit=1',{credentials:'include'})).json()).items?.[0];if(!alvo)return {erro:'sem relatório histórico no índice'};
  document.dispatchEvent(new KeyboardEvent('keydown',{key:'k',ctrlKey:true,bubbles:true}));const t0=performance.now();
  let campo=null;for(let i=0;i<100&&!campo;i++){campo=document.querySelector('input[aria-label="Buscar em tudo"]');if(!campo)await new Promise(r=>setTimeout(r,30));}if(!campo)return {erro:'busca não abriu'};
  const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;set.call(campo,alvo.title.slice(0,10));campo.dispatchEvent(new Event('input',{bubbles:true}));
  let item=null;for(let i=0;i<200&&!item;i++){item=[...document.querySelectorAll('.locator-list:not(.stale) li button')].find(b=>b.querySelector('strong')?.innerText===alvo.title);if(!item)await new Promise(r=>setTimeout(r,25));}
  if(!item)return {erro:'alvo não apareceu no localizador'};item.click();
  const ms=await M.ate(()=>[...document.querySelectorAll('iframe')].some(f=>(f.title||'').startsWith(alvo.title.slice(0,10))&&f.getBoundingClientRect().height>100));
  return {ms:ms===null?null:performance.now()-t0,alvo:alvo.title.slice(0,60),fechar:alvo.title};})()` };
const ORDEM = (arg('fluxos', '') || Object.keys(FLUXOS).join(',')).split(',').filter(f => FLUXOS[f]);

const SEM_MEDIDA = {
  comparar_respostas: 'Comparar exige montar vários leitores e arranjo; harness dedicado fica como pré-condição de F1.',
  decidir_no_celular: 'Enviar decisão grava feedback; só com a ponte desligada e conferência de recibo; não automatizado em F0.',
  recuperar_conexao: 'Perda de rede e reenvio idempotente pedem simulação de rede no gateway; não automatizado em F0.',
};

const resultado = { gerado_em: new Date().toISOString(), navegador: NAVEGADOR.split('/').pop(), base: BASE, repeticoes: N, termo: TERMO,
  definicao: 'frio = primeira execução após recarregar com cache HTTP desligado (abrir_app: todas as repetições); quente = repetições na mesma página. Tempo do clique até o alvo utilizável, medido na página (performance.now).',
  uso: 'Referência de ordem de grandeza. Com N pequeno e variação alta, não decide paridade fina; o gate da F1 pede no mínimo 10 amostras quentes por fluxo nas mesmas condições, senão "paridade não verificada" (PLANO_FINAL §6.1).',
  componentes_fixos: { localizador_debounce_ms: 220, fonte: 'web/src/Locator.tsx (setTimeout 220 ms antes de cada busca); a Biblioteca filtra local, sem rede nem espera' },
  ordem_fluxos: ORDEM, viewports: {}, nao_medido: SEM_MEDIDA };
// Condições da medida (gate §6.1: mesmo aparelho, acervo e estado inicial). Coletadas no início e no fim.
const condicoes = async () => {
  const busca = await avaliar(`fetch('/api/search?limit=1',{credentials:'include'}).then(r=>r.json()).then(j=>({itens:j.counts?.total,projetos:j.coverage?.length,nao_lidos:j.coverage?.filter(c=>c.status==='nao_lido').length,revisao:j.query_revision}))`).catch(e => ({ erro: e.message }));
  const appReal = await fetch('http://127.0.0.1:8766/api/health').then(r => r.ok).catch(() => false);
  return { em: new Date().toISOString(), acervo: busca, app_real_8766_no_ar: appReal, carga_1min: os.loadavg()[0] || 'NAO_MEDIDO (Windows)', memoria_livre_gb: +(os.freemem() / 2 ** 30).toFixed(1) };
};
try {
  await cdp('Page.enable'); await cdp('Runtime.enable'); await cdp('Network.enable');
  await cdp('Page.navigate', { url: LINK }); await espera(4000);
  const versao = await (await fetch(`http://127.0.0.1:${porta}/json/version`)).json();
  // A cópia indexa 1 projeto por ciclo ao subir: medir só com o índice completo, senão abrir_app paga a ingestão.
  let esperou = 0; for (; esperou < 180; esperou += 5) { const c = await condicoes(); if (c.acervo?.nao_lidos === 0) break; await espera(5000); }
  resultado.condicoes = { maquina: { cpu: os.cpus()[0]?.model, nucleos: os.cpus().length, memoria_gb: +(os.totalmem() / 2 ** 30).toFixed(1), sistema: `${os.platform()} ${os.release()}` },
    navegador: versao.Browser, espera_indice_completo_s: esperou, inicio: await condicoes() };
  for (const [nome, vp] of Object.entries({ '1440': { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false }, '390': { width: 390, height: 844, deviceScaleFactor: 2, mobile: true } })) {
    await cdp('Emulation.setDeviceMetricsOverride', vp);
    await cdp('Emulation.setTouchEmulationEnabled', { enabled: vp.mobile });
    const porFluxo = {};
    for (const fluxo of ORDEM) { const def = FLUXOS[fluxo];
      const amostras = []; let detalhe = null;
      for (let i = 0; i < N; i++) {
        const frio = i === 0;
        if (frio || fluxo === 'abrir_app') {
          await cdp('Network.setCacheDisabled', { cacheDisabled: true });
          await cdp('Page.navigate', { url: BASE });
          const t = await (async () => { for (let k = 0; k < 400; k++) { await espera(50); try { const v = await avaliar(`(()=>{const c=document.querySelector('.home-card');return c&&c.getBoundingClientRect().height>0?performance.now():0})()`); if (v) return v; } catch {} } return null; })();
          await cdp('Network.setCacheDisabled', { cacheDisabled: false });
          await avaliar(AJUDA); await espera(800);
          // abrir_app recarrega sem cache em toda repetição: todas as amostras são frias.
          if (fluxo === 'abrir_app') { amostras.push({ frio: true, ms: t === null ? null : Math.round(t) }); continue; }
        }
        let r; try { r = await avaliar(def.expr); } catch (e) { r = { erro: e.message }; }
        if (r?.erro) { detalhe = r.erro; amostras.push({ frio, ms: null, erro: r.erro }); }
        else { detalhe = r.alvo ?? detalhe; amostras.push({ frio, ms: r.ms === null ? null : Math.round(r.ms), ...(r.acoes ? { acoes: r.acoes } : {}) }); }
        // Reset fora do tempo: fecha o relatório aberto pela rodada, senão a seguinte só mediria "já estava aberto".
        if (r?.fechar) { const n = await avaliar(`(async()=>{const t=${JSON.stringify(r.fechar)};const bs=[...document.querySelectorAll('button[aria-label]')].filter(b=>{const l=b.getAttribute('aria-label');return l.startsWith('Fechar '+t.slice(0,20))&&!/guardado/.test(l)});bs.forEach(b=>b.click());await new Promise(r=>setTimeout(r,400));return bs.length})()`).catch(() => 0); if (!n) amostras[amostras.length - 1].sem_reset = true; }
        await avaliar(`document.querySelector('.modal-backdrop, [role="dialog"]')&&document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))`).catch(() => {});
        await espera(600);
      }
      const ok = amostras.filter(a => typeof a.ms === 'number').map(a => a.ms); const quentes = amostras.filter(a => !a.frio && typeof a.ms === 'number').map(a => a.ms).sort((a, b) => a - b);
      const frios = amostras.filter(a => a.frio && typeof a.ms === 'number').map(a => a.ms).sort((a, b) => a - b);
      porFluxo[fluxo] = { porta: def.porta, acoes_deliberadas: def.acoes, alvo: detalhe, frio_ms: amostras[0]?.ms ?? null,
        frio_mediana_ms: frios.length > 1 ? frios[Math.floor(frios.length / 2)] : null,
        quente_ms: quentes, quente_mediana_ms: quentes.length ? quentes[Math.floor(quentes.length / 2)] : null,
        min_ms: ok.length ? Math.min(...ok) : null, max_ms: ok.length ? Math.max(...ok) : null,
        falhas: amostras.filter(a => a.ms === null).length, amostras };
      console.log(nome, fluxo, JSON.stringify({ frio: porFluxo[fluxo].frio_ms, quente: porFluxo[fluxo].quente_mediana_ms, falhas: porFluxo[fluxo].falhas }));
    }
    resultado.viewports[nome] = porFluxo;
  }
  resultado.condicoes.fim = await condicoes();
} finally {
  writeFileSync(SAIDA, JSON.stringify(resultado, null, 2), 'utf8');
  try { ws.close(); } catch {} proc.kill(); await espera(500); try { rmSync(PERFIL, { recursive: true, force: true }); } catch {}
}
