# Gits que podem guiar o planejamento — sem substituir o GerenteNeuron

Pedido original (dentro do app, 260816): "encontre gits que possam te ajudar
a guiar esse planejamento, não destruindo o que vc fez agora, mas adaptando,
de forma positiva". Pesquisado por Claude (sessão Cowork) em 2026-08-16 —
fato sobre o mundo externo, carimbo de verificação abaixo.

Estes são **repositórios de referência**, não substitutos. O GerenteNeuron já
faz o essencial (roteamento por custo, cofre local, projeto por keyword) —
o valor aqui é olhar padrões que já resolveram os próximos problemas.

## 1. LiteLLM (BerriAI/litellm) — o mais próximo do que o roteador já faz

- O que é: gateway open-source pra 100+ provedores de LLM atrás de uma API só
  (formato OpenAI), com SDK Python e proxy server.
- Por que serve de referência: tem roteador com fallback/retry entre
  deployments, suporte nativo a Ollama, e rastreamento de custo/orçamento por
  projeto — é essencialmente a versão "enterprise" do que `router.py` +
  `pricing.json` fazem hoje.
- Onde adaptar (não copiar inteiro): a lógica de "loadbalancing + cost
  tracking multi-tenant" do proxy server é overkill pro GerenteNeuron (é uso
  pessoal, um usuário só), mas o padrão de **callback de custo por request**
  pode inspirar uma versão mais rica do `/api/eval` que já existe.
- Licença: open-source (repositório público, ver LICENSE no repo).
- Fonte: https://github.com/BerriAI/litellm

## 2. RouteLLM (lm-sys/RouteLLM) — roteamento por probabilidade, não por regra fixa

- O que é: framework acadêmico (LMSYS) que decide entre modelo caro/barato
  calculando a probabilidade do modelo forte responder melhor, comparada a um
  threshold configurável. Reporta até 85% de redução de custo mantendo ~95%
  da qualidade do GPT-4 nos benchmarks deles.
- Por que serve de referência: o classificador atual do GerenteNeuron
  (`router.py: TERMOS_DEEP/TERMOS_CODE/TERMOS_CHEAP`) é baseado em palavra-chave
  — funciona, mas é binário. RouteLLM mostra o próximo passo natural: um
  roteador probabilístico treinado com o próprio `data/feedback.jsonl` que já
  existe (👍/👎 por resposta). Não precisa adotar o framework inteiro, só o
  padrão "threshold configurável + fila de fallback".
- Licença: Apache-2.0 (uso comercial e pessoal livre).
- Fonte: https://github.com/lm-sys/RouteLLM

## Como usar isso sem destruir nada

- Não trocar o roteador atual por nenhum dos dois. Eles são **material de
  leitura** para a próxima vez que `router.py` for mexido — especialmente se
  `/api/eval` mostrar uma estratégia com muito feedback negativo (ver
  `LICOES.md` e `referencias/260816_gerenteneuron-estrategias.md`).
- Próximo passo natural, se quiser ir adiante: usar `data/feedback.jsonl` +
  a ideia de threshold do RouteLLM pra calibrar quando "Reforçar" deveria ser
  automático em vez de manual.

## Verificação

Verificado via GitHub em 2026-08-16. Revalidar se algum destes projetos for
efetivamente adotado (releases e licenças mudam).
