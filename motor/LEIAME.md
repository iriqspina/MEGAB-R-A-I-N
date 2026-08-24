# motor\ — a máquina do megabrain

Você não precisa abrir nada aqui. Esta pasta guarda o que faz o megabrain
funcionar; a raiz da central guarda o que é SEU.

| pasta | o que é |
|---|---|
| `skills\` | os poderes que a IA carrega (/megabrain, /ingerir, ...) |
| `referencias\` | os textos de método que a IA consulta |
| `modelos\` | moldes: META, cérebro vazio, peças visuais do relatório |
| `dna\` | o retrato do protocolo + o backup imaculado das suas infos (`dna\usuario\`, nunca sobe) |
| `tests\` | a rede de segurança: roda com `python bin\mb-testar.py` |
| `dist\` | os instaláveis (.plugin/.skill) que você clica pra instalar |
| `plugin-megabrain\` · `plugin-megabrain-claude\` | as fontes dos plugins (Kimi e Claude/Cowork) |
| `gerenteneuron\` | o Neuron: app local e observador de telemetria |

`bin\` continua na raiz de propósito: o hook dos agentes aponta pra ele por
caminho absoluto, e mover quebraria configuração fora da central.

Criado na etapa 2 da reorg (260824). Manifesto e como desfazer:
`90_arquivo\migracao-motor-260824\manifest.json` ·
`python bin\mb-migrar-motor.py --desfazer`
