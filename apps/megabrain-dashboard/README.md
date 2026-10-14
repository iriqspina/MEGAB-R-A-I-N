# MegaBrain Central para Windows

Instale pela raiz: dois cliques em `INSTALAR-MEGABRAIN.cmd`. O instalador cria um
ambiente Python local compartilhado com o widget de cotas, instala dependências,
compila o lançador e cria `00_PARA-VOCE/MegaBrain Central.lnk`. Abre o relatório
de boas-vindas dentro do aplicativo. Não requer Node para consultar a interface.

Requisitos: Windows 64 bits, Python 3.11 a 3.14, internet para obter dependências
e compilador .NET Framework 4 do Windows. A instalação não configura contas de IA,
serviço global, firewall ou túnel. Seus arquivos e dados começam locais.

O botão **Guia do MegaBrain** explica as funções e os limites por assunto.
Projetos são descobertos ao lado da pasta MegaBrain quando contêm ESTADO.md,
MEGABRAIN ou 00_PARA-VOCE. Apresentar uma sessão não cadastra automaticamente
um projeto fora desse conjunto.

Para um relatório recebido: copie o HTML e recursos relativos para
`00_PARA-VOCE/<tarefa>/` de um projeto. Use o Python do ambiente criado para
`bin/mb-abrir-entrega.py <arquivo-absoluto>`. O relatório abre no aplicativo;
a confirmação fica no recibo nativo, separada do pedido de abertura.

Execução por IA exige clientes oficiais instalados e autenticados nas suas contas.
O isolamento de código exige configuração compatível de Windows/Node/Codex.
O revisor ZCode depende de versão verificada. A instalação do app não comprova
esses recursos nem conecta fornecedores. Celular remoto exige configuração própria.
