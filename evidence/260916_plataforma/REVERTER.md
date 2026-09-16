# Reversão local · 260916

1. Os arquivos anteriores ficam em `backup/`, preservados antes de editar; o motor de automações possui backup próprio na mesma árvore. O dashboard estava limpo no início: cópia anterior exata recuperável de `git show HEAD:apps/megabrain-dashboard/dashboard.py`, HEAD inicial em baseline.json.
2. Antes de restaurar qualquer arquivo, comparar o hash atual com `manifesto-final.json`. Se houve edição posterior, não sobrescrever: aplicar reversão do trecho em revisão manual.
3. Reverter somente os arquivos listados no manifesto desta rodada. Não executar git reset/checkout sobre o workspace, que já tinha alterações de outras sessões.
4. Novos módulos podem permanecer inativos: restaurar as chamadas do hook e do aplicativo remove a integração. Preferências e registros são dados locais preserváveis. A entrada HTML continua disponível sem executar processos.
5. Identidades sincronizadas têm backups por destino em `backup-identidades/`; conservar também a fonte antiga. Restaurar via sincronizador após examinar mudanças posteriores, nunca por cópia cega.
6. Nenhum arquivo antigo foi movido. Não há migração de caminho para desfazer nem instalação de serviço agendado.
