---
name: registrar-licao
description: Registra o aprendizado de uma tarefa num arquivo de lições. Use quando o usuário digitar /registrar-licao, disser "registra isso", "anota essa lição", "guarda esse aprendizado", "não deixa eu esquecer disso" ou "aprende com isso".
---

# registrar-licao — memória que corta caminho

Grava 3 linhas num arquivo de lições. Esta versão para Codex não inclui o hook `SessionStart` do pacote Claude; no início de uma entrega, leia o arquivo no Gate 0.

## Onde gravar — dois destinos

Escolha o destino pelo alcance da lição.

### GLOBAL (default) — `<MEGABRAIN_ROOT>/licoes-megabrain.md`

Na central, localize o arquivo de lições pelo estado do projeto; não presuma um caminho absoluto de outra máquina.

Use quando a lição vale **para qualquer projeto**: comportamento de ferramenta, limite de formato, armadilha de processo, padrão que se repete entre clientes.

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
3. Se o pedido do usuário ou o escopo atual autoriza registrar a lição, escreva a entrada completa e **anexe ao fim**. Caso contrário, proponha a entrada e o destino; instalar o plugin não concede autorização de escrita permanente.
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

Quando o arquivo passar de ~40 entradas, relate a necessidade de consolidação e proponha o merge. Consolidar pode apagar ou reescrever histórico, então exige autorização explícita.

## Cabeçalho para arquivo novo

```markdown
# Lições — megabrain

Memória de longo prazo. Em cada entrega, consulte este arquivo no Gate 0.

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
6. **Consolidar sem autorização.** Merge ou remoção de lições muda histórico; primeiro proponha a ação e aguarde autorização.
