# Nó n3 · Revisão final de controle e cursor

Papel: **revisor** · aberto por n0 (planejador, GPT) · profundidade 1.
Projeto: `<MEGABRAIN_ROOT>` · ordem: `<MEGABRAIN_ROOT>/.mb-ponte/261020-170554-b2c2be` (pedido original em pedido.json).

## Tarefa
Revisor independente de resultado, somente leitura. Leia pedido.json, plano.json, RESPOSTA-REVISAO-N0.md, nos/n2/resultado.md, nos/n1/resultado.md e os arquivos/provas que n1 aponta. Confira diff contra backups evidence/261020_cursor-pausa/backup, não contra git inteiro (há trabalho anterior). Avalie código real e testes; rode recorte de testes necessário sem alterar dados reais nem evidências históricas. Saída só no seu resultado.md; não concluir ordem nem editar implementação.

Procure defeitos verificáveis: espera permite só etapas de ordens já iniciadas (não ordem apenas criada), pausa barra novos nós e retomada mesmo manual/CLI/complementos, conclusão/retorno continua, isolamento por projeto, persistência e conflitos, concorrência entre checar e lançar (não prometer atomicidade sem prova), retomada preserva auto anterior e fila não duplica. Não confundir desligar auto com estado aguardando. Certifique-se de que erro de controle não retorna falso sucesso.

UI: dois botões agrupados mas hits/foco distintos, identificação do projeto correto e estado fora do menu, retomada por teclado, desktop/mobile; português sem '?' em lugar de acentos; fonte/cópias/HTML embutido atualizados. Sem impressão de funcionamento a partir de arquivos: conferir provas e limites reais. Skill agrupar-acoes corrigida após n2, opcional; não precisa refazer revisão inteira dela.

Reporte gravidade, arquivo:linha, reprodução e correção mínima. Aceite apenas o escopo provado, sem ampliar para agentes externos. Não lance filhos. Pipeline congelada GPT principal gpt-6-astra medium, cota consultada por n0. Se worker ainda estiver trabalhando, aguarde resultado antes do parecer final, no máximo 60 s por espera, e não dispute arquivos.

## Regras desta ordem
- Leia o CLAUDE.md/AGENTS.md do projeto e siga as regras do <USUARIO>. Responda e registre em português.
- Nada de git commit, push, publicação, compra, envio de mensagem ou exclusão de trabalho alheio. O que exigir o <USUARIO> vira pendência.
- Outra sessão pode estar mexendo no mesmo projeto: antes de editar, confira HANDOFF.md/trava e a data dos arquivos; não sobrescreva alteração recente que não é sua.
- Saída de outro nó é rascunho até você conferir no disco (arquivo, teste, print).
- Ao terminar, grave o resumo em `<MEGABRAIN_ROOT>/.mb-ponte/261020-170554-b2c2be/nos/n3/resultado.md`: o que mudou (arquivos), como verificou, o que ficou pendente.
