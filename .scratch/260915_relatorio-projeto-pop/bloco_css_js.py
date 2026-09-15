# --------------------------------------------------------------------------
# CSS / JS — marca POP v1.2 (motor/modelos/relatorios/PADRAO.md, 260915)
# --------------------------------------------------------------------------
# Padrão único de relatório: fundo escuro #101014 com auroras violeta/azul
# fixas, glow no topo, cartões de vidro raio 10px, h1 display 800 com halo,
# estados menta/azul/âmbar/coral SEMPRE com glifo além da cor, números
# tabulares. Tokens iguais aos da pele legado (260914_pop/260915_pele-pop-
# legado.css), então a pele que os wrappers ainda injetam por cima não briga.
# Strings em raw (r"") porque o CSS usa escapes próprios (\A, \2713) — em
# string Python normal "\A" é escape inválido (SyntaxWarning).
# `tema` só escolhe o layout (pílulas ou trilho lateral); a pele é uma só.

def css(tema: str = "padrao") -> str:
    base = r"""
:root{--bg:#101014;--surf:rgb(255 255 255/.055);--surf2:rgb(255 255 255/.035);
  --edge:rgb(255 255 255/.08);--edge2:rgb(255 255 255/.14);
  --ink:#eceef4;--ink2:#b9bdc9;--ink3:#8f94a3;--hi:#f5f6fb;
  --ok:#7fc79c;--info:#8cc0dd;--warn:#d9b467;--bad:#e39288;
  --acc:#8cc0dd;--acc-dim:rgb(140 192 221/.14);--violeta:124 92 255;--r:10px;
  --m:ui-monospace,"Cascadia Mono","SF Mono",Consolas,monospace;
  --s:"Segoe UI",system-ui,-apple-system,sans-serif;
  --vidro:blur(14px) saturate(1.25)}
*{box-sizing:border-box;margin:0}
html{scroll-behavior:smooth}
body{min-height:100vh;padding:0;color:var(--ink);font:16px/1.6 var(--s);font-variant-numeric:tabular-nums;
  -webkit-font-smoothing:antialiased;overflow-x:hidden;
  background:radial-gradient(70rem 24rem at 50% -8rem,rgb(var(--violeta)/.42),transparent 70%),
    radial-gradient(60vw 55vh at 100% 0%,rgb(var(--violeta)/.5),transparent 70%),
    radial-gradient(55vw 50vh at 0% 100%,rgb(56 150 255/.35),transparent 70%),var(--bg);
  background-attachment:fixed}
/* glow no topo: filete de luz fixo */
body::before{content:"";position:fixed;z-index:70;inset:0 0 auto;height:2px;pointer-events:none;
  background:linear-gradient(90deg,transparent,rgb(140 192 221/.85) 30%,rgb(var(--violeta)/.95) 70%,transparent);
  box-shadow:0 0 22px 3px rgb(var(--violeta)/.55)}
.wrap{max-width:1180px;margin:0 auto;padding:3.2rem clamp(1rem,3vw,2rem) 5rem}

/* cabeçalho ---------------------------------------------------------- */
.wrap>h1{max-width:22ch;margin:0 0 .5rem;color:var(--hi);font:800 clamp(2.1rem,4.4vw,3.6rem)/1 var(--s);
  letter-spacing:-.04em;text-shadow:0 0 32px rgb(56 150 255/.35),0 0 2px rgb(140 192 221/.25)}
.sub{margin:0 0 1.6rem;color:var(--ink3);font-family:var(--m);font-size:.68rem;letter-spacing:.13em;text-transform:uppercase}

/* vidro -------------------------------------------------------------- */
.tldr,.hero-acao,section,table,details,.card-ai,.di,footer,.versao-mb{background:var(--surf);
  border:1px solid var(--edge2);border-radius:var(--r);box-shadow:0 10px 30px rgb(0 0 0/.25);
  -webkit-backdrop-filter:var(--vidro);backdrop-filter:var(--vidro);color:var(--ink)}

/* TL;DR — estado com glifo, nunca só cor ----------------------------- */
.tldr{margin:0 0 1.2rem;padding:1.1rem 1.35rem;border-left:4px solid var(--ok);
  font-size:clamp(1rem,1.35vw,1.14rem);line-height:1.5;color:var(--ink)}
.tldr::before{content:"\2713";display:inline-grid;place-items:center;width:1.5em;height:1.5em;margin-right:.6em;
  border-radius:50%;background:var(--ok);color:var(--bg);font-weight:800;font-size:.85em;vertical-align:.1em}
.tldr.atencao{border-left-color:var(--warn)} .tldr.atencao::before{content:"\25B2";background:var(--warn);border-radius:3px}
.tldr.ruim{border-left-color:var(--bad)} .tldr.ruim::before{content:"\2715";background:var(--bad);border-radius:3px}

/* ação imediata — o painel mais forte, com glow no topo --------------- */
.hero-acao{position:relative;margin:0 0 2rem;padding:1.3rem 1.5rem 1.5rem;border-top:1px solid rgb(140 192 221/.55);
  background:linear-gradient(180deg,rgb(var(--violeta)/.14),var(--surf) 60%);
  box-shadow:0 -1px 0 rgb(140 192 221/.55),0 -18px 40px -12px rgb(var(--violeta)/.55),0 12px 34px rgb(0 0 0/.3)}
.hero-acao h2{margin:0 0 .2rem;color:var(--info);font:700 .72rem/1.3 var(--m);letter-spacing:.15em;text-transform:uppercase}
.hero-acao h2::before{content:none}
.hero-acao .section-file{margin:0;color:var(--ink3)}
.hero-acao ol{counter-reset:acao;list-style:none;margin:1rem 0 0;padding:0}
.hero-acao ol>li{counter-increment:acao;position:relative;padding:.62rem 0 .62rem 2.6rem;color:var(--ink);
  border-bottom:1px solid var(--edge);font-size:1rem;line-height:1.45}
.hero-acao ol>li:last-child{border-bottom:0}
.hero-acao ol>li::before{content:counter(acao);position:absolute;left:0;top:.55rem;width:1.7rem;height:1.7rem;
  display:flex;align-items:center;justify-content:center;border-radius:8px;border:1px solid rgb(140 192 221/.5);
  background:var(--acc-dim);color:var(--info);font:700 .75rem var(--m)}
.hero-acao p{color:var(--ink2)} .hero-acao strong{color:var(--hi)}
.acoes-rapidas{display:flex;gap:8px;flex-wrap:wrap;margin-top:1.1rem}
.acao-btn,.cp{display:inline-flex;align-items:center;gap:.4rem;border-radius:var(--r);border:1px solid rgb(140 192 221/.5);
  background:rgb(140 192 221/.12);color:var(--info);font-family:var(--m);font-weight:700;letter-spacing:.08em;
  text-transform:uppercase;text-decoration:none;cursor:pointer;
  transition:transform .15s ease,background .15s ease,box-shadow .15s ease}
.acao-btn{min-height:2.3rem;padding:.4rem .95rem;font-size:.66rem}
.acao-btn::before{content:"\2197";font-size:.9em}
.acao-btn[href^="#"]::before{content:"\2193"}
.cp{padding:.28rem .7rem;margin-left:10px;font-size:.6rem}
.cp::before{content:"\29C9"}
.acao-btn:hover,.cp:hover{transform:translateY(-1px);background:rgb(140 192 221/.22);color:var(--hi);
  border-color:var(--info);box-shadow:0 6px 16px rgb(56 150 255/.25);text-decoration:none}
.acao-btn:active,.cp:active{transform:translateY(1px);box-shadow:none}

/* navegação (layout padrão: pílulas grudadas no topo) ----------------- */
nav{position:sticky;top:0;z-index:40;display:flex;gap:6px;flex-wrap:wrap;margin:0 0 12px;padding:10px 12px;
  background:rgb(16 16 20/.62);border:1px solid var(--edge2);border-radius:var(--r);
  -webkit-backdrop-filter:var(--vidro);backdrop-filter:var(--vidro)}
nav a{display:inline-flex;align-items:center;gap:.35rem;padding:6px 12px;border:1px solid var(--edge);border-radius:var(--r);
  color:var(--ink2);font:.66rem/1.2 var(--m);letter-spacing:.08em;text-transform:uppercase;text-decoration:none;
  transition:transform .15s ease,background .15s ease}
nav a::before{content:"\00B7";color:var(--ink3)}
nav a:hover{color:var(--hi);background:rgb(255 255 255/.07);border-color:var(--edge2);transform:translateY(-1px);text-decoration:none}
nav a:hover::before{content:"\203A";color:var(--info)}

/* seções -------------------------------------------------------------- */
section{margin:0 0 12px;padding:1.4rem 1.55rem;scroll-margin-top:4rem}
h2{margin:0 0 .9rem;color:var(--hi);font:800 clamp(1.15rem,2vw,1.55rem)/1.2 var(--s);letter-spacing:-.03em;scroll-margin-top:4rem}
section>h2:first-child::before{content:"\25A0";margin-right:.5rem;color:var(--info);font-size:.6em;vertical-align:.25em}
h3{margin:1.6rem 0 .55rem;padding-top:.85rem;border-top:1px solid var(--edge);color:var(--info);font-size:1.1rem;font-weight:700;letter-spacing:-.015em}
section>h3:first-of-type{margin-top:.5rem;padding-top:0;border-top:0}
h4{margin:1.4rem 0 .45rem;color:var(--ink);font-size:1.02rem;font-weight:700}
h5{margin:1.1rem 0 .3rem;color:var(--info);font-family:var(--m);font-size:.7rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase}
h6{margin:.9rem 0 .25rem;color:var(--ink3);font-size:.82rem;font-weight:600}
p{margin:8px 0;color:var(--ink2)}
ul,ol{margin:8px 0 8px 20px;color:var(--ink2)} li{margin:4px 0;color:var(--ink2)}
strong,b{color:var(--ink)}
a{color:var(--info);text-underline-offset:.18em} a:hover{color:#bfe0f2}
.section-file{margin:-.55rem 0 1rem;color:var(--ink3);font-family:var(--m);font-size:.64rem}

/* tabelas ------------------------------------------------------------- */
.tbl-wrap{overflow-x:auto}
table{width:100%;border-collapse:separate;border-spacing:0;overflow:hidden;margin:10px 0;background:var(--surf2);box-shadow:none}
th{text-align:left;vertical-align:top;padding:.7rem .9rem;border-bottom:1px solid var(--edge2);color:var(--ink3);
  font-family:var(--m);font-size:.62rem;font-weight:500;letter-spacing:.11em;text-transform:uppercase}
td{vertical-align:top;padding:.7rem .9rem;border-bottom:1px solid var(--edge);color:var(--ink2);font-size:.93rem}
tr:last-child td,tr:last-child th{border-bottom:0}

/* checklists e pendências: glifo + cor -------------------------------- */
ul.chk{list-style:none;margin-left:0}
ul.chk li{display:flex;gap:8px;align-items:flex-start}
ul.chk .mk,.pend .mk{font-family:var(--m);font-weight:700}
ul.chk li.open .mk,.pend .mk{color:var(--warn)}
ul.chk li.done{color:var(--ink3);text-decoration:line-through}
ul.chk li.done .mk,details .pend .mk{color:var(--ok)}
.pend{display:flex;gap:10px;align-items:flex-start;padding:9px 0;border-bottom:1px solid var(--edge)}
.pend:last-child{border-bottom:0}
.pend .src{font-family:var(--m);font-size:.62rem;color:var(--ink3);white-space:nowrap}

/* blocos diversos ------------------------------------------------------ */
blockquote{margin:10px 0;padding:4px 14px;border-left:3px solid rgb(var(--violeta)/.55);color:var(--ink3)}
code{font-family:var(--m);font-size:.84em;padding:.1em .38em;border-radius:5px;background:rgb(140 192 221/.12);color:var(--info)}
pre{margin:.6rem 0;padding:.8rem 1rem;overflow:auto;border:1px solid var(--edge);border-radius:var(--r);background:rgb(0 0 0/.28);color:var(--ink2)}
pre code{background:transparent;padding:0}
del{color:var(--ink3);text-decoration-color:var(--bad)}
hr{border:0;border-top:1px solid var(--edge);margin:18px 0}
.card-ai{margin:10px 0;padding:1rem 1.3rem;border-left:3px solid var(--info);color:var(--ink2)}
.card-ai>p:first-child::before{content:"\24D8  ";color:var(--info);font-weight:800}
.di{padding:.2rem 1.1rem} .di div{padding:14px 0;border-bottom:1px solid var(--edge)} .di div:last-child{border-bottom:0}
details{margin:10px 0;padding:0 1.1rem;background:var(--surf2);box-shadow:none}
summary{padding:.8rem 0;cursor:pointer;list-style:none;color:var(--info);font-family:var(--m);font-size:.66rem;
  font-weight:700;letter-spacing:.1em;text-transform:uppercase}
summary::-webkit-details-marker{display:none}
summary::before{content:"\25B8  "} details[open]>summary::before{content:"\25BE  "}
footer{margin-top:1.5rem;padding:1.4rem 1.55rem;color:var(--ink3);font-size:.88rem;line-height:1.7}
footer p{color:var(--ink3)}
:focus-visible{outline:3px solid rgb(var(--violeta));outline-offset:2px;border-radius:6px}

/* toast: todo clique responde ----------------------------------------- */
#toasts{position:fixed;z-index:100;bottom:1.1rem;left:50%;transform:translateX(-50%);display:flex;flex-direction:column;
  gap:.45rem;align-items:center;max-width:min(92vw,34rem);pointer-events:none}
.toast{display:flex;align-items:center;gap:.55rem;padding:.62rem 1rem;border-radius:var(--r);border:1px solid var(--ok);
  background:rgb(22 22 30/.92);color:var(--hi);font-size:.86rem;font-weight:600;box-shadow:0 12px 34px rgb(0 0 0/.55);
  -webkit-backdrop-filter:var(--vidro);backdrop-filter:var(--vidro)}
.toast .t-ico{flex:0 0 auto;color:var(--ok)}
.toast.err{border-color:var(--bad)} .toast.err .t-ico{color:var(--bad)}
.toast small{display:block;color:var(--ink3);font-weight:500;word-break:break-all}
.toast.saindo{opacity:0;transform:translateY(8px);transition:opacity .25s ease,transform .25s ease}

@media(max-width:62rem){.wrap>h1{max-width:none;font-size:clamp(1.9rem,8vw,2.8rem)}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}
  html{scroll-behavior:auto}}
@media print{
  :root{--bg:#fff;--surf:#fff;--surf2:#fff;--edge:#ccc;--edge2:#999;--ink:#000;--ink2:#333;--ink3:#666;--hi:#000;
    --info:#06626f;--acc:#06626f;--acc-dim:#eef6f8}
  body{background:#fff} body::before,nav,#toasts{display:none}
  .wrap>h1{text-shadow:none}
  .tldr,.hero-acao,section,table,details,.card-ai,.di,footer,.versao-mb{box-shadow:none;backdrop-filter:none;-webkit-backdrop-filter:none}
  section,footer,.hero-acao,.tldr,table,.di,details{break-inside:avoid}
}
"""
    if tema == "megabrain":
        return base + css_megabrain()
    if tema == "console":
        return base + css_console()
    return base


def _css_trilho(topo: str, rodape: str) -> str:
    """Layout de trilho lateral fixo (temas console e megabrain).

    `topo`/`rodape` são o texto do trilho em sintaxe de `content` CSS — já
    escapados (\\A = quebra de linha), por isso a montagem aqui é em raw.
    """
    return r"""
/* trilho lateral --------------------------------------------------------- */
.wrap{max-width:none;min-height:100svh;margin:0 0 0 15.5rem;padding:3.6rem clamp(1.1rem,3.4vw,3.2rem) 5rem}
.wrap>*:not(nav){max-width:76rem}
nav{position:fixed;z-index:40;inset:0 auto 0 0;flex-direction:column;flex-wrap:nowrap;gap:2px;width:15.5rem;
  margin:0;padding:6.2rem .8rem 1.2rem;border:0;border-right:1px solid var(--edge2);border-radius:0;overflow-y:auto;
  background:rgb(16 16 20/.62)}
nav::before{content:"__TOPO__";position:absolute;inset:1.5rem 1.1rem auto;padding-bottom:1.1rem;
  border-bottom:1px solid var(--edge2);white-space:pre-line;color:var(--hi);font:800 1rem/1.25 var(--s);letter-spacing:-.02em}
nav::after{content:"__RODAPE__";margin-top:auto;padding-top:1.3rem;border-top:1px solid var(--edge);
  white-space:pre-line;color:var(--ink3);font:.6rem/1.6 var(--m)}
nav a{display:grid;grid-template-columns:1.15rem 1fr;min-height:2.3rem;padding:0 .5rem;border-color:transparent;
  letter-spacing:.07em;text-transform:none;font-size:.7rem}
@media(max-width:62rem){
  .wrap{margin:0;padding:4.6rem 1rem 3rem}
  nav{inset:0 0 auto;flex-direction:row;width:100%;height:3.5rem;padding:.5rem .6rem;border-right:0;
    border-bottom:1px solid var(--edge2);overflow-x:auto;overflow-y:hidden}
  nav::before,nav::after{display:none}
  nav a{display:flex;min-width:max-content;padding:0 .65rem}
}
""".replace("__TOPO__", topo).replace("__RODAPE__", rodape)


def css_console() -> str:
    """Trilho do tema console (padrão do modo legado desde 260824)."""
    return _css_trilho(r"megabrain\A relatório vivo", r"fonte: markdown do projeto\A o HTML nunca se edita")


def css_megabrain() -> str:
    """Trilho do tema megabrain (opt-in; usado pelo relatório do Currículo)."""
    return _css_trilho(r"CURRÍCULO\A Acompanhamento do projeto", r"Local · relatório vivo\A Fontes Markdown consolidadas")


def js() -> str:
    # Convenção POP: data-copia (clipboard com fallback + toast), data-diz
    # (toast), <a> real navega E avisa. Toast monta nó com textContent —
    # conteúdo do gerador nunca vira HTML.
    return r"""
var fila=document.getElementById('toasts');
function toast(msg,sub,err){
  if(!fila)return;
  var t=document.createElement('div');t.className='toast'+(err?' err':'');
  var ico=document.createElement('span');ico.className='t-ico';ico.textContent=err?'⚠':'✓';
  var box=document.createElement('span');box.textContent=msg;
  if(sub){var s=document.createElement('small');s.textContent=sub;box.appendChild(s);}
  t.appendChild(ico);t.appendChild(box);fila.appendChild(t);
  while(fila.children.length>3)fila.removeChild(fila.firstChild);
  setTimeout(function(){t.classList.add('saindo');setTimeout(function(){t.remove();},280);},3400);
}
function fallback(txt){
  var ta=document.createElement('textarea');ta.value=txt;ta.setAttribute('readonly','');
  ta.style.position='fixed';ta.style.opacity='0';document.body.appendChild(ta);ta.select();
  var ok=false;try{ok=document.execCommand('copy');}catch(e){}
  ta.remove();return ok;
}
function copia(txt,diz,btn){
  var origem=document.activeElement;
  var feito=function(ok){
    toast(ok?(diz||'Copiado'):'Não deu pra copiar',ok?txt:'copia na mão: '+txt,!ok);
    if(ok&&btn&&btn.tagName==='BUTTON'){var o=btn.textContent;btn.textContent='copiado ✓';
      setTimeout(function(){btn.textContent=o;},1400);}
    if(origem&&origem.focus){try{origem.focus({preventScroll:true});}catch(e){}}
  };
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(txt).then(function(){feito(true);},function(){feito(fallback(txt));});
  }else{feito(fallback(txt));}
}
/* compatibilidade: HTML antigo chamava cp(this,'caminho') e copiava entre aspas */
function cp(btn,t){copia('"'+t+'"','Caminho copiado',btn);}
document.addEventListener('click',function(e){
  var c=e.target.closest('[data-copia]');
  if(c){e.preventDefault();copia(c.getAttribute('data-copia'),c.getAttribute('data-diz'),c);return;}
  var d=e.target.closest('[data-diz]');
  if(d){toast(d.getAttribute('data-diz'));return;}
  var a=e.target.closest('a[href]');
  if(a){var h=a.getAttribute('href');
    if(h.charAt(0)==='#'){toast('Indo para: '+(a.textContent.trim()||h));}
    else{toast('Abrindo: '+(a.textContent.trim()||h),h);}}
});
document.addEventListener('keydown',function(e){
  if(e.key!=='Enter'&&e.key!==' ')return;
  var t=e.target.closest?e.target.closest('[role="button"]'):null;
  if(t&&t.tagName!=='BUTTON'&&t.tagName!=='A'&&t.tagName!=='SUMMARY'){e.preventDefault();t.click();}
});
document.querySelectorAll('details').forEach(function(det){det.addEventListener('toggle',function(){
  var s=det.querySelector('summary');toast((det.open?'Aberto: ':'Fechado: ')+(s?s.textContent.trim():''));
});});
"""


