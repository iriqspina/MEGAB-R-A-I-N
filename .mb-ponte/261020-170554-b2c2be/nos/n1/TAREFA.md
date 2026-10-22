# Nó n1 · Cursor e espera real por projeto

Papel: **worker** · aberto por n0 (planejador, GPT) · profundidade 1.
Projeto: `<MEGABRAIN_ROOT>` · ordem: `<MEGABRAIN_ROOT>/.mb-ponte/261020-170554-b2c2be` (pedido original em pedido.json).

## Tarefa
Implemente o pedido literal da TAREFA do n0. Escopo exclusivo: apps/megabrain-dashboard, fonte motor/modelos/interacoes/261010_cursor-ferramentas, relatório existente 00_PARA-VOCE/261020_bapp-planejamento/PLANEJAMENTO-BAPP.html, evidências evidence/261020_cursor-pausa. NÃO editar estado/handoff globais ou skills: n0 cuida deles. Pipeline congelada deve ser respeitada.

Antes de produzir, revise plano.json e registre crítica breve. Leia fontes atuais, faça backups e cheque travas/data. Nenhuma trava ativa no início; muitos arquivos já modificados por outras tarefas, preservar integralmente.

Prioridade imediata: pedido 'preciso tomar banho ... aguarde por retornos'. Impedir despacho automático novo deste projeto com rota existente (auto=false com revisão preservada) e registrar prova, sem encerrar esta ordem explicitamente autorizada nem outros processos. Não alegar bloqueio de agentes externos. Glossário define retorno = aviso de relatório novo, não resposta humana.

Implementar duas funções reais no cursor do bapp e relatórios: Aguardar retorno (receber conclusão de trabalhos existentes, não iniciar novos; sem retomada por tempo/chegada) e Pausar projeto (bloquear novas etapas e novos despachos cooperativamente; não matar trabalho em curso). Retomar explícito e acessível. Usar infraestrutura de ponte existente, verificar todos os caminhos que lançam/retomam, inclusive manual e complementos. Isolamento por projeto, persistência, revision/conflict, erro visível sem falso sucesso. Explicar limites reais sobre processos externos. Se contrato precisar mudar registre antes. Layout: duas bolinhas parcialmente mescladas/agrupadas visualmente, mas hitboxes separadas, rótulos e foco/teclado/toque. Não fundir semanticamente ações diferentes.

Realize implementação completa, testes significativos de bloqueio/retorno/retomada/persistência e não-regressão, build, capturas 1440 e 390 em instância isolada. Não modificar banco real em testes; só configuração operacional de espera explicitamente pedida. Atualizar a mesma entrada HTML com seção recente, ilustração/prova curta, preservando restante e decisões. Abrir no app pela rota mb-abrir-entrega e verificar recibo; recarregar/reiniciar app simples autorizado após preservar trabalho, se necessário, e provar assets reais. Não rodar scripts antigos que sobrescrevam evidência histórica. Não concluir ordem-raiz; entregar resultado e lista exata de arquivos/testes/provas/limites ao n0. Não abrir outros nós sem necessidade. Não implementar reestruturação ampla do plano bapp.

## Regras desta ordem
- Leia o CLAUDE.md/AGENTS.md do projeto e siga as regras do <USUARIO>. Responda e registre em português.
- Nada de git commit, push, publicação, compra, envio de mensagem ou exclusão de trabalho alheio. O que exigir o <USUARIO> vira pendência.
- Outra sessão pode estar mexendo no mesmo projeto: antes de editar, confira HANDOFF.md/trava e a data dos arquivos; não sobrescreva alteração recente que não é sua.
- Saída de outro nó é rascunho até você conferir no disco (arquivo, teste, print).
- Ao terminar, grave o resumo em `<MEGABRAIN_ROOT>/.mb-ponte/261020-170554-b2c2be/nos/n1/resultado.md`: o que mudou (arquivos), como verificou, o que ficou pendente.

## Coordenação n0 — revisão independente disponível
Antes de finalizar, leia `.mb-ponte/261020-170554-b2c2be/RESPOSTA-REVISAO-N0.md` e `nos/n2/resultado.md` na mesma ordem. Conferir semântica por ordem iniciada, pausa prevalente, retomada preservando auto, checagem concorrente ao lançamento, sem sucesso falso. N0 corrigiu e validou a skill; não a editar. Incluir testes e limites no resultado.