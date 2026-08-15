---
name: codex-megabrain
description: Executa o protocolo MEGABRAIN no Codex com estado multi-IA, trava de arquivos, planejamento proporcional, auditoria anti-slop, verificação e handoff. Use quando o usuário citar "megabrain", pedir modo completo/otimizado, iniciar ou retomar projeto complexo, solicitar entrega de design/código/documento, pedir revisão rigorosa, ou coordenar Codex com Claude, Kimi ou outro agente.
---

# Codex MEGABRAIN

Aplicar o MEGABRAIN como camada operacional do Codex. Manter a fonte central
como autoridade; não duplicar o protocolo inteiro nesta skill.

## Resolver a fonte

Localizar `<MEGABRAIN_ROOT>` nesta ordem:

1. pasta `MEGABRAIN/` do projeto atual, se existir e estiver sincronizada;
2. variável `MEGABRAIN_CENTRAL`;
3. ancestral ou workspace que contenha `VERSAO.txt`, `MEGABRAIN.md`,
   `bin/mb-check-version.py` e `referencias/`.

Não gravar caminho pessoal absoluto em `SKILL.md`. Se houver mais de uma fonte
plausível ou se o projeto estiver mais novo que a central, parar antes de
sobrescrever e pedir direção.

## Calibrar a execução

- Pergunta rápida ou conversa: responder diretamente; não representar os gates.
- Explicação, revisão ou diagnóstico: inspecionar e relatar; não implementar sem
  pedido de mudança.
- Pedido de criar, alterar ou corrigir: executar mudanças locais reversíveis e
  validar sem pedir confirmação intermediária.
- Escrita externa, publicação, push, compra, exclusão material ou ampliação de
  escopo: obter autorização específica.

## 0. Assumir o trabalho

Antes de editar um projeto:

1. Ler `ESTADO.md`, `HANDOFF.md`, a cauda de `DECISOES.md` e as lições
   relevantes. Não varrer o repositório inteiro primeiro.
2. Verificar alterações existentes e preservá-las.
3. Consultar a trava:

   ```text
   python <MEGABRAIN_ROOT>/bin/mb-sync.py --dir <projeto> status
   ```

4. Se estiver livre, travar somente os caminhos necessários com
   `--agente Codex`. Não tomar trava válida de outro agente.
5. Em projeto derivado, executar `mb-check-version.py --projeto <projeto>`.
   Central mais nova pode sincronizar; projeto mais novo exige decisão do
   usuário antes de subir para a central.
6. Fazer pull somente quando houver repositório, árvore segura para integração
   e escopo autorizado. Pull não é pré-condição cega.

## 1. Enquadrar

Definir internamente antes de produzir:

- artefato final e aplicativo de destino;
- leitor e decisão que ele tomará;
- três critérios verificáveis de aprovação;
- restrições duras;
- contraexemplo genérico que deve ser evitado.

Perguntar apenas quando uma ambiguidade muda materialmente a solução. Para
design, ler `<MEGABRAIN_ROOT>/referencias/260810_design-projects.md`; se a
entrega virar interface em código, ler também
`260810_impeccable-routing.md`.

## 2. Planejar e orçar contexto

- Usar plano quando houver três ou mais etapas dependentes ou múltiplos
  arquivos; manter exatamente uma etapa em andamento.
- Buscar nomes e trechos antes de abrir arquivos grandes.
- Carregar referências sob demanda, conforme a tabela da skill central em
  `<MEGABRAIN_ROOT>/skills/megabrain/SKILL.md`.
- Registrar checkpoint em arquivo quando a tarefa atravessar sessões.
- Delegar somente quando o usuário ou as instruções ativas autorizarem trabalho
  multiagente; dividir apenas subtarefas independentes e limitadas.
- Para escolher modelo, ler
  `<MEGABRAIN_ROOT>/referencias/260813_multi-ia.md`.

## 3. Executar

- Estruturar antes de preencher.
- Preferir a ferramenta e a linguagem já adotadas pelo projeto.
- Não introduzir stack nova sem recomendação registrada e benefício verificável.
- Colocar procedimento repetível em skill, garantia em script/hook, estado em
  arquivos de handoff e conhecimento pesado em referência.
- Pesquisar fatos atuais antes de afirmá-los; marcar estimativas.
- Em diagnóstico técnico, usar o formato pessoal ativo do usuário.

## 4. Auditar e reparar uma vez

Ler `<MEGABRAIN_ROOT>/referencias/260810_anti-slop.md` para texto, copy ou
peça final. Verificar:

- especificidade, evidência e trade-offs;
- repetição, frases vazias e estrutura automática;
- substituição de marca: se serve igual ao concorrente, especificar;
- compressão: cortar cerca de 30% quando nada essencial se perde;
- em visual, hierarquia, contraste e decisões motivadas.

Fazer uma rodada de reparo. Se ainda falhar, voltar ao enquadramento em vez de
polir indefinidamente.

## 5. Verificar

- Abrir o artefato no destino real quando possível.
- Rodar testes proporcionais ao risco e conferir caminhos, datas e cálculos.
- Comparar com `DECISOES.md` e não declarar sucesso com validação parcial.
- Para protocolo ou skill, validar o arquivo efetivamente carregado, não apenas
  a cópia do repositório.
- Validar esta skill com o `quick_validate.py` do criador de skills do Codex.

## 6. Passar o bastão

Ao concluir tarefa não trivial:

1. atualizar `ESTADO.md` de forma curta;
2. atualizar `HANDOFF.md` com feito, aberto, próximo verbo+objeto e arquivos;
3. anexar decisões com a alternativa descartada;
4. liberar a trava com `mb-sync.py ... release --agente Codex`;
5. fazer commit local quando apropriado; nunca fazer push sem autorização
   explícita para o repositório;
6. se o core mudou, atualizar `VERSAO.txt` e registrar quais cópias ainda
   precisam ser sincronizadas.

## Como isso costuma dar errado

1. Aplicar o protocolo inteiro numa pergunta curta.
2. Copiar a skill central e criar duas fontes divergentes.
3. Confundir plano escrito com execução verificada.
4. Escolher o modelo mais caro por reflexo, sem relação com a tarefa.
5. Usar agente barato para decisão final sem auditoria.
6. Alterar stack porque uma tecnologia parece melhor fora do contexto.
7. Fazer push ou sobrescrever projeto mais novo como parte automática do
   handoff.
