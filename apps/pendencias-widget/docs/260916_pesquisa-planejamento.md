# Pesquisa de planejamento — `/pendencias` (skill MEGABRAIN + widget de desktop)

260916 · v1 · Fonte de verdade desta pesquisa: medição real feita nesta sessão
(29 pastas em `C:/Projetos`, 17 com `ESTADO.md`+`HANDOFF.md` na raiz,
amostras de Marketeiro/Portfolio/Rato de Olho/Pets lidas, arquitetura dos
widgets Cotas IA e Agentes IA inspecionada). Segunda opinião: conta gpt2
("astra", default + high) despachada em paralelo — anexada ao final quando
voltar.

## 1. Interpretação do pedido

O dono quer um **radar de pendências** sempre visível: um widget discreto na
tela que resume, por projeto, o que está pendente nos projetos da pasta que ele
escolher — hoje `C:/Projetos` — alimentado pelo protocolo que já
existe (ESTADO.md/HANDOFF.md por projeto), e controlável por conversa via skill
`/pendencias` em qualquer IA. "Colocar e tirar" = pausar projeto parado (some
do widget sem perder histórico) e adicionar/remover pendências manualmente.
É produto final para ele e instalável para qualquer usuário que aceite o
widget MEGABRAIN.

## 2. O que uma "pendência" é (modelo de dados)

Medição: os ESTADO.md são heterogêneos — pendências aparecem como "TL;DR"
estado atual, linha "Próximo passo:", "Gate seguinte:", "PENDENTE" ou
"PAUSADO por logout". Parsear tudo é frágil; ignorar tudo desperdiça o que os
agentes já escrevem.

**Decisão: híbrido com registro central como fonte da verdade.**

1. **Item automático por projeto** ("auto"): o scanner extrai do ESTADO.md o
   `resumo` (linha TL;DR) e, se existir, o `proximo_passo` (primeira linha que
   casa `próximo passo|gate seguinte|pendente` — case-insensitive). Idade do
   item = mtime do ESTADO.md. Não vira "feito" nunca sozinho; se o dono
   dispensar (`--dispensar`), só volta quando o hash do ESTADO.md mudar
   (conteúdo novo = pendência nova legítima).
2. **Itens manuais** ("manual"): criados por conversa via skill ou CLI, com
   título, detalhe opcional e data. São os "colocar e tirar" que ele pediu.
3. **Projeto**: nome, caminho, `ativo: true|false` (pausado some do widget,
   fica no registro), `pausado_sugerido` (auto-detecção de "PAUSADO/não
   retomar" no ESTADO.md → o widget sugere pausar, não pausa sozinho).

Contrato do arquivo `dados/pendencias.json` (central, lido pelo widget e
escrito só pelo CLI — escrita única evita a classe de bug das 2 instâncias do
Cotas brigando pelo arquivo):

```json
{
  "versao": 1,
  "raiz": "C:/Projetos",
  "projetos": [
    {
      "nome": "Marketeiro",
      "caminho": "C:/Projetos\\Marketeiro",
      "ativo": true,
      "resumo": "método de qualificação e lote 1 prontos para crítica...",
      "proximo_passo": null,
      "estado_hash": "sha1 do ESTADO.md",
      "estado_mtime": "2026-09-15T04:15:00",
      "pausado_sugerido": false,
      "itens": [
        {"id": "260916-1930-a1b2", "origem": "manual", "titulo": "Crítica das 5 fichas do lote 1",
         "detalhe": null, "criada_em": "2026-09-16T19:30:00", "estado": "aberta",
         "dispensada_em": null}
      ]
    }
  ]
}
```

## 3. UX — jornadas do usuário final

**J1 · Abertura da manhã (5s):** olha o pill na tela → "7 pendências · 5
projetos" → clica → vê grupos por projeto, cada grupo com 1 item auto
(próximo passo real, com idade) + itens manuais. Sem ação, o widget nunca
toca no mouse dele nem rouba foco.

**J2 · Agir numa pendência:** duplo-clique no item → abre a pasta do projeto
no Explorer (a ação mais reversível e universal; abrir ESTADO.md direto no
editor padrão é o segundo clique — item exposto em menu de contexto v1.1).

**J3 · Pausar projeto parado (o pedido explícito):** hover no grupo do
projeto → botão ⏸ "pausar projeto" → grupo some com fade, contagem do pill
atualiza no mesmo instante. Um rodapé discreto "pausados: 3" clicável abre a
lista de pausados com botão ▶ retomar em cada. Nada é apagado: `ativo:false`
no registro.

**J4 · Adicionar/remover pendência conversando (qualquer IA):** "add
pendência no Marketeiro: mandar proposta pra Hanada" → a IA roda
`python bin/mb-pendencias.py add Marketeiro "mandar proposta pra Hanada"` →
próxima leitura do widget (poll 60s ou ⟳) mostra. Remover/feito idem. A skill
documenta os comandos; o script é a garantia (roteamento oficial megabrain:
skill = pedido, script = garantia).

**J5 · Instalar em outra pasta:** settings do widget tem campo `raiz`
editável pelas Configurações (v1.1) e `bin/mb-pendencias.py raiz <caminho>`
na v1 — escanear outra pasta de projetos é um comando, sem código novo.

**Estados do widget:** vazio total ("Nada pendente" + hora); tudo pausado
(pill esmaecido + "retome por /pendencias"); >20 itens (lista rola dentro do
card, pill mostra total real; densidade nunca estica o card além de 60% da
altura da tela).

**"Sutil" operacionalizado:** parado e recolhido, o widget é um pill de
~34px de altura que não pisca, não notifica e não cresce sozinho; só muda
quando os dados mudam. Cor de texto neutra; número de pendências com peso,
o resto esmaecido. Alerta visual só por idade (item auto >7 dias vira âmbar)
— urgência implícita, sem gamificação.

## 4. UI — anatomia visual (herdada do Cotas IA, medida nos irmãos)

- **Forma recolhida (pill):** fundo carvão opacidade 76%, raio 14px (tokens
  irmãos), altura ~34px, conteúdo "◷ 7 pendências · 5 projetos" — glifo de
  pilha/relógio + número em 13px semibold + resto em 12px cinza claro.
- **Forma expandida (card):** largura ~320px, lista de grupos; cabeçalho
  arrastável (DragHeader do irmão) com título "Pendências", contagem e
  botões ⟳ (atualizar) e ▾/▴ (recolher). Grupo = nome do projeto em caps
  10px esmaecido + badge de contagem + ⏸ no hover; itens = bullet de status
  (verde nova / âmbar >7d / cinza dispensável), título 12px truncado a 1
  linha com tooltip completo, idade "3d" à direita.
- **Paleta:** mesma do Cotas IA — carvão #14161c, texto claro, status
  #7cc48f/#e0b46a/#a2a8b1 (theme.py irmão), Segoe UI. Sem cor nova na v1.
- **Comportamento:** FramelessWindowHint | WindowStaysOnTopHint | Tool (fora
  da taskbar), `WA_ShowWithoutActivation` (não rouba foco ao abrir — regra
  do desktop I.A.), singleton QLocalServer (chave própria), posição/opacidade
  /expandido persistidos em settings.json próprio, re-clamp nos limites do
  monitor ao mostrar.
- **Prova:** modo `--screenshot` (padrão irmão) grava PNG para verificação
  visual sem abrir mão do boot real; lançamento de teste nasce no desktop
  I.A. com stderr redirecionado (regra 260916: queda sem log é debug às cegas).

## 5. Arquitetura

```
apps/pendencias-widget/
  widget.py                 entry (args: --demo --screenshot --expanded --raiz)
  pendencias_core/
    paths.py                dirs + REGISTRY_PATH (dados/pendencias.json central)
    registro.py             load/save atômico + CRUD + pausar/retomar/dispensar
    scanner.py              scan da raiz: detecta projetos, extrai resumo/
                            próximo passo/pausado_sugerido, preserva manual
    persistence.py          settings.json do widget (posição, opacidade, escala)
    single_instance.py      guard (chave pendencias-widget-260916)
    theme.py                tokens visuais (herdado do irmão, subconjunto)
    ui_card.py              MainWindow: pill ↔ card, grupos, hover actions
  tests/                    test_registro.py, test_scanner.py (unittest puro)
  INSTALAR-E-ABRIR.cmd      1 clique: atalho + abre (padrão irmão)
  launch.vbs                pythonw sem console (venv do Cotas IA, como Agentes IA)
  README.md
bin/mb-pendencias.py        CLI fino (sys.path → pendencias_core): scan | listar |
                            add | rm | feito | dispensar | pausar | retomar | raiz
motor/skills/pendencias/SKILL.md   fonte da skill (→ cópia idêntica em ~/.zcode/skills)
00_PARA-VOCE/260916_widget-pendencias/   entrega humana
```

Reuso direto dos padrões irmãos: venv PySide6 do Cotas IA (nada novo a
instalar), launch.vbs do Agentes IA, DragHeader/singletons/screenshot do
Cotas IA, tema carvão. Novo de verdade: registro+scanner (core puro, testável
sem Qt) e ui_card.

## 6. Critérios de estado final (v1)

1. `python bin/mb-pendencias.py scan` na raiz real termina escrevendo
   `dados/pendencias.json` válido com os 17+ projetos detectados (json.load ok).
2. `listar` mostra grupos com itens auto+manual; `add/rm/feito/dispensar/
   pausar/retomar/raiz` alteram o registro e o widget reflete na leitura
   seguinte (poll ou ⟳) — sem reiniciar.
3. Widget com `--screenshot` grava PNG com pill e card renderizados (prova).
4. `python -m unittest discover -s apps/pendencias-widget/tests` verde.
5. Skill instalada em `~/.zcode/skills/pendencias/SKILL.md` com md5 igual à
   fonte em `motor/skills/`.
6. Lançado no desktop I.A. via script com stderr redirecionado; log 0 byte
   após 10s = boot limpo.
7. Nenhuma escrita fora de `dados/pendencias.json`, settings do próprio app e
   pasta de entrega.

## 7. Riscos top 5 (com mitigação)

1. **Parser frágil de ESTADO.md heterogêneo** → item auto é só
   resumo+primeira linha de próximo passo; falha de parse = campo null, nunca
   item inventado; tudo manual por cima do auto.
2. **Duas fontes escrevendo o registro** (CLI de duas sessões) → escrita
   atômica (tmp+replace) e CLI curto; conflito real é raro (operações
   humanas, não loop).
3. **Widget vira ruído** (TDAH) → nada anima sem mudança de dado; expansão
   só por clique; pausados fora da vista.
4. **Pasta raiz com projeto não-MEGABRAIN** (flux, mimde etc.) → critério de
   projeto = tem ESTADO.md ou MEGABRAIN/; os outros são ignorados e listados
   uma vez como "não-projetos" no `scan -v`.
5. **Custo de manutenção de mais um widget** → core puro sem Qt (testável),
   UI fina, venv/tema/launcher compartilhados com irmãos; nenhuma dependência
   nova.
