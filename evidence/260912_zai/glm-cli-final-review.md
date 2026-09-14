# Revisão GLM-5.3 da configuração CLI — 12/09/2026

O OpenCode CLI com provider Z.ai e modelo `glm-5.3` leu o plano e sete scripts de `bin/zai` em modo somente leitura. A primeira revisão apontou um defeito real: o atalho Codex passava `-Tier`, parâmetro ausente em `start-codex-glm.ps1`. Também apontou caminho de catálogo preso ao usuário local, prompts iniciados por hífen e risco de histórico Win+V.

Correções e provas do Codex:

1. O instalador de atalhos omite `-Tier` no Codex; o atalho existente foi atualizado. Leitura COM do `.lnk` confirmou destino e ausência de `-Tier`. `start-codex-glm.ps1 -Check` passou.
2. O caminho do catálogo passou a ser montado a partir de `%USERPROFILE%` no inicializador; o perfil já instalado tinha o caminho correto para esta conta.
3. O Codex recebe prompt por stdin e o OpenCode prefixa uma quebra de linha para que um hífen inicial não seja interpretado como opção. Testes reais com prompts iniciados por hífen retornaram `GLM-CODEX-FLAG-OK` e `GLM-OPENCODE-FLAG-OK`, ambos código 0.
4. O plano passou a distinguir clipboard ativo, limpo, do histórico Win+V, não verificado.

A segunda revisão GLM-5.3 leu os quatro scripts alterados e retornou **nenhum bloqueante por inspeção estática**. O revisor declarou que não executou launchers nem validou atalhos instalados; essas provas dinâmicas acima foram feitas pelo Codex. A revisão GLM não constitui `plan_review` ou `review_approved` da run formal V6.
