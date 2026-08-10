# MEGABRAIN · camada de projeto

Complementa `SKILL.md` (gates de entrega + multi-agente). Este arquivo
governa o **projeto inteiro**, não a entrega isolada.

---

## 1 · Fases do projeto (macro)

```
estado → grelhar → spec → tickets → implementar → validar → publicar → registrar
```

1. **ESTADO** — medir antes de dizer. Toda sessão começa lendo o estado real
   (git, build, testes, o que está no ar) e devolve um retrato de 5 linhas,
   TL;DR primeiro. Sinal que não se mediu vira `?`, nunca chute.
2. **GRELHAR** — entender antes de especificar. Interrogatório até fechar
   cada ramo. O que se aprende vira termo num glossário do domínio ou
   decisão registrada — nunca fica só na conversa.
3. **SPEC** — uma por feature, viva, com critérios de aceite verificáveis.
   Sonda de 2 minutos antes: suposição de viabilidade vira linha SIM/NÃO
   medida antes de entrar na spec.
4. **TICKETS** — decomposição com dependência (`Blocked by`, prioridade,
   critério de aceite próprio).
5. **IMPLEMENTAR** — um ticket por vez, TDD por fatia. Revisão em dois eixos
   (padrão do repo + fidelidade à spec) antes do commit. Nunca código sem
   spec.
6. **VALIDAR** — o número sai do harness, nunca de documento. Teste que
   afirmava o bug e não afirma mais: reaponta se mudou de lugar, apaga se o
   defeito sumiu — nunca remenda pra defender o erro.
7. **PUBLICAR** — portões impossíveis de pular, pausa antes do irreversível.
   Build → verificar artefato → auditoria → harness → **pausa** → deploy →
   smoke → linha no changelog. O agente prepara e testa, nunca executa
   deploy ou migração: entrega um script pronto que roda os portões e
   pausa antes do irreversível.
8. **REGISTRAR** — sessão sem rastro não aconteceu. Diário ganha entrada;
   lição nova entra no arquivo de lições sem pedir permissão. Lição 3× vira
   regra deste arquivo ou de uma skill.

## 2 · Artefatos (o que existe em todo projeto adulto)

| Artefato | Papel |
|---|---|
| glossário do domínio | termo ambíguo se resolve aqui |
| regras fixas do repo | convenções invioláveis do projeto |
| tracker vivo por feature | spec, plano, decomposição, issues |
| `docs/` | planos e handoffs, datados |
| atalhos numerados + leiame | o dia a dia em um clique |
| relatório vivo | retrato auto-atualizante — edita-se o gerador, nunca o output |
| changelog | o que subiu, mais novo primeiro |
| pasta de descartáveis | sondas e scripts de uma vez só |
| `MEGABRAIN/` | esta pipeline sincronizada — cópia não se edita |

## 3 · Regras de ouro (valem em todo projeto)

1. Nunca escrever código sem plano ou spec. Sem exceção.
2. Um comando de terminal por vez — prompt interativo engole a linha colada.
3. Data no nome de arquivo só fora do repo (exports, entregas). Dentro,
   nome estável — quem versiona é o git.
4. Gerado nunca se edita — edita-se a fonte/o gerador.
5. Arquivo gigante se lê por trecho, nunca inteiro sem necessidade.
6. Deploy, migração, irreversível: sempre script pronto com pausa antes do
   ponto sem volta — nunca lista de comandos soltos.
7. Ao pedir uma ação a quem opera, sempre o caminho completo do
   arquivo/pasta.
8. Local-first — dado pessoal não sobe pra serviço externo.
9. Medir > supor. Marcador de "não medido" em vez de chute.
10. Tela que muda não se distingue de travada — tarefa longa nunca
    redireciona a saída inteira pra arquivo; dois canais (tela + log).
11. Achado é endereço, não posição — nunca renumerar; derrubado fica
    riscado com o porquê; novo pega o próximo número livre.
12. Commit alheio pendente não sequestra arquivo novo — checar o estado do
    versionamento antes de criar arquivo; havendo pendência, adicionar só
    a lista explícita do que é seu.
13. Buscar comportamento por verbos e sinônimos, não pelo termo exato do
    pedido.
14. Teste vermelho pós-conserto: reapontar ou apagar — nunca remendar
    seletor que defende o erro.
15. Feedback de uma ação nasce no campo visual de quem agiu.
16. Formato de resposta padrão: TL;DR no topo; primeira frase de cada
    parte resume a parte; tópicos numerados.
17. Portar entre agentes/runtimes: hooks não atravessam, skills atravessam
    sem edição. Regra sempre-ativa e estática vai pro system prompt, não
    pro hook.
18. Memória/arquivo legado: normalizar pra UTF-8 puro antes de editar por
    programa.
19. Quadro que se monitora todo dia vira widget fixo + tarefa agendada, em
    vez de depender de lembrar de pedir.
20. **Garantia real é script, não markdown.** O que precisa acontecer
    sempre e sem falha vive em script/hook, nunca só numa skill.
21. Formato pedido explicitamente vence o protocolo. Ordem: formato pedido
    > protocolo > default.

## 4 · Camada micro (gates de entrega + multi-agente)

Vive em `SKILL.md` — não duplicado aqui.

## 5 · Níveis de adoção por projeto

| Nível | O que o projeto tem | Quando |
|---|---|---|
| **1 · referência** | `MEGABRAIN/` + glossário do domínio | projeto novo ou exploração |
| **2 · tracker** | + tracker de specs/tickets + regras do repo | entrou em desenvolvimento |
| **3 · ciclo completo** | + harness com carimbo + atalhos + relatório vivo + deploy com portões | produto no ar |

Todo projeto nasce no nível 1. Subir de nível é decisão explícita, com
spec — nunca por acidente.

## 6 · Como esta pipeline evolui

1. Lição nova → arquivo de lições (GATILHO/LIÇÃO/ATALHO, datada).
2. Lição 3× → entra neste arquivo ou na `SKILL.md`.
3. Editou a fonte → registre a mudança no changelog da própria pipeline.
4. Espalhe a versão nova pros projetos que adotaram (script de sincronização
   próprio de cada setup).
5. A cópia dentro de cada projeto não se edita — a fonte manda.
