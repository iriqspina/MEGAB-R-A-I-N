# ESTADO — megabrain core

MODO: otimizado

TL;DR: v7.5 consolidada. Auditoria multi-IA fechou diagnóstico, limpeza,
relatório único, 19 megabrains de projeto em cópia magra, três mecânicas do
djinnai.io e trava por arquivo integrada aos escritores compartilhados. Suíte
141/141; preflight PODE COMEÇAR; IDs de decisão únicos desde 260825; nenhum
canônico órfão na raiz.

ONDE ESTAMOS: fases 1, 2 e 3 concluídas. A central é o único dono da máquina;
cada projeto guarda ponteiro + estado próprio. `dados/estado.json` é a fonte
para IAs e `00_painel/RELATORIO.html` é a leitura humana. Claude/Kimi/Codex usam
a mesma skill canônica medida pelo preflight.

BLOQUEIO: nenhum.

PRÓXIMO PASSO: abrir `01_acoes/01_ABRIR-RELATORIO.cmd` e validar a leitura
humana. Manutenção futura começa por preflight, trava o arquivo real com
`mb_trava.py`, roda 141+ testes e publica pelas ações 10 → 11 quando houver
mudança pública.

ÚLTIMA AÇÃO: consolidação conjunta Codex + Kimis. A colisão `260825y` virou
`260825ag` no bloco sem citações; o AI reviewer manteve `260825y`. A cópia
órfã de cinco lições recriada na raiz foi fundida no núcleo e removida; o sync
agora usa `u.achar()` e o preflight impede a regressão.
