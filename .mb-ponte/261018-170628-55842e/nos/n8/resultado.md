# Resultado do nó n8 — revisão GLM do mapa corrigido pelo GPT

TL;DR — **APROVADO.** Mapa corrigido pelo n4 conferido: 20/20 testes de motor rodados por mim, hashes fonte/candidato conferidos, HTML entregue validado (regenerado às 17:36:12 pela fonte do n4 + cursor atual do n3, condição prevista). Sem problema concreto que exija ajuste; 4 notas não bloqueantes registradas. Produto não editado.

## Veredito e provas

1. **APROVADO** — revisão completa em `evidence/261018_ponte-orquestradores/revisao-mapa-glm.md`.
2. **Testes reais rodados por mim** (não só lidos): `python -m unittest motor.tests.test_mb_harness_mapa` → 20/20 OK; `python bin/mb-harness-mapa.py --validar` → "Planta válida" (exit 0).
3. **Hashes conferidos 2×** (17:35 e após 45 s, estáveis): gerador `506f2fbc…`, mapa.js `e071e0e3…`, mapa.css `17a969b9…`, LEIAME `bb49bb4d…`, testes `6fe6ec95…` — todos iguais aos reportados pelo n4. HTML final `806e45b6…` (247.120 B) = mapa do n4 (`2d2e05fb…`, 247.099 B) + cursor atualizado do n3 (+21 bytes exatos em ambos).
4. **HTML entregue revalidado**: cursor e Ferramentas embutidos, `window.HARNESS` sem `<` cru, zero rede externa, `base_id 4179a8bd5b1b`, 52 estações/8 linhas, COMEÇA/CHEGA AQUI, régua de paradas, rascunho `mb-harness-mapa:v1`, `saveFeedback`.

## O que verifiquei contra a tarefa

- Orientação mobile cima→baixo: no código + provada por teste de paridade (antes dizia "esquerda→direita" na coluna vertical).
- Ritmo narração/pausa/resume/velocidade: `tempoLeitura` (0,6 s + palavras/3,5 ÷ velocidade) com teste real; pausa vertical congela e retoma a mesma chegada (prova n4: 2/14 "cliente", antes saltava para 3/14).
- Controles clique/teclado/editor/export preservados: menu ⋯, régua 44 px, setas/Delete/Enter/Esc/Ctrl+Z, editor completo, exportar/importar/enviar; fluxo de 43 checks do n4 sobre o HTML final com hashes conferidos por mim (0 falhas).
- Sem overflow/colisão: posicionamento por custo no código; barra estável (180,29 px antes/depois na medição do n4; crítica media pulo 183→193).
- Mapa e editável gerados pela fonte: `--validar` OK, regeneração reprovação pela fonte, compactação só da cópia embutida do cursor.
- Concorrência respeitada: janela >20 min do n4, backups presentes, sessão Claude parou antes de tocar o produto, entrega reutiliza a mesma entrada.
- Conceito cidade/metrô preservado; nenhuma nova estética imposta.

## Notas não bloqueantes (detalhe em revisao-mapa-glm.md)

1. **Limitação declarada:** GLM via adapter textual — não inspecionei prints visualmente; verificação por código, testes e medidas. Inspeção visual foi do GPT (n4/n0), que declarou tê-la feito.
2. Capturas "depois/" do n4 são do quase-final (antes da troca textual 11 paradas→12 estações); compensado com o fluxo 43/43 repetido no HTML final e declarado.
3. `narracao_inicial` estática diz "esquerda→direita" (texto de repouso); o JS a substitui pela orientação correta no arranque — risco residual baixo.
4. Cursor mudou após o fechamento do n4; n3 regenerou e eu revalidei. Se mudar de novo, regenerar pela fonte antes da prova final do n0.

## Pendências

- n0: integração final, apresentação da mesma entrada no app MegaBrain e decisão sobre dupla checagem visual dos prints (nota 1). Nada exigido do <USUARIO> neste nó.

```text
<MEGABRAIN_ROOT>\evidence\261018_ponte-orquestradores
```
