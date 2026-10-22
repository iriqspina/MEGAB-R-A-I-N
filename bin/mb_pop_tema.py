# -*- coding: utf-8 -*-
"""Tema claro do POP v1.2 — fonte única compartilhada pelos geradores.

O template (motor/modelos/relatorios/260914_pop/relatorio-pop.html) carrega
uma cópia embutida destas definições (contrato: arquivo único offline).
motor/tests/test_mb_relatorio_pop_tema.py confere os tokens-chave nos dois
lugares pra impedir divergência.
"""
from __future__ import annotations

CHAVE_TEMA = "megabrain.pop.tema"

# CSS do tema claro + do botão de alternância. Vai por ÚLTIMO no <style>,
# depois do CSS base do esqueleto.
CSS_TEMA = """
  /* ═══ TEMA CLARO (opção do padrão único · escuro é o default) ═══
     Ativado por html[data-tema="claro"]. Paleta clara própria — não é filtro:
     acentos VIVOS nos gráficos (bordas, ícones, dots, barras, botões — mesmo
     jeitão do escuro) e versão escura -tx só onde a cor vira TEXTO. */
  html[data-tema="claro"]{
    --fundo:#F5F3EE; --fundo2:#EAE7E0; --card:#FFFFFF; --card2:#F5F3EE;
    --tinta:#191923; --corpo:#454552; --fraco:#5E5E6E;
    --linha:rgba(25,25,35,.14); --line:rgba(25,25,35,.20);
    --coral:#FF4B4B; --verde:#58CC02; --azul:#1CB0F6; --amarelo:#FFC800; --roxo:#CE82FF; --rosa:#FF82C4;
    --coral-tx:#AD2838; --verde-tx:#216B42; --azul-tx:#185ABD; --amarelo-tx:#805000; --roxo-tx:#6236A5; --rosa-tx:#96356D;
    --sombra-card:0 10px 30px rgba(25,25,35,.14);
  }
  html[data-tema="claro"] body::before{
    background:
      radial-gradient(58rem 30rem at 50% -12%, rgba(124,58,237,.26) 0%, transparent 65%),
      radial-gradient(34rem 20rem at 82% 6%, rgba(236,72,153,.16) 0%, transparent 60%),
      radial-gradient(30rem 18rem at 8% 12%, rgba(28,176,246,.12) 0%, transparent 60%),
      linear-gradient(180deg, #FFFFFF 0%, var(--fundo) 40%);}
  html[data-tema="claro"] .hero h1{color:var(--tinta)}
  @supports ((-webkit-background-clip:text) or (background-clip:text)){
    html[data-tema="claro"] .hero h1{background:linear-gradient(180deg,#191923 30%,#7C3AED 88%);
      -webkit-background-clip:text;background-clip:text;color:transparent;
      filter:drop-shadow(0 6px 22px rgba(124,58,237,.35))}
  }
  /* textos coloridos usam a versão escura (-tx) pra contraste AA */
  html[data-tema="claro"] .pill{background:rgba(206,130,255,.14);border-color:rgba(124,58,237,.45);color:var(--roxo-tx)}
  html[data-tema="claro"] .hero .sub b{color:var(--verde-tx)}
  html[data-tema="claro"] .gates-leg b{color:var(--amarelo-tx)}
  html[data-tema="claro"] .gate--ok b{color:var(--verde-tx)}
  html[data-tema="claro"] .gate--trava b{color:var(--amarelo-tx)}
  html[data-tema="claro"] .run--ok .q{color:var(--verde-tx)}
  html[data-tema="claro"] .run--warn .q{color:var(--amarelo-tx)}
  html[data-tema="claro"] .cota--ok .ritmo{color:var(--verde-tx)}
  html[data-tema="claro"] .cota--warn .ritmo{color:var(--amarelo-tx)}
  html[data-tema="claro"] .papel b{color:var(--roxo-tx)}
  html[data-tema="claro"] .sk b{color:var(--azul-tx)}
  html[data-tema="claro"] .it .num{color:var(--roxo-tx)}
  html[data-tema="claro"] .fig figcaption b{color:var(--azul-tx)}
  html[data-tema="claro"] .acao .n{color:color-mix(in oklab,var(--c) 62%,#14141F)}
  html[data-tema="claro"] td[style*="--verde"]{color:var(--verde-tx)}
  html[data-tema="claro"] td[style*="--coral"]{color:var(--coral-tx)}
  html[data-tema="claro"] .anelzinho svg circle:nth-of-type(2){stroke:#E39B00}
  html[data-tema="claro"] .anelzinho svg circle:first-of-type{stroke:rgba(25,25,35,.14)}
  html[data-tema="claro"] .btn{color:#fff;text-shadow:0 1px 2px rgba(20,20,31,.28)}
  html[data-tema="claro"] .share i{color:#fff;text-shadow:0 1px 2px rgba(20,20,31,.3)}
  html[data-tema="claro"] .spark .bar{box-shadow:0 0 12px rgba(28,176,246,.35)}
  html[data-tema="claro"] .toast{box-shadow:0 10px 26px rgba(25,25,35,.22)}
  /* botão do tema (header) */
  .tema-linha{display:flex;align-items:center;gap:.6rem;margin:0 0 .4rem}
  .tema-btn{display:inline-flex;align-items:center;gap:.45rem;padding:.4rem .85rem;border-radius:99px;cursor:pointer;
    background:var(--card2);border:1px solid var(--linha);color:var(--tinta);font:700 .74rem var(--mono);
    transition:transform .08s ease}
  .tema-btn:hover{border-color:var(--roxo)}
  .tema-btn:active{transform:translateY(2px)}
  .tema-btn:focus-visible{outline:3px solid var(--roxo);outline-offset:2px}
  .tema-btn:disabled{opacity:.55;cursor:not-allowed}
  .tema-btn .lua{display:none}
  html[data-tema="claro"] .tema-btn .lua{display:inline}
  html[data-tema="claro"] .tema-btn .sol{display:none}
  .tema-status{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
"""

# Script síncrono no <head>, antes do <style>: restaura a preferência antes da
# primeira pintura. Precedência: preferência salva válida → tema inicial → escuro.
JS_TEMA_HEAD = """\
<script>
/* restauração de tema: síncrono, antes da primeira pintura.
   precedência: preferência salva válida → tema inicial do arquivo → escuro */
(function(){
  try{
    var t = localStorage.getItem('megabrain.pop.tema');
    if (t === 'claro' || t === 'escuro') document.documentElement.setAttribute('data-tema', t);
  }catch(e){}
})();
</script>"""

# Botão + região de status. Nasce visível e desabilitado; o script síncrono
# logo abaixo habilita. Sem JS, fica desabilitado com a explicação do noscript.
HTML_TEMA_CONTROLE = """\
<div class="tema-linha">
        <button type="button" id="btn-tema" class="tema-btn" aria-pressed="false" disabled>
          <span class="sol" aria-hidden="true">☀️</span><span class="lua" aria-hidden="true">🌙</span>
          <span id="btn-tema-txt">Tema: escuro</span>
        </button>
        <span id="tema-status" role="status" class="tema-status"></span>
        <noscript><small style="color:var(--fraco)">alternância de tema precisa de JavaScript — o relatório segue legível no tema gerado</small></noscript>
      </div>
      <script>
      /* controle do tema: síncrono, imediatamente após o botão. Enter/Espaço nativos do <button>. */
      (function(){
        var btn = document.getElementById('btn-tema');
        var txt = document.getElementById('btn-tema-txt');
        var st  = document.getElementById('tema-status');
        function temaAtual(){ return document.documentElement.getAttribute('data-tema') === 'claro' ? 'claro' : 'escuro'; }
        function sincroniza(){
          var claro = temaAtual() === 'claro';
          btn.setAttribute('aria-pressed', claro ? 'true' : 'false');
          txt.textContent = 'Tema: ' + (claro ? 'claro' : 'escuro');
        }
        sincroniza();
        btn.disabled = false;
        btn.addEventListener('click', function(){
          var proximo = temaAtual() === 'claro' ? 'escuro' : 'claro';
          document.documentElement.setAttribute('data-tema', proximo);
          sincroniza();
          var salvo = false;
          try { localStorage.setItem('megabrain.pop.tema', proximo); salvo = true; } catch(e){}
          st.textContent = 'Tema ' + proximo + ' ativado' + (salvo ? '. Preferência salva.'
            : ' nesta página. Não foi possível salvar a preferência.');
        });
      })();
      </script>"""


# ═══ INTERAÇÕES OBRIGATÓRIAS (261010) ═══
# Pedido do <USUARIO> (Portfólio, 10/10/2026): "lembre-se disso como elemento necessário
# principal e recrie para os relatórios megabrain dos projetos". Todo relatório POP sai com
# as Ferramentas do cursor (segurar 0,4 s parado → menu em leque → Comentar; era 2 s até 261017). Relatório que pede
# decisão usa também motor/modelos/interacoes/261010_decisoes-respondiveis/.
# Fonte única do componente: motor/modelos/interacoes/261010_cursor-ferramentas/ na central,
# MEGABRAIN/modelos/interacoes/... na cópia do projeto. Sem o arquivo, nada é inserido.
MARCA_INTERACOES_INICIO = "<!-- mb-interacoes:inicio -->"
MARCA_INTERACOES_FIM = "<!-- mb-interacoes:fim -->"


def _js_componente(nome_pasta: str, arquivo: str) -> str:
    from pathlib import Path as _P
    aqui = _P(__file__).resolve().parent
    for base in (aqui.parent / "motor" / "modelos", aqui.parent / "modelos"):
        alvo = base / "interacoes" / nome_pasta / arquivo
        if alvo.is_file():
            codigo = alvo.read_text(encoding="utf-8")
            if "</script" in codigo.lower():
                return ""
            return codigo
    return ""


def html_interacoes() -> str:
    """Bloco pronto (com marcas) das Ferramentas do cursor para colar antes de </body>."""
    codigo = _js_componente("261010_cursor-ferramentas", "cursor-ferramentas.js")
    if not codigo:
        return ""
    visual_css = _js_componente("261011_agrupamento-visual", "agrupamento.css")
    visual_js = _js_componente("261011_agrupamento-visual", "agrupamento.js")
    visual = ('<style id="mb-agrupamento-estilo">' + visual_css + '</style>\n'
              '<script id="mb-agrupamento-script">' + visual_js + '</script>\n') if visual_css and visual_js else ''
    return (MARCA_INTERACOES_INICIO + '\n' + visual + '<script id="cf-script">' + codigo + "</script>\n"
            "<script>try{if(window.CursorFerramentas&&!window.__mbCF){window.__mbCF="
            "CursorFerramentas.iniciar({modo:'auto'});}}catch(e){}</script>\n" + MARCA_INTERACOES_FIM)


def aplicar_interacoes(html_texto: str) -> tuple[str, str]:
    """Insere ou atualiza o bloco. Devolve (html, 'inserido'|'atualizado'|'igual'|'sem-componente')."""
    bloco = html_interacoes()
    if not bloco:
        return html_texto, "sem-componente"
    i = html_texto.find(MARCA_INTERACOES_INICIO)
    if i >= 0:
        j = html_texto.find(MARCA_INTERACOES_FIM, i)
        if j >= 0:
            j += len(MARCA_INTERACOES_FIM)
            if html_texto[i:j] == bloco:
                return html_texto, "igual"
            return html_texto[:i] + bloco + html_texto[j:], "atualizado"
    k = html_texto.lower().rfind("</body>")
    if k < 0:
        return html_texto + "\n" + bloco + "\n", "inserido"
    return html_texto[:k] + bloco + "\n" + html_texto[k:], "inserido"
