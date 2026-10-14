# MegaBrain · Na sua mesa

Frontend novo da aplicação `apps/megabrain-dashboard`. React, TypeScript e Vite, usando React Grid Layout para os cartões e Lucide para ícones. Reutiliza o cérebro rosa e as famílias tipográficas locais do projeto; não carrega fontes de terceiros.

## Rodar e compilar

Na pasta `apps/megabrain-dashboard/web`:

```powershell
npm.cmd ci
npm.cmd run dev
npm.cmd run build
```

Desenvolvimento: `http://127.0.0.1:5176`, com `/api` encaminhado para `http://127.0.0.1:8766`. Produção: o servidor existente serve `dist/` na mesma origem da API. O frontend não inicia nem configura acesso público.

```powershell
npm.cmd run check
npm.cmd run check:api
```

`check:api` exige o servidor local ligado. Verifica o contrato por leitura, autenticando com a chave nativa local em memória; não imprime credenciais, conteúdo de projetos ou URLs de pairing. O script não dispara análises nem altera projetos. A criação de sessão é o único efeito de autenticação.

## Contrato e persistência

Fonte: `evidence/261011_app-megabrain/CONTRATO-APP.json` na raiz do projeto. Todo dado de projeto vem da API autenticada. Pairing por fragmento `#pair=` é consumido e removido antes do POST. Sessão HttpOnly e CSRF permanecem em memória; não há credencial em localStorage.

Layout, abas e módulos salvam no workspace versionado. Resposta409 preserva rascunho local e oferece recarregar a versão salva; nunca sobrescreve silenciosamente. Comentários e referências são confirmados pelo servidor. Eventos são consultados incrementalmente; dados novos não trocam a versão de arquivo já aberta.

O módulo Processo consulta `/routing`, permitindo escolher categoria, editar etapas, ordenar e testar um exemplo. Obrigatoriedade é definida pelo backend. Nova análise envia categoria escolhida quando fornecida; categorização automática é apresentada como sugestão, com caminho inspecionável. Esta versão executa análise/revisão textual, não edição de código/design nem publicação.

## Verificação da interface

A inspeção visual e os fluxos desktop/mobile são conduzidos pelo coordenador no navegador integrado, contra o servidor real. O build não prova qualidade visual, persistência após reiniciar o servidor, uso físico no Pixel7 ou acesso fora de casa. Esses resultados devem ser registrados separadamente na evidência da tarefa.

Interações principais: Ctrl/Cmd+K, abas, dois projetos lado a lado, preview A/B, modo Organizar com arrastar/resize e alternativas por botões, comentário por menu ou pressão de1segundo. Em tela pequena, a grade vira coluna e os previews alternam A/B.

## Limites

Sem dados fictícios, serviço externo de fontes ou execução automática em código de frontend. A disponibilidade da central e do executor são fatos do backend. Acesso remoto depende da configuração autenticada do serviço; uma URL local não prova uso fora da rede doméstica. Arquivos HTML ficam em iframe isolado, sem scripts.
