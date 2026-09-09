# Checklist de cobertura v1 — gate de planejamento

Regra: o orquestrador responde **todas** as 15 chaves com `sim` / `nao` / `na` + nota.
`na` sem justificativa é falha de gate, não é aprovação.
`nao` é permitido — significa "consciente e fora de escopo", e vai para `escopo_fora`.

Este arquivo é vivo. Toda omissão real que escapar vira linha nova aqui, alimentada pelo `falhas.jsonl`.

| # | Chave | Pergunta que o orquestrador responde |
|---|---|---|
| 1 | `migracao_dados` | Algum dado existente muda de forma, tipo ou local? Quem migra os registros já gravados? |
| 2 | `rollback` | Se isso quebrar em produção, qual é o comando ou passo exato para voltar? |
| 3 | `testes` | Que teste novo prova que isso funciona? Que teste existente pode quebrar por causa disso? |
| 4 | `config_env` | Precisa de variável de ambiente, chave, flag ou secret novo? Onde é documentado? |
| 5 | `documentacao` | O que um humano precisa ler depois para operar isso? README, AGENTS.md, comentário? |
| 6 | `erro_rede` | O que acontece se a chamada externa falhar, demorar ou voltar 500? Tem retry? Tem timeout? |
| 7 | `estado_vazio` | Como fica a tela/saída quando não há nenhum dado? |
| 8 | `estado_carregando` | Existe momento de espera perceptível? O que o usuário vê nele? |
| 9 | `permissao_auth` | Quem pode fazer isso? Alguém que não deveria consegue? Muda alguma regra de acesso? |
| 10 | `responsivo_mobile` | Isso é visto em tela pequena? Continua utilizável a ~380px? |
| 11 | `dark_mode` | Alguma cor foi fixada em hex? Sobrevive à inversão de tema? |
| 12 | `acessibilidade` | Contraste, foco de teclado, label em controle sem texto, leitor de tela. |
| 13 | `performance` | Isso roda em loop, em lista grande, ou a cada render? Qual o pior caso de volume? |
| 14 | `log_observabilidade` | Quando isso falhar em produção, o que aparece no log para eu descobrir? |
| 15 | `compatibilidade_versao` | Quebra API pública, contrato de dados, ou clientes antigos? Precisa de versionamento? |

## Perguntas condicionais (só quando aplicável ao seu stack)

Ativar por tipo de projeto. Se ativadas, entram como chaves extras em `cobertura`.

- **Cliente/design:** o entregável respeita o brandbook? Existe versão em outro formato/proporção pedida?
- **WordPress / portfólio:** o bloco aparece igual no editor e no front? (paridade Gutenberg)
- **Figma ↔ código:** qual lado é a fonte da verdade nesta mudança?
- **Cloudflare/Supabase:** muda binding, migration, RLS ou limite de plano?
- **Financeiro/dados sensíveis:** algum valor real entra em log, prompt ou commit?

## Como o adversário usa isso

O orquestrador-2 recebe o plano **já preenchido** e a instrução:

> Não melhore este plano. Encontre o que falta nele.
> Liste no mínimo 5 lacunas. Se encontrar menos de 5, a quinta entrada deve explicar
> por que você acredita que o plano está completo e o que você verificou para concluir isso.
> Para cada lacuna: gravidade (bloqueante / importante / cosmética) e o item do plano que deveria cobri-la.
> Você não propõe solução. Você aponta o buraco.

Saída dele vai em `lacunas_adversario`. Toda lacuna `bloqueante` com `resolucao: recusada`
exige justificativa registrada em `DECISOES.md` — é o único caminho para o plano passar do gate.
