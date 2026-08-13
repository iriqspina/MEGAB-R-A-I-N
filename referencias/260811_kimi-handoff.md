# Quando a tarefa bate numa parede do sandbox: empacotar pro Kimi

O Cowork/Claude roda dentro de um sandbox com acesso só ao que foi
explicitamente conectado — não à pasta home, não a caminho fora do que o
<USUARIO> escolheu, e algumas pastas conectadas bloqueiam delete/rename por
política (erro "Operation not permitted" em vez de recusa educada). O Kimi
CLI roda **local, sem sandbox**: enxerga o disco inteiro com a permissão da
conta do <USUARIO>. Quando a tarefa exige isso, a resposta certa não é dizer
"não consigo" — é empacotar a tarefa pro Kimi resolver.

## Quando rotear pra cá

- `request_cowork_directory` devolve erro tipo "Cannot mount the home
  directory itself" ou similar.
- O caminho que a tarefa precisa está fora de qualquer pasta já conectada
  nesta sessão, e conectar mais uma pasta não resolve (ex.: a tarefa precisa
  de várias pastas espalhadas, ou de uma ação em nível de sistema).
- Delete/rename falha com erro de permissão mesmo depois de
  `allow_cowork_file_delete` (a política vale por pasta conectada, não por
  todo o disco).
- Ação de sistema operacional: instalar programa, mexer em variável de
  ambiente, editar registro, matar processo, reiniciar serviço.

Não rotear pra cá só porque é mais rápido — se a pasta já está conectada e
a ferramenta de arquivo já resolve, usa ela. Isso aqui é fallback de
alcance, não atalho de preguiça.

## O que entregar

Nunca "manda pro Kimi resolver" solto. Monta um bloco de texto **pronto pra
colar**, autocontido, sem depender de contexto que só existe nesta
conversa:

1. **Objetivo em uma frase** — o que precisa estar verdadeiro no final.
2. **Caminhos absolutos reais** — nunca "a pasta de lições", sempre
   `<MEGABRAIN_ROOT>\licoes-megabrain.md` por extenso.
   Se o caminho tem espaço duplo ou caractere estranho (ex.: `MEGA B R A I  N`),
   copiar literal, nunca redigitar de memória.
3. **Estado atual verificado** — o que já foi confirmado nesta sessão
   (conteúdo, tamanho, última entrada) pra o Kimi não repetir diagnóstico.
4. **Ação exata** — comando ou passo a passo, não "sincronize os dois
   arquivos" vago.
5. **Como verificar que deu certo** — o que o Kimi (ou o <USUARIO>) deve
   conferir depois, e o que colar de volta pra confirmar.

Formato do bloco: título curto + corpo em markdown dentro de um bloco de
código, pra ele copiar de uma vez.

## Depois que ele rodar no Kimi

Se o <USUARIO> colar o resultado de volta nesta conversa, audita como
qualquer output de outro agente (Gate 4 do protocolo principal): confere se
bateu com o esperado, não assume que rodou limpo só porque ele disse que
rodou. Se a lição/decisão que motivou o handoff merece registro, registra
em `licoes-megabrain.md` — o Kimi ter executado não substitui o registro
daqui.

## Como isso costuma dar errado

1. **Empacotar vago.** "Peça pro Kimi arrumar aquilo" sem caminho absoluto
   nem estado atual obriga o Kimi a redescobrir tudo — perde exatamente o
   trabalho de diagnóstico que já foi feito aqui.
2. **Rotear cedo demais.** Tarefa que a pasta já conectada resolveria virar
   handoff desnecessário — sempre tentar primeiro com o que está conectado.
3. **Não verificar depois.** Aceitar "rodei no Kimi" sem conferir o
   resultado quebra o mesmo princípio que vale pra qualquer entrega de outro
   agente: output alheio é rascunho até auditado.
