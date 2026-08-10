# Context engineering

> Contexto é recurso **finito e degradante**. Não é depósito: é orçamento.

---

## Os quatro modos de falha

| Falha | Sintoma | Correção |
|---|---|---|
| **Poluição** | Informação irrelevante disputa atenção com a relevante | Ler sob demanda; grep antes de read |
| **Context rot** | Qualidade cai em contexto longo mesmo sem estourar o limite | Checkpoint em arquivo; recomeçar sessão |
| **Ferramenta inchada** | Modelo escolhe a ferramenta errada | Conjunto mínimo viável |
| **Perda de meio** | Instrução no meio de prompt longo é ignorada | Crítico no início e repetido no fim |

---

## Técnicas

### 1. Leitura sob demanda
Nunca despeje pasta ou repositório inteiro. Sequência: `Glob` (achar) → `Grep`
(localizar trecho) → `Read` (só o trecho, com offset/limit).

Regra: **leia o arquivo quando precisar dele, não guarde o arquivo na
memória.** Reler 40 linhas é mais barato que carregar 4000 e degradar todo o
resto da sessão.

### 2. Compactação
Em tarefa longa, resuma o trecho concluído e descarte o bruto. O que sobrevive:
decisões tomadas, restrições descobertas, estado atual. O que morre: o caminho
até lá.

### 3. Nota estruturada (a técnica mais subestimada)
Escreva o estado num `.md` de trabalho em vez de carregar na janela.

```markdown
# 260804_estado.md
## Decidido
- Paleta travada: #161616 / #F2F2F2 / #FF4D00
- Formato final: .pptx 16:9, entrega 06/08

## Aberto
- Fonte do título: aguardando aprovação do cliente

## Descartado (não reabrir)
- Versão com gradiente — cliente rejeitou 04/08
```

O arquivo não sofre context rot. A janela sofre. Sessão longa = mova a memória
pro disco.

> A seção "Descartado (não reabrir)" é o que impede o agente de reciclar ideia
> morta na iteração seguinte.

### 4. Agente separado para trabalho barulhento
Pesquisa ampla, varredura de arquivos, coleta de dados → delegue a um agente
separado (sob pedido explícito): ele queima o contexto *dele* e
devolve só a conclusão.

Delegue: busca ampla · leitura de muitos arquivos · verificação independente ·
exploração de alternativas.
Não delegue: decisão que depende do histórico da conversa · trabalho que exige
o contexto acumulado.

Agente **específico** bate genérico. "Auditar contraste WCAG nas 6 telas" >
"agente de QA".

### 5. Conjunto mínimo viável de ferramentas
*Se um humano não consegue dizer com certeza qual ferramenta usar numa dada
situação, o agente também não consegue.* Ferramenta ambígua = contexto
desperdiçado em decisão errada.

### 6. Divulgação progressiva (3 níveis)
```
Nível 1  descrição da skill (sempre em contexto)  ~30 palavras
Nível 2  corpo da SKILL.md (ao disparar)          <500 linhas
Nível 3  arquivos de referência (sob demanda)     sem limite prático
```
É por isso que o MEGABRAIN é fatiado em `referencias/` e não num monólito.

---

## Orçamento prático de sessão

| Zona | Comportamento |
|---|---|
| 0–50% | Normal |
| 50–70% | Comece a compactar; escreva estado em arquivo |
| 70–85% | Delegue trabalho novo; não abra arquivo grande |
| >85% | Escreva handoff completo em `.md` e recomece a sessão |

Handoff mínimo: objetivo · decidido · aberto · descartado · próximo passo ·
caminhos dos arquivos (template pronto: T6 em `260810_metaprompt-templates.md`).

---

## Como isso costuma dar errado

1. **Ler preventivamente "pra ter contexto".** Isso não é contexto, é ruído.
2. **Confiar na memória de 200 mensagens atrás.** Não confie — releia o arquivo.
3. **Um agente genérico pra tudo.** Ele devolve resumo genérico.
4. **System prompt gigante.** Custa em toda sessão, inclusive nas que não
   precisam.
5. **Compactar cedo demais.** Compactar antes de decidir apaga a informação que
   sustentava a decisão. Compacte depois de fechar o bloco.
