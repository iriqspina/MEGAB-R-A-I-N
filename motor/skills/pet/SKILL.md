---
name: pet
description: Gerencia e abre o MEGABRAIN Pets, incluindo estado real da instalação, configurações e perfis. Use quando o usuário disser /pet ou pedir para abrir, configurar ou conferir o aplicativo Pets.
---

# MEGABRAIN Pets

Use o launcher canônico da central; não deduza instalação pelo texto da skill. Resolva a raiz por `MEGABRAIN_CENTRAL` e, se ausente, `MEGABRAIN_HOME`. O launcher é `<raiz>\bin\mb-pet.py`. Se as duas variáveis estiverem ausentes, procure uma central local identificável antes de agir; não suponha que o projeto atual contém o launcher e não grave caminho pessoal dentro da skill.

1. Rode `python "<raiz>\bin\mb-pet.py" settings --json`.
2. Se `available` for falso, informe que o aplicativo ainda não está disponível. Só rode `offers` quando o usuário pedir a instalação ou estiver num fluxo interativo de instalação da identidade.
3. Para abrir o aplicativo no projeto em que o usuário está trabalhando, rode `python "<raiz>\bin\mb-pet.py" start --project "<pasta atual do projeto>"` com o caminho absoluto real.
4. Para listar perfis, rode `python "<raiz>\bin\mb-pet.py" profiles --json`. Para abrir o gerenciador ligado ao projeto atual, rode `python "<raiz>\bin\mb-pet.py" start --view profiles --project "<pasta atual do projeto>"`.

Perfis são dados. Nunca importe código de um perfil. Credenciais e integrações externas continuam exigindo configuração pelo usuário no aplicativo.
