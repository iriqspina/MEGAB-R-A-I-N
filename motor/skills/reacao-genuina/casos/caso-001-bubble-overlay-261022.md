# Caso 001 · Bubble — card do modo assistir clicável + bolhas (261022)

**Skill:** reacao-genuina v1 · **Projeto:** <PROJETOS_ROOT>/Bubble ·
**Estado:** proposta entregue, aguardando decisão do <USUARIO>.

## Contexto

Overlay flutuante (modo assistir, picture-in-picture) que fica sobre outras
abas durante a chamada. Print real do estado atual: pílula escura com
"Papo geral · 2 pessoas · 1:27:46" + botões de microfone e câmera à esquerda do
centro, botão azul escrito "Voltar pra sala" no miolo e botão vermelho de
desconexão na ponta direita. Correção do modo assistir (share-vozes) já no
disco, aguardando publicação — as mudanças deste caso são planejamento, sem
código ainda.

## Diagnóstico pela skill (checklist)

1. **Primeiro instante:** o que salta é o botão azul com texto — o estímulo
   mais forte pede leitura, não ação.
2. **Custo de leitura:** 1 frase obrigatória ("Voltar pra sala") para executar
   a ação principal do overlay.
3. **Alvo:** área de clique útil ≈ o botão de texto (~15% do card); resto do
   corpo é morto.
4. **Descoberta:** sem hover no corpo; só o botão diz "clicável" (por rótulo).
5. **Estado por imagem:** n/a neste card (bolhas são a extensão proposta).
6. **Retração:** n/a hoje — participantes invisíveis fora da sala.
7. **Varredura curta:** 3 zonas de botão + texto; tolerável, mas mira exigida.
8. **Legibilidade:** ok (sem transparência).
9. **Nada quebrou:** n/a (proposta, não aplicada).

## Proposta

- Remover o botão "Voltar pra sala"; **o corpo do card vira o botão** de voltar.
- Mic e câmera movidos para a direita, alinhados ao lado do botão de
  desconexão; 100% funcionais.
- Mesmo comprimento no eixo X (footprint preservado); **centro livre** para
  clicar sem mirar.
- **Hover** na área livre (fora dos botões): o card "acorda" ao sentir o
  ponteiro — ensina clicável sem texto.
- 3 propostas visuais coesas com bolhas + planejamento de bolhas retráteis dos
  participantes (câmera→vídeo na bolha; tela→perfil+tela; ambos→os dois; nada→
  foto de perfil; tela mais quadrática mas com sentimento de bolha; **sem
  transparência**; botão de retração com estilo novo, diferente dos controles
  existentes).

## Métricas (previsto, antes → depois)

| métrica | antes | depois (previsto) |
|---|---|---|
| frases obrigatórias para ação principal | 1 | 0 |
| área de alvo da ação principal (% do card) | ~15% (botão) | ~70% (corpo fora dos controles) |
| feedback pré-clique no alvo | não (só rótulo) | hover no corpo |
| estados visuais por imagem (participantes) | 0 | 4 regras (câm/tela/ambos/perfil) |

## Reação humana

PENDENTE — decisões respondíveis no relatório da tarefa (qual proposta A/B/C,
aprovar overlay-clicável + hover, estilo do botão retrátil, janela de
implementação).

## Lições candidatas (para validar na rodada)

- Remover rótulo e ampliar alvo é a jogada padrão quando a ação principal é
  única e o contêiner é pequeno (P2+P3 juntas).
- Alinhar controles num só bloco (direita) libera o centro como zona de clique
  sem mira — preservar footprint evita regressão de layout.

## Prova

- Print real do estado atual:
  `Bubble/00_PARA-VOCE/10_Design-thinking/img/261022_card-atual.png`
- Relatório com propostas e decisões:
  `Bubble/00_PARA-VOCE/10_Design-thinking/261022_REACAO-GENUINA-OVERLAY.html`
- Pedido literal: `memoria/cerebro/raw/261022_pedido-skill-reacao-genuina.md`
