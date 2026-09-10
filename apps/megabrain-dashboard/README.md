# MEGABRAIN · visão pessoal

Painel pessoal local: próximo passo e prioridade em uma superfície principal, sinais da leitura, decisões recentes e contexto do projeto. A origem continua sendo `collect()`; o painel não recalcula nem escreve no estado dos projetos.

## Abrir

`launch.vbs` abre sem terminal; `launcher.cmd` serve para depuração. Ambos usam o Python de `apps/ia-quota-widget/.venv`, com PySide6 e QtWebEngine já disponíveis no ambiente verificado em 260910.

A janela mantém **Escolher projeto**, **Atualizar** e releitura a cada 20 segundos. A visualização usa `QWebEngineView` para interpretar o CSS de navegador. Atualizações sem alteração de conteúdo não recarregam a página, preservando foco e rolagem. Os links dos documentos `.md` e `.json` abrem no aplicativo associado pelo Windows.

`python apps/megabrain-dashboard/dashboard.py --html-only --project <pasta>` gera `data/dashboard.html` sem importar PySide6. Nesse arquivo, **Recarregar prévia** apenas reabre o HTML já gerado; não executa Python.

## Dados e aparência

A data exibida é a data registrada na fonte, não a hora do clique. O arquivo `dados/estado.json`, quando presente, conserva a precedência original sobre os documentos Markdown. Os documentos atuais podem ser posteriores à fotografia dos dados; os links permitem conferir ambos.

`assets/dashboard.css` define o vidro claro e as adaptações de largura. Figtree, Instrument Sans e JetBrains Mono são usadas quando instaladas; Segoe UI e Consolas são alternativas locais. Nenhuma fonte remota, imagem externa, gráfico decorativo ou medição inventada é necessária.

## Verificar

`python -m unittest discover -s apps/megabrain-dashboard/tests -v`

Relatório da revisão e prévia para <USUARIO> em `<MEGABRAIN_ROOT>\00_PARA-VOCE\260910_v7-megabrain\`.

Limite desta revisão: a inspeção visual pelo navegador foi bloqueada pela política da ferramenta. Testes de dados e geração do HTML não equivalem a validação visual da janela.
