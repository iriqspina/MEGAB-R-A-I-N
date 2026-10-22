---
name: filtro-percepcao
description: Revisão fina da comunicação que o app mostra sobre si mesmo (avisos, estados, erros, números) para não gerar sentimento negativo falso nem culpar o usuário sem evidência medida. Use automaticamente ao desenhar ou revisar qualquer aviso/status/erro/telemetria visível na interface, em qualquer projeto. Não proíbe linguagem visual (cor, ícone, forma) e não esconde problema real.
---

# filtro-percepcao — o app não se acusa; o usuário não se sente culpado

**v1 · 261022**. Nasceu de um pedido do <USUARIO> (Bubble): tirar o aviso grande
"Sua conexão está travando" porque, além de grande, "é negativo pro sentimento do
usuário" — e criar uma proteção permanente: "uma skill que protege as informações
que podem ser mal interpretadas ou podem induzir a alguém a achar que é negativo o
uso do app, ou o próprio app ser ruim". O próprio pedido define o limite: "é pra ser
uma revisão fina, mais do que algo que vá limitar os desdobramentos de outros
designs" — não é "não podemos usar vermelho nunca".

## A regra que sustenta tudo

**Comunicação de estado é design de sentimento.** Todo texto, aviso ou número que o
app mostra sobre si mesmo ou sobre o ambiente do usuário é lido como um julgamento:
do app, da conexão, do aparelho, da pessoa. Informação técnica sem tradução de
intenção gera sentimento negativo falso. O app pode (e deve) medir tudo — o que
muda é o que vira interface.

## Os 7 princípios

1. **Saudável é invisível.** Estado bom não ocupa tela. Se não tem nada para o
   usuário fazer, não tem nada para mostrar. (Alinhado à regra de UI do Bubble:
   status vira toast, pílula compacta; estado saudável invisível.)
2. **Resolver sozinho vem antes de acusar.** Se o app pode se ajustar (degradar
   qualidade, tentar de novo, cachear, reconectar), ajusta em silêncio e conta só
   quando a mudação for perceptível para a pessoa ("sua câmera pausou; volta
   sozinha quando a conexão melhorar").
3. **Só acusa com evidência medida.** "Sua internet não está dando conta" exige
   perda/atraso medidos — não estimativa conservadora do navegador, não limite do
   próprio serviço no caminho. Estimativa vira diagnóstico, nunca acusação.
4. **Culpa a causa certa.** Distinguir 4 culpados possíveis: (a) o
   aparelho/conexão do usuário, (b) o caminho até o serviço, (c) decisão ou limite
   do serviço, (d) bug nosso. A frase aponta o certo, com palavra neutra — ou não
   aponta ninguém.
5. **Toda acusação é proporcional e vem com saída.** Aviso grande = problema que o
   usuário pode resolver agora, com botão que resolve de verdade (valor coerente
   com a medição). Sem saída acionável = não é aviso, é log. Tamanho segue a
   consequência: toast < pílula < banner.
6. **Número bruto é diagnóstico, não interface.** Métricas (Mbps, RTT, MOS, perda)
   ficam no painel técnico/diagnóstico para quem pediu; no fluxo, só estado
   traduzido em consequência para a pessoa.
7. **Palavra neutra, verdade inteira.** "Está se ajustando" > "está travando";
   "voltou sozinho" > "caiu". Sem drama e sem maquiagem: problema que exige ação
   continua claro — inclusive com cor de alerta quando for verdadeiro.

## O que esta skill NÃO é (para não cercear design)

- **Não proíbe recurso visual.** Vermelho, ícone de alerta, animação de erro:
  permitidos quando o problema é real e pede ação. O filtro é sobre frase, tamanho,
  momento e evidência — não sobre paleta ou forma.
- **Não esconde falha.** Bug, incidente e limitação continuam registrados no canal
  técnico (logs, diagnóstico, relatório). Silêncio na interface ≠ silêncio para o
  desenvolvedor.
- **Não mexe na voz da marca nem em peça criativa** (marketing, arte, conceito,
  ilustração). Atua só na comunicação de estado/erro/telemetria do produto.
- **Não é gate extra.** É checklist de 2 minutos na revisão de UI, junto com a
  checagem visual 1440/390 — não cria aprovação nova, não trava entrega, não
  limita experimento visual.

## Checklist (aplicar em todo aviso/status/erro/número visível)

1. Exige ação do usuário agora? Se não, não mostra.
2. O tamanho é proporcional à consequência?
3. A frase aponta a causa certa (usuário × caminho × serviço × bug)?
4. Tem evidência medida, não estimativa?
5. A saída oferecida resolve de verdade (coerente com a medição)?
6. O número bruto ficou no painel técnico?
7. Lendo frio, alguém concluiria "o app é ruim" ou "meu aparelho é ruim" sem ser
   verdade? Se sim, reescrever.

## Caso fundador (Bubble, 261022)

**Antes:** banner central grande "Sua conexão está travando · Sua internet não está
dando conta de enviar tudo · Capacidade estimada ~1 Mbps", botão "Limitar envio a
1,5 Mbps" (acima da capacidade estimada — não resolvia nada). Disparava com
estimativa conservadora do caminho (falso-positivo), com speedtest bom e o Discord
"liso" ao lado: lia-se como "o app é ruim". **Depois:** banner removido do rtc.js;
o controlador de qualidade continua degradando sozinho em silêncio; câmera pausada
avisa em toast neutro que diz que volta sozinha; controle manual segue no menu
Qualidade da tela e no gráfico Onda; números no diagnóstico local. Bateria 362/362.

Fonte literal do pedido: `memoria/cerebro/raw/261022_pedido-filtro-percepcao.md`.
