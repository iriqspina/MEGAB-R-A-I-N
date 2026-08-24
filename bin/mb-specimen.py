#!/usr/bin/env python3
"""
Gerador de SPECIMENS visuais — megabrain 04_visuais.

Por que specimen e não screenshot: print de landing page é 80% hero e 20%
mecanismo, muda quando o site muda, e não cabe numa pasta de referência que
serve pra decidir. O specimen isola O MECANISMO — a paleta real, o par
tipográfico, o dispositivo de layout — no mesmo formato pra todos, para dar
pra comparar lado a lado.

Cada cartão declara a URL da fonte: o specimen é a leitura, o site é a verdade.
"""
import html as H
import json
from pathlib import Path

SAIDA = Path("/tmp/spec/out")
SAIDA.mkdir(parents=True, exist_ok=True)

CSS_BASE = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1000px;height:700px;background:#0e0e10;color:#e8e6e1;
  font-family:'Inter','Helvetica Neue',Arial,sans-serif;display:flex;flex-direction:column;
  -webkit-font-smoothing:antialiased;overflow:hidden}
.cab{display:flex;align-items:baseline;gap:14px;padding:26px 34px 0;flex-wrap:wrap}
.n{font-family:'IBM Plex Mono',monospace;font-size:12px;font-weight:600;letter-spacing:.18em;color:#6f6d68}
.nome{font-size:26px;font-weight:700;letter-spacing:-.02em}
.tipo{font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:500;letter-spacing:.16em;
  text-transform:uppercase;color:#8e8b84;border:1px solid #2e2e31;padding:2px 8px;border-radius:2px}
.oque{padding:8px 34px 0;font-size:14px;color:#a3a09a;line-height:1.5;max-width:88ch}
.palco{flex:1;margin:20px 34px;background:#141416;border:1px solid #26262a;
  display:flex;align-items:center;justify-content:center;overflow:hidden;position:relative}
.rodape{display:grid;grid-template-columns:1fr 1fr;gap:0;border-top:1px solid #26262a}
.rod{padding:16px 34px 22px}
.rod+.rod{border-left:1px solid #26262a}
.rot{font-family:'IBM Plex Mono',monospace;font-size:9.5px;font-weight:600;letter-spacing:.16em;
  text-transform:uppercase;margin-bottom:5px}
.rot.s{color:#5fd18f}.rot.n{color:#e08a7c}
.rod p{font-size:12.5px;line-height:1.5;color:#b9b6b0}
.url{position:absolute;right:34px;top:30px;font-family:'IBM Plex Mono',monospace;
  font-size:10px;color:#5c5a56}
"""

# ── cada specimen: (n, nome, tipo, oque, demo_html, demo_css, roubar, nao, url)
SPECS = [
("01","Linear","estética · cinza quente",
 "O refresh documentado pela própria equipe. O movimento de estado-da-arte em 2025 foi <em>para longe do frio</em> — sem virar papel.",
 """<div class=lin>
   <div class=lin__side><b>navegação</b><span>rebaixada de propósito</span></div>
   <div class=lin__main>
     <div class=lin__card><b>conteúdo</b><span>domina por contraste, não por tamanho</span></div>
     <div class=lin__sw>
       <i style="background:#08090a"></i><i style="background:#141516"></i>
       <i style="background:#1c1c1f"></i><i style="background:#23252a"></i>
       <i style="background:#3e3e44"></i>
     </div>
     <div class=lin__leg>quatro degraus + hairline · nenhuma sombra em lugar nenhum</div>
   </div>
 </div>""",
 """.lin{display:flex;width:100%;height:100%}
 .lin__side{width:190px;background:#08090a;padding:22px 18px;border-right:1px solid #23252a}
 .lin__side b{display:block;font-size:13px;color:#5c5a56}
 .lin__side span{font-size:11px;color:#3e3e44}
 .lin__main{flex:1;background:#141516;padding:26px 30px;display:flex;flex-direction:column;gap:18px;justify-content:center}
 .lin__card{background:#1c1c1f;border:1px solid #3e3e44;padding:18px 20px}
 .lin__card b{display:block;font-size:17px;font-weight:590;letter-spacing:-.016em}
 .lin__card span{font-size:12px;color:#8e8b84}
 .lin__sw{display:flex;gap:0}.lin__sw i{flex:1;height:34px;display:block}
 .lin__leg{font-family:'IBM Plex Mono',monospace;font-size:10px;color:#6f6d68;letter-spacing:.04em}""",
 "Elevação por empilhamento de cinzas quase idênticos + hairline de 1px. E rebaixar a navegação em vez de promover o conteúdo — é mais barato e mais eficaz. Inter no peso <b>590</b> (não 600) com tracking negativo escalonado.",
 "O “softening” aplicado a tudo. A Linear otimiza para calma; monitoramento quer densidade e urgência. Suavizar toda borda apaga a separação entre séries.",
 "linear.app/now/how-we-redesigned-the-linear-ui"),

("02","Raycast","estética · escada de superfície",
 "Command center para macOS. Densidade de instrumento sem um único drop shadow no produto inteiro.",
 """<div class=ray>
   <div class=ray__row style="background:#0d0d0d"><span>canvas</span><code>#07080a</code></div>
   <div class=ray__row style="background:#101111"><span>surface</span><code>#0d0d0d</code></div>
   <div class=ray__row style="background:#121212"><span>elevated</span><code>#101111</code></div>
   <div class="ray__row ray__row--on"><span>linha ativa</span><code>#121212</code><kbd>⌘K</kbd></div>
   <div class=ray__leg>profundidade = 4 tons na escala escura. Custo de render: zero.</div>
 </div>""",
 """.ray{width:78%;display:flex;flex-direction:column;gap:2px}
 .ray__row{display:flex;align-items:center;gap:12px;padding:13px 16px;border:1px solid #242728}
 .ray__row span{font-size:13px;color:#cdcdcd;flex:1}
 .ray__row code{font-family:'IBM Plex Mono',monospace;font-size:11px;color:#5c5a56}
 .ray__row--on{background:#121212;border-color:#3a3d3e}
 .ray__row--on span{color:#f4f4f6}
 kbd{font-family:'IBM Plex Mono',monospace;font-size:10px;height:20px;line-height:20px;padding:0 7px;
   background:linear-gradient(#121212,#0d0d0d);border:1px solid #242728;border-radius:3px;color:#cdcdcd}
 .ray__leg{font-family:'IBM Plex Mono',monospace;font-size:10px;color:#6f6d68;margin-top:12px}""",
 "Escada de superfície: cada degrau mais claro lê como um passo mais próximo. E o <b>keycap inline de 20px</b> — ensina o atalho no ponto de uso sem roubar espaço.",
 "O coral da marca. Saturação ali fica confinada a logo e badge; o chrome é monocromático — é isso que mantém legível uma tela de 200 linhas.",
 "raycast.com"),

("03","Warp","estética · acento único",
 "Terminal agentic. Um fósforo violeta sobre preto fosco, e nada mais colorido na interface.",
 """<div class=wrp>
   <div class=wrp__l><span class=wrp__p>◆</span> agent.plan()</div>
   <div class=wrp__l><span class=wrp__d>›</span> analisando 4 arquivos</div>
   <div class=wrp__l><span class=wrp__p>◆</span> tool: <b>read_file</b></div>
   <div class=wrp__l><span class=wrp__d>›</span> 2 edições propostas</div>
   <div class=wrp__btn>Aplicar</div>
   <div class=wrp__leg>o acento NÃO vai no botão de ação — só em ícone, código e link</div>
 </div>""",
 """.wrp{width:76%;font-family:'IBM Plex Mono',monospace;font-size:13px;line-height:2}
 .wrp__l{color:#faf9f6}
 .wrp__p{color:#cbb0f7}
 .wrp__d{color:#5c5a56}
 .wrp__l b{color:#cbb0f7;font-weight:500}
 .wrp__btn{display:inline-block;margin-top:16px;background:#e6e6e6;color:#454647;
   font-family:Inter,sans-serif;font-size:12px;font-weight:600;padding:7px 18px;border-radius:3px}
 .wrp__leg{margin-top:18px;font-size:10px;color:#6f6d68;letter-spacing:.04em}""",
 "Um acento cromático em toda a interface, e proibido no botão de ação. Texto primário em off-white <b>quente</b> (#faf9f6), não branco puro — tira a dureza clínica.",
 "Gradientes e imagem de fundo (que eles adicionaram para customização). Em painel denso, fundo com gradiente destrói qualquer sparkline sobreposta.",
 "warp.dev"),

("04","Modal","estética · racionamento",
 "Compute serverless para IA. A regra de cor mais disciplinada que encontramos.",
 """<div class=mdl>
   <div class=mdl__grid>
     <i></i><i></i><i></i><i class=on></i><i></i><i></i><i></i><i></i>
     <i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i>
   </div>
   <p class=mdl__t>o verde aparece como preenchimento em <b>exatamente um</b> elemento por viewport</p>
   <p class=mdl__b>corpo de texto em verde dessaturado (#8cab87), nunca no verde de sinal</p>
 </div>""",
 """.mdl{width:74%;text-align:left}
 .mdl__grid{display:grid;grid-template-columns:repeat(8,1fr);gap:6px;margin-bottom:22px}
 .mdl__grid i{height:30px;background:#141a13;border:1px solid #485346;display:block}
 .mdl__grid i.on{background:#7fee64;border-color:#7fee64;box-shadow:0 0 18px rgba(127,238,100,.35)}
 .mdl__t{font-size:14px;color:#8cab87;line-height:1.6}
 .mdl__t b{color:#7fee64}
 .mdl__b{font-family:'IBM Plex Mono',monospace;font-size:10px;color:#6f6d68;margin-top:10px}""",
 "Racionar o sinal: uma cor de estado tratada como LED, não como pintura. É o que falta em 90% dos dashboards — todo mundo colore tudo e nada mais chama atenção.",
 "Verde-sobre-preto como identidade. Sozinho, é literalmente o clichê de IA. O que salva aqui é a <em>disciplina</em>, não a cor.",
 "modal.com"),

("05","Gitness","estética · ao contrário",
 "Plataforma de CI/CD que faz duas coisas invertidas — e as duas funcionam.",
 """<div class=gts>
   <div class=gts__c><b>PIPELINE</b><span>borda clara sobre canvas quase preto</span></div>
   <div class=gts__c><b>BUILD</b><span>parece painel serigrafado, não card flutuante</span></div>
   <div class=gts__d>T R A C K I N G &nbsp; P O S I T I V O</div>
 </div>""",
 """.gts{width:80%;display:flex;flex-direction:column;gap:14px;align-items:center}
 .gts__c{width:100%;border:1px solid #d9dae5;background:#070707;padding:16px 18px}
 .gts__c b{display:block;font-size:12px;letter-spacing:.14em;color:#70dcd3}
 .gts__c span{font-size:12px;color:#8e8b84}
 .gts__d{margin-top:8px;font-size:22px;font-weight:700;letter-spacing:.056em;color:#e8e6e1}""",
 "Bordas <b>claras</b> de 1px definindo cards sobre canvas quase preto — o oposto do padrão. E tracking positivo no display, em todos os tamanhos: rótulo de painel de controle, não headline de SaaS.",
 "Duas cores de acento na mesma superfície. A regra deles: mint e azul nunca coexistem — e é o que impede virar arco-íris.",
 "gitness.com"),

("06","Oxide Computer","estética · quatro canais",
 "Identidade construída pela Pentagram a partir de TUI, CLI e ASCII art. A saída mais inteligente do clichê mono-acento.",
 """<div class=oxd>
   <div class=oxd__r><i style="background:#48d597"></i><span>operational</span><code>rack-01</code></div>
   <div class=oxd__r><i style="background:#f5b944"></i><span>degraded</span><code>rack-04</code></div>
   <div class=oxd__r><i style="background:#e86886"></i><span>faulted</span><code>rack-07</code></div>
   <div class=oxd__r><i style="background:#4969f6"></i><span>updating</span><code>rack-09</code></div>
   <div class=oxd__a>▚▚▚ ░░▒▒▓▓ ▚▚▚ ░░▒▒▓▓ ▚▚▚ ░░▒▒▓▓ ▚▚▚</div>
 </div>""",
 """.oxd{width:76%;font-family:'IBM Plex Mono',monospace}
 .oxd__r{display:flex;align-items:center;gap:14px;padding:10px 0;border-bottom:1px solid #26262a}
 .oxd__r i{width:9px;height:9px;display:block;flex:0 0 auto}
 .oxd__r span{font-size:12px;color:#b9b6b0;flex:1;letter-spacing:.05em}
 .oxd__r code{font-size:11px;color:#5c5a56}
 .oxd__a{margin-top:18px;font-size:13px;color:#2f4a3d;letter-spacing:.1em;line-height:1.3}""",
 "<b>Quatro cores funcionais</b> sobre preto em vez de um acento só — é assim que se escapa do clichê mantendo o look. Textura de grid derivada de ASCII. E mono para <em>dado</em>, não para código.",
 "O verde isolado. Se roubar só o verde-sobre-preto você caiu exatamente no default. O que funciona é o conjunto de quatro + a textura.",
 "oxide.computer"),

("07","Vercel Geist","sistema · malha",
 "O grid é descrito na própria doc como parte central da estética — não como utilitário.",
 """<div class=gst>
   <div class=gst__box><b>painel sólido</b><span>oclui a malha que cruza por baixo</span></div>
   <div class=gst__box2></div>
 </div>""",
 """.palco{background:
   repeating-linear-gradient(to right,rgba(232,230,225,.09) 0 1px,transparent 1px 38px),
   repeating-linear-gradient(to bottom,rgba(232,230,225,.09) 0 1px,transparent 1px 38px),#141416 !important}
 .gst{width:78%;display:flex;gap:0;align-items:stretch;height:60%}
 .gst__box{flex:2;background:#1c1c1f;border:1px solid #3e3e44;padding:20px 22px;
   display:flex;flex-direction:column;justify-content:center}
 .gst__box b{font-size:16px;display:block;margin-bottom:4px}
 .gst__box span{font-size:12px;color:#8e8b84}
 .gst__box2{flex:1;border:1px dashed #3e3e44}""",
 "Malha de 1px permanentemente visível, e células sólidas <b>ocluem</b> as guias que as cruzam. Papel milimetrado técnico onde os cards recortam a malha em vez de flutuar sobre ela.",
 "A paleta neutra sozinha. Geist é chassi excelente e <em>invisível</em> — a direção visual tem que vir de outro lugar.",
 "vercel.com/geist/grid"),

("08","Grafana","dashboard · stat row",
 "O produto de monitoramento em produção. A linha de stat panels no topo é o padrão que virou consenso.",
 """<div class=grf>
   <div class=grf__s><svg viewBox="0 0 100 40" preserveAspectRatio=none><path d="M0 34 L16 30 L32 33 L48 20 L64 24 L80 10 L100 6" fill=none stroke="#73bf69" stroke-width=2/><path d="M0 34 L16 30 L32 33 L48 20 L64 24 L80 10 L100 6 L100 40 L0 40Z" fill="rgba(115,191,105,.14)"/></svg>
     <b style="color:#73bf69">98.4%</b><span>UPTIME</span></div>
   <div class=grf__s><svg viewBox="0 0 100 40" preserveAspectRatio=none><path d="M0 20 L16 18 L32 26 L48 22 L64 30 L80 28 L100 34" fill=none stroke="#ff9830" stroke-width=2/><path d="M0 20 L16 18 L32 26 L48 22 L64 30 L80 28 L100 34 L100 40 L0 40Z" fill="rgba(255,152,48,.14)"/></svg>
     <b style="color:#ff9830">412ms</b><span>P95</span></div>
   <div class=grf__s><svg viewBox="0 0 100 40" preserveAspectRatio=none><path d="M0 36 L20 35 L40 30 L60 32 L80 18 L100 12" fill=none stroke="#f2495c" stroke-width=2/><path d="M0 36 L20 35 L40 30 L60 32 L80 18 L100 12 L100 40 L0 40Z" fill="rgba(242,73,92,.14)"/></svg>
     <b style="color:#f2495c">17</b><span>ERROS/MIN</span></div>
 </div>""",
 """.grf{display:flex;gap:1px;width:88%;background:#26262a}
 .grf__s{flex:1;background:#141416;padding:18px 18px 14px;position:relative;overflow:hidden;height:130px}
 .grf__s svg{position:absolute;inset:auto 0 0 0;height:52px;width:100%;opacity:.85}
 .grf__s b{position:relative;font-family:'IBM Plex Mono',monospace;font-size:32px;
   font-weight:600;letter-spacing:-.03em;display:block;font-variant-numeric:tabular-nums}
 .grf__s span{position:relative;font-family:'IBM Plex Mono',monospace;font-size:9.5px;
   letter-spacing:.16em;color:#8e8b84;display:block;margin-top:6px}""",
 "Sparkline <b>atrás</b> do número, com preenchimento de área — e o número herda a cor do limiar em vez de ganhar um badge ao lado. Um elemento faz o trabalho de três.",
 "A cauda longa de painéis abaixo. A stat row funciona porque é curta: 3 a 6. Acima disso ninguém lê nada.",
 "play.grafana.org"),

("09","Cal.com · OpenStatus","dashboard · barra de execuções",
 "O widget mais reaproveitável do gênero status page. Troque “dia” por “sessão do agente”.",
 """<div class=cal>
   <div class=cal__h><span>últimas 45 execuções</span><b>98.4%</b></div>
   <div class=cal__b id=bars></div>
   <div class=cal__f><span>45 sessões atrás</span><span>agora</span></div>
 </div>""",
 """.cal{width:82%}
 .cal__h{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px}
 .cal__h span{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.14em;
   text-transform:uppercase;color:#8e8b84}
 .cal__h b{font-family:'IBM Plex Mono',monospace;font-size:18px;color:#48d597}
 .cal__b{display:flex;gap:3px;height:46px}
 .cal__b i{flex:1;border-radius:2px;display:block;height:100%}
 .cal__f{display:flex;justify-content:space-between;margin-top:9px}
 .cal__f span{font-family:'IBM Plex Mono',monospace;font-size:9px;color:#5c5a56}""",
 "45 a 90 barras finas, gap de 2–3px, altura fixa, cor sólida por estado. O histórico inteiro numa faixa de 46px — mais informativo que qualquer número isolado.",
 "Tooltip como única forma de ler o detalhe. Em relatório estático que se lê de longe, o valor tem que estar na forma, não no hover.",
 "status.cal.com · themes.openstatus.dev"),

("10","OpenRouter","dashboard · frescor",
 "Leaderboard ao vivo. A gramática de “vivo” sem uma única animação.",
 """<div class=orr>
   <div class=orr__stamp>dados até 21 ago 2026, 14:02 · atualiza a cada 5min</div>
   <div class=orr__row><span class=orr__i>01</span><b>claude-opus</b><code>482B</code><em class=up>+7%</em></div>
   <div class=orr__row><span class=orr__i>02</span><b>gpt-5.2</b><code>371B</code><em class=up>+103%</em><i>NOVO</i></div>
   <div class=orr__row><span class=orr__i>03</span><b>gemini-3-pro</b><code>298B</code><em class=dn>−4%</em></div>
 </div>""",
 """.orr{width:78%;font-family:'IBM Plex Mono',monospace}
 .orr__stamp{font-size:10px;color:#8e8b84;letter-spacing:.05em;padding-bottom:12px;
   border-bottom:1px solid #26262a;margin-bottom:6px}
 .orr__row{display:flex;align-items:baseline;gap:14px;padding:11px 0;border-bottom:1px solid #1e1e21}
 .orr__i{font-size:10px;color:#5c5a56}
 .orr__row b{flex:1;font-family:Inter,sans-serif;font-size:14px;font-weight:600}
 .orr__row code{font-size:13px;color:#b9b6b0;font-variant-numeric:tabular-nums}
 .orr__row em{font-style:normal;font-size:11px;width:52px;text-align:right}
 .up{color:#48d597}.dn{color:#e08a7c}
 .orr__row i{font-style:normal;font-size:8.5px;letter-spacing:.14em;color:#0e0e10;
   background:#48d597;padding:2px 5px;border-radius:2px}""",
 "Carimbo de frescor explícito + <b>delta percentual em cada linha</b> + label “novo”. É o que faz a página parecer viva sem mover um pixel. Monitoramento sem sinal de recência mente por omissão.",
 "O top-5 em card grande. Serve pra leaderboard público; num painel operacional a tabela densa desde a linha 1 é melhor.",
 "openrouter.ai/rankings"),

("11","Langfuse","agente · dois modos",
 "O melhor que existe hoje para desenhar execução de agente. Resolve a tensão central do problema.",
 """<div class=lgf>
   <div class=lgf__col><div class=lgf__t>AGREGADO — a arquitetura</div>
     <div class=lgf__n>plan</div><div class=lgf__a>↓</div>
     <div class="lgf__n lgf__n--loop">retrieve_docs <b>(3/3)</b> ↻</div><div class=lgf__a>↓</div>
     <div class=lgf__n>synthesize</div></div>
   <div class=lgf__col><div class=lgf__t>EXPANDIDO — a execução</div>
     <div class=lgf__n>plan</div><div class=lgf__a>↓</div>
     <div class=lgf__n>retrieve_docs #1</div><div class=lgf__a>↓</div>
     <div class=lgf__n>retrieve_docs #2</div><div class=lgf__a>↓</div>
     <div class=lgf__n>retrieve_docs #3</div><div class=lgf__a>↓</div>
     <div class=lgf__n>synthesize</div></div>
 </div>""",
 """.lgf{display:flex;gap:56px;width:82%;justify-content:center}
 .lgf__col{display:flex;flex-direction:column;align-items:center;gap:0}
 .lgf__t{font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:.16em;
   color:#8e8b84;margin-bottom:14px}
 .lgf__n{font-family:'IBM Plex Mono',monospace;font-size:11px;background:#1c1c1f;
   border:1px solid #3e3e44;padding:7px 14px;white-space:nowrap}
 .lgf__n--loop{border-color:#5fd18f;color:#5fd18f}
 .lgf__n b{color:#e8e6e1}
 .lgf__a{color:#3e3e44;font-size:11px;line-height:1.6}""",
 "Dois modos sobre o <b>mesmo</b> run, com métricas iguais nos dois. Agregado: passos de mesmo nome colapsam com contador e loop vira ciclo. Expandido: um nó por chamada. Um agente que fez 40 chamadas não pode virar lista de 40 linhas.",
 "Grafo como única leitura. Quando fica grande, a saída é um log linear com Ctrl+F — eles mesmos construíram isso depois.",
 "langfuse.com/docs/observability/features/agent-graphs"),

("12","Braintrust","agente · span tipado",
 "Árvore à esquerda, detalhe à direita. O mecanismo mais reaproveitável da pesquisa inteira.",
 """<div class=brt>
   <div class=brt__c><span class=brt__k style="color:#8cc0dd">LLM</span>
     <div class=brt__f><i>modelo</i><b>opus-4.5</b></div>
     <div class=brt__f><i>tokens</i><b>1.204 / 380</b></div>
     <div class=brt__f><i>TTFT</i><b>340ms</b></div>
     <div class=brt__f><i>duração</i><b>2.1s</b></div></div>
   <div class=brt__c><span class=brt__k style="color:#d9b467">SCORING</span>
     <div class=brt__f><i>score</i><b style="color:#5fd18f">0.82</b></div>
     <div class=brt__why>“cobre os 3 critérios mas cita só 1 fonte primária”</div></div>
 </div>""",
 """.brt{display:flex;gap:20px;width:84%}
 .brt__c{flex:1;background:#1c1c1f;border:1px solid #3e3e44;padding:16px 18px}
 .brt__k{font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:.16em;
   display:block;margin-bottom:12px}
 .brt__f{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #26262a}
 .brt__f i{font-style:normal;font-size:11px;color:#8e8b84}
 .brt__f b{font-family:'IBM Plex Mono',monospace;font-size:11.5px}
 .brt__why{margin-top:12px;font-size:11.5px;line-height:1.5;color:#b9b6b0;font-style:italic}""",
 "Tipar o span e deixar o <b>tipo mudar o template do detalhe</b>. LLM mostra tokens e time-to-first-token; scoring mostra o score <em>e o raciocínio do juiz</em>. Número sem justificativa é ruído.",
 "Renderizar tudo com o mesmo card genérico “chave: valor”. É o que quase todo painel faz, e é o que apaga a diferença entre os tipos.",
 "braintrust.dev/foundations/how-to-read-a-trace"),

("13","Honeycomb BubbleUp","dashboard · seleção × baseline",
 "Você seleciona o anômalo e o sistema diz o que ele tem de diferente. Único mecanismo que responde “o que os caminhos ruins têm em comum”.",
 """<div class=hny>
   <div class=hny__t>execuções que falharam <b>vs.</b> todo o resto</div>
   <div class=hny__r><span>tool: web_search</span><div class=hny__bars><i class=sel style="width:81%"></i><i class=base style="width:4%"></i></div><code>81% / 4%</code></div>
   <div class=hny__r><span>contexto &gt; 80%</span><div class=hny__bars><i class=sel style="width:64%"></i><i class=base style="width:11%"></i></div><code>64% / 11%</code></div>
   <div class=hny__r><span>modelo: haiku</span><div class=hny__bars><i class=sel style="width:22%"></i><i class=base style="width:19%"></i></div><code>22% / 19%</code></div>
   <div class=hny__leg><i class=sel></i> seleção &nbsp;&nbsp; <i class=base></i> baseline &nbsp;·&nbsp; ordenado pela diferença</div>
 </div>""",
 """.hny{width:84%;font-family:Inter,sans-serif}
 .hny__t{font-size:13px;color:#b9b6b0;margin-bottom:16px}
 .hny__t b{color:#e8e6e1}
 .hny__r{display:flex;align-items:center;gap:14px;padding:8px 0}
 .hny__r span{font-family:'IBM Plex Mono',monospace;font-size:11px;width:130px;color:#b9b6b0}
 .hny__bars{flex:1;display:flex;flex-direction:column;gap:3px}
 .hny__bars i{height:9px;display:block;min-width:2px}
 .sel{background:#e8c547}.base{background:#4a7fb5}
 .hny__r code{font-family:'IBM Plex Mono',monospace;font-size:10px;color:#8e8b84;width:64px;text-align:right}
 .hny__leg{margin-top:16px;font-size:10px;color:#6f6d68;display:flex;align-items:center;gap:6px}
 .hny__leg i{width:14px;height:8px;display:inline-block}""",
 "Duas barras sobrepostas — amarelo é a sua seleção, azul é todo o resto — ordenadas pela diferença. Convenção de duas cores que não depende de escala sequencial nem de legenda.",
 "Aplicar sem volume. Com 20 execuções a comparação é ruído estatístico; o mecanismo só ganha sentido a partir de algumas centenas.",
 "docs.honeycomb.io/reference/honeycomb-ui/query/query-results"),

("14","Blade Runner 2049 · Territory","FUI · dois sistemas",
 "Screen graphics feitos sob a diretriz “imagine um mundo onde a tecnologia digital não existe mais”.",
 """<div class=br9>
   <div class=br9__c br9--old><div class=br9__k>LAPD — legado</div>
     <div class=br9__v>0.8241<span class=ghost>0.8241</span></div>
     <div class=br9__d>ghosting, degradação de cor</div></div>
   <div class=br9__c><div class=br9__k>WALLACE — síntese</div>
     <div class=br9__v>0.8241</div>
     <div class=br9__d>puro, mínimo, geométrico</div></div>
 </div>""",
 """.br9{display:flex;gap:26px;width:82%}
 .br9__c{flex:1;padding:22px;border:1px solid #3e3e44;background:#141416}
 .br9--old{background:#12100c;border-color:#4a4030}
 .br9__k{font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:.18em;
   color:#8e8b84;margin-bottom:16px}
 .br9__v{font-family:'IBM Plex Mono',monospace;font-size:38px;letter-spacing:-.02em;position:relative;
   font-variant-numeric:tabular-nums}
 .br9--old .br9__v{color:#d8c9a3}
 .ghost{position:absolute;left:1.5px;top:1.2px;color:rgba(216,201,163,.28)}
 .br9__d{font-size:11px;color:#6f6d68;margin-top:14px}""",
 "A bifurcação de dois sistemas dentro do mesmo produto — <em>dado bruto/legado</em> vs <em>síntese/controle</em>, com tratamentos opostos. E o ghosting como marcador semântico de <b>dado defasado</b>, em vez de um badge cinza.",
 "As texturas orgânicas e as lentes ópticas. É set design: custa GPU e destrói densidade. O preto-e-branco geométrico é o que escala.",
 "territorystudio.com/project/blade-runner-2049"),

("15","Oblivion · GMUNK","FUI · restrição",
 "Sistema gráfico completo do filme. Duas restrições declaradas, ambas aplicáveis.",
 """<div class=obl>
   <div class=obl__half style="background:#f2f0ea;color:#14140f">
     <b>1 4 . 2 °</b><span>a mesma paleta sobre claro</span></div>
   <div class=obl__half style="background:#0a0d10;color:#e8f4f8">
     <b>1 4 . 2 °</b><span>e sobre escuro</span></div>
   <div class=obl__leg>acentos escolhidos por <b>luminância estável</b>, não por contraste contra o preto</div>
 </div>""",
 """.obl{width:80%;position:relative}
 .obl__half{display:inline-block;width:50%;padding:34px 26px;vertical-align:top;text-align:center}
 .obl__half b{font-family:'IBM Plex Mono',monospace;font-size:26px;display:block;
   letter-spacing:.08em;color:#3aa5c9}
 .obl__half span{font-size:11px;opacity:.6;display:block;margin-top:10px}
 .obl__leg{margin-top:22px;font-size:11.5px;color:#8e8b84;text-align:center}
 .obl__leg b{color:#b9b6b0}""",
 "“Uma paleta que funcionasse igualmente bem sobre fundo escuro <b>ou</b> claro” — é exatamente a fuga do clichê preto+neon, e resolve claro/escuro de graça. Mais: “funcionalidade acima do excesso, mantendo o greeble sob controle”.",
 "O método FUI inteiro. Todo FUI é otimizado para um plano de 3 segundos, não para 8 horas de plantão. Use a linguagem, nunca o método.",
 "gmunk.com/OBLIVION-GFX"),

("16","Monaspace","tipografia · texture healing",
 "Superfamília de cinco monoespaçadas com métricas compartilhadas, do GitHub Next.",
 """<div class=mns>
   <div class=mns__r><span class=mns__l>sem healing</span><code class=bad>illiminating&nbsp;mwm&nbsp;9f3a11</code></div>
   <div class=mns__r><span class=mns__l>com healing</span><code class=good>illiminating&nbsp;mwm&nbsp;9f3a11</code></div>
   <div class=mns__leg>glifos estreitos (i, l, j) cedem espaço; largos (m, w) alargam — <b>sem quebrar o grid mono</b></div>
 </div>""",
 """.mns{width:80%}
 .mns__r{display:flex;align-items:center;gap:20px;padding:14px 0;border-bottom:1px solid #26262a}
 .mns__l{font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:.14em;
   color:#8e8b84;width:110px}
 .mns__r code{font-family:'IBM Plex Mono',monospace;font-size:20px;letter-spacing:0}
 .bad{opacity:.55;letter-spacing:.06em}
 .good{color:#e8e6e1}
 .mns__leg{margin-top:18px;font-size:11.5px;color:#8e8b84;line-height:1.6}
 .mns__leg b{color:#b9b6b0}""",
 "<b>Texture healing</b> via alternates contextuais: iguala a densidade visual sem sair do mono. Colunas de ID e hash param de parecer manchadas. E as cinco famílias têm métricas idênticas — dá pra misturar na mesma tabela.",
 "As ligaduras de código. Em dashboard, <code>!=</code> virando um glifo único destrói a leitura caractere a caractere que você precisa em log e ID.",
 "monaspace.githubnext.com"),

("17","Recursive","tipografia · eixo MONO",
 "Variável de cinco eixos, com um que quase nenhuma outra fonte tem.",
 """<div class=rcs>
   <div class=rcs__s style="letter-spacing:-.01em">MONO 0.0 — proporcional</div>
   <div class=rcs__s style="letter-spacing:.02em">MONO 0.5 — semi</div>
   <div class=rcs__s style="letter-spacing:.06em;font-family:'IBM Plex Mono',monospace">MONO 1.0 — monoespaçado</div>
   <div class=rcs__leg>largura <b>idêntica</b> em Sans e Mono, independente de peso e slant<br>
   → animar peso/mono em hover com <b>zero layout shift</b></div>
 </div>""",
 """.rcs{width:78%}
 .rcs__s{font-size:21px;padding:11px 0;border-bottom:1px solid #26262a;color:#e8e6e1}
 .rcs__leg{margin-top:20px;font-size:11.5px;color:#8e8b84;line-height:1.7}
 .rcs__leg b{color:#5fd18f}""",
 "O eixo <b>MONO (0→1)</b> interpola continuamente entre proporcional e monoespaçado. Com CASL 0 (“bordas achatadas, otimizado para informação densa”), é direção tipográfica futurista que não é mais uma grotesca neutra.",
 "CASL 1 e o eixo cursivo. Formas de pincel em dado operacional destroem a autoridade da leitura.",
 "recursive.design"),

("18","Halftone & dither em CSS","textura · valor sem gradiente",
 "Meio-tom e dithering ordenado feitos em CSS puro, sem canvas e sem shader.",
 """<div class=hlf>
   <div class=hlf__c><div class=hlf__d style="--s:3px"></div><span>medido</span></div>
   <div class=hlf__c><div class=hlf__d style="--s:5px;opacity:.75"></div><span>estimado</span></div>
   <div class=hlf__c><div class=hlf__d style="--s:8px;opacity:.5"></div><span>sem dado</span></div>
   <div class=hlf__leg>densidade de ponto <b>é</b> o valor — funciona em monocromático,<br>
   resolve daltonismo de graça, e dither vira a forma honesta de mostrar incerteza</div>
 </div>""",
 """.hlf{width:80%;text-align:center}
 .hlf__c{display:inline-block;width:30%;margin:0 1%}
 .hlf__d{height:96px;border:1px solid #3e3e44;
   background-image:radial-gradient(circle at center, #5fd18f 42%, transparent 44%);
   background-size:var(--s) var(--s)}
 .hlf__c span{display:block;margin-top:9px;font-family:'IBM Plex Mono',monospace;
   font-size:10px;letter-spacing:.12em;color:#8e8b84}
 .hlf__leg{margin-top:24px;font-size:11.5px;color:#8e8b84;line-height:1.7}
 .hlf__leg b{color:#b9b6b0}""",
 "Densidade de ponto como codificação de valor, e <b>dither para marcar incerteza</b>: série medida sólida, série estimada pontilhada. O olho lê a diferença sem legenda.",
 "O pacote CRT completo (curvatura, scanline, máscara de sombra) e o <code>contrast(999)</code> sobre área grande — caro e força repaint. Pegue Bayer e quantização, deixe a curvatura.",
 "leanrada.com/notes/pure-css-halftone"),
]

FONTES = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
          '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
          'family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">')

idx = []
for n, nome, tipo, oque, demo, demo_css, roubar, nao, url in SPECS:
    slug = f"{n}_{nome.lower().replace(' · ','-').replace(' ','-').replace('·','-')}"
    slug = "".join(c for c in slug if c.isalnum() or c in "-_")
    pagina = f"""<!doctype html><html lang=pt-BR><head><meta charset=utf-8>{FONTES}
<style>{CSS_BASE}{demo_css}</style></head><body>
<div class=cab><span class=n>{H.escape(n)}</span><span class=nome>{H.escape(nome)}</span>
<span class=tipo>{H.escape(tipo)}</span></div>
<p class=oque>{oque}</p>
<div class=palco><span class=url>{H.escape(url)}</span>{demo}</div>
<div class=rodape>
  <div class=rod><div class="rot s">roubar</div><p>{roubar}</p></div>
  <div class=rod><div class="rot n">não roubar</div><p>{nao}</p></div>
</div></body></html>"""
    (SAIDA / f"{slug}.html").write_text(pagina, encoding="utf-8")
    idx.append({"n": n, "nome": nome, "tipo": tipo, "slug": slug, "url": url,
                "oque": oque, "roubar": roubar, "nao": nao})

json.dump(idx, open(SAIDA / "indice.json", "w"), ensure_ascii=False, indent=2)
print(f"{len(idx)} specimens em {SAIDA}")
