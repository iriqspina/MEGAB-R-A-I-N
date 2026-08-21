---
name: registrar-licao
description: Grava o aprendizado de uma tarefa num arquivo de lições que o plugin megabrain lê automaticamente no início das próximas sessões. Use quando o usuário digitar /megabrain:licao, disser "registra isso", "anota essa lição", "guarda esse aprendizado", "não deixa eu esquecer disso", "aprende com isso", ou ao concluir uma tarefa não-trivial em que algo deu errado, surpreendeu, ou revelou um atalho.
---

# registrar-licao — memória que corta caminho

Grava 3 linhas num arquivo de lições. O hook `SessionStart` do plugin encontra esse arquivo na pasta de trabalho e injeta o conteúdo automaticamente — o usuário nunca precisa lembrar de abrir.

## Onde gravar — dois destinos

O hook `SessionStart` do plugin carrega os dois automaticamente. Escolha pelo alcance da lição.

### GLOBAL (default) — `<MEGABRAIN_ROOT>/licoes-megabrain.md`

No Windows, o caminho padrão é `S:\projetos multi i.a\MEGA B R A I  N\licoes-megabrain.md` (definido pela variável de ambiente `MEGABRAIN_ROOT`; sem ela, o hook usa esse fallback).

Use quando a lição vale **para qualquer projeto**: comportamento de ferramenta, limite de formato, armadilha de processo, padrão que se repete entre clientes. O hook cria esse arquivo na primeira execução.

**Este é o destino padrão.** Na dúvida, é aqui.

### PROJETO — arquivo de lições na pasta de trabalho

Use quando a lição é **específica de um cliente ou produto**: preferência de marca, restrição técnica daquele stack, o que aquele stakeholder rejeita. Não polui os outros projetos.

Procure nesta ordem, até 2 níveis abaixo da pasta conectada:

1. `licoes-megabrain.md`
2. `METAPROTOCOLO-LICOES.md`
3. `LICOES.md` / `LESSONS.md`
4. Qualquer arquivo terminando nesses nomes (ex.: `260804_LESSONS.md`)

Não achou e a lição é claramente do projeto → crie `licoes-megabrain.md` na raiz da pasta, com o cabeçalho do fim deste arquivo. Se o usuário tem convenção de nome (ex.: prefixo de data `YYMMDD_`), respeite.

### Regra de decisão

> Essa lição seria útil num cliente completamente diferente? **Sim → global. Não → projeto.**

Em qualquer destino: **anexe ao fim**, nunca reescreva o arquivo.

## Formato da entrada

```
## YYMMDD — <contexto em até 5 palavras>
GATILHO: quando essa situação reaparece
LIÇÃO: o que deu errado ou foi descoberto
ATALHO: o que fazer direto da próxima vez
```

Use a data de hoje. Uma linha por campo. Sem parágrafo, sem enfeite.

## Como escrever cada campo

**GATILHO** é a condição de reconhecimento futuro, não o nome do projeto.
- ❌ `projeto do cliente X`
- ✅ `deck de proposta para cliente que já tem identidade visual fechada`

**LIÇÃO** é o fato surpreendente, não a narrativa.
- ❌ `tivemos dificuldade com as fontes`
- ✅ `PowerPoint não embute fonte variável — exporta como fallback silenciosamente`

**ATALHO** é uma ação executável, não um princípio.
- ❌ `prestar mais atenção nas fontes`
- ✅ `converter variable font para instância estática antes de montar o .pptx`

## Filtro — o que NÃO registrar

Se a entrada não muda uma ação futura, ela é lixo de contexto: custa tokens em toda sessão seguinte e não paga nada.

Não registre:
- Narrativa da sessão ("fizemos um deck de 12 slides")
- Preferência permanente do usuário (tom, ferramenta, formato) → isso vai pro `SYSTEM.md` do plugin ou do agente, não aqui
- Fato que qualquer um saberia sem ter passado por isso
- Elogio ou balanço ("correu bem")

## Procedimento

1. Identifique o que na tarefa foi **não-óbvio antes de começar**. Se nada foi, diga isso e não registre.
2. Decida o destino pela regra acima (global vs projeto).
3. Escreva a entrada completa e **anexe direto ao arquivo**. Não pergunte, não mostre para aprovar, não espere confirmação — o usuário deu autorização permanente ao instalar o plugin.
4. Informe em UMA linha o gatilho gravado e o caminho do arquivo.

## Promoção — quando a lição vira skill

Ao gravar, verifique se o arquivo já tem entradas com o **mesmo gatilho**.

| Ocorrências | Ação |
|---|---|
| 1× | Grave normal |
| 2× | Grave e marque a entrada com `[2×]` |
| 3× | Grave, marque `[3×]` e **avise**: isso virou processo, não memória — proponha transformar numa skill própria |

Lição que se repete três vezes não é memória, é procedimento não escrito. Skill é mais barata que reler a mesma lição toda sessão.

## Manutenção

Quando o arquivo passar de ~40 entradas, faça a consolidação direto, sem pedir permissão: agrupe por tema, funda entradas redundantes, apague as que descreviam ferramentas ou versões que não existem mais. Arquivo de lições inchado vira o problema que ele deveria resolver. Depois liste em uma linha o que foi fundido e o que saiu — é a única coisa que precisa de revisão dele.

## Cabeçalho para arquivo novo

```markdown
# Lições — megabrain

Memória de longo prazo. O hook do plugin injeta este arquivo automaticamente
no início de cada sessão nesta pasta.

Formato: GATILHO (quando reaparece) / LIÇÃO (o que descobri) / ATALHO (o que
fazer direto). Só entra o que muda comportamento futuro.

---
```

## Como isso costuma dar errado

1. **Virar diário.** Entrada que narra em vez de instruir. Custa contexto em toda sessão e não devolve nada.
2. **Gatilho vago.** `projeto de design` casa com tudo, então não avisa nada. O gatilho precisa ser reconhecível e específico.
3. **Atalho que é princípio.** "Ter mais cuidado" não é executável. Escreva o comando, o passo, o parâmetro.
4. **Sobrescrever o arquivo.** Sempre anexe. Perder o histórico apaga o valor acumulado.
5. **Registrar preferência permanente aqui.** Preferência é configuração, não lição — o lugar dela é o `SYSTEM.md`.
6. **Nunca consolidar.** Sem poda, o arquivo cresce até virar ruído.
