---
name: marcelinhopet
description: Abre o perfil Marcelinho no aplicativo MEGABRAIN Pets. Use quando o usuário disser /marcelinhopet ou pedir especificamente para chamar ou abrir o Marcelinho.
---

# Marcelinho Pet

1. Resolva a central por `MEGABRAIN_CENTRAL` ou `MEGABRAIN_HOME`; não suponha que o projeto atual contém `bin\mb-pet.py` e não grave um caminho pessoal na skill.
2. Confira o estado real com `python "<raiz>\bin\mb-pet.py" settings --json`.
3. Se o executável estiver disponível, rode `python "<raiz>\bin\mb-pet.py" start --profile marcelinho --project "<pasta atual do projeto>"` com o caminho absoluto real.
4. Se estiver ausente, informe o caminho procurado pelo launcher e ofereça a instalação; não alegue que Marcelinho foi aberto.

O perfil `marcelinho` é um arquivo de dados do Pets. Esta skill é somente o segundo comando canônico; não duplica personalidade, memória nem credenciais.
