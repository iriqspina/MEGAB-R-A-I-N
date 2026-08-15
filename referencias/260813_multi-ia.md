# Guia multi-IA — qual modelo usar para quê

Guia genérico para escolher entre IAs de código em tarefas de desenvolvimento,
design e documentação. Não prende a um projeto específico.

## Divisão por tipo de trabalho

| Tarefa | Agente indicado | Por quê |
|---|---|---|
| Varredura, extração, leitura longa | Contexto grande / custo baixo | Economiza token do agente de julgamento |
| Refactor mecânico, boilerplate | Contexto grande / custo baixo | Trabalho repetitivo, pouca decisão |
| Enquadramento, decisão de design | Julgamento / síntese | Define direção antes de gastar código |
| Auditoria anti-slop, texto final | Julgamento / síntese | Requer leitura crítica e gosto |
| Handoff multi-agente (Claude↔Kimi) | Ambos, com trava | Um prepara, outro revisa; trava evita conflito |
| Fallback (quando um falha) | Terceiro agente | Sem papel fixo; assume o gate do substituído |

## Escolha por modelo

| Modelo | Melhor uso | Evitar |
|---|---|---|
| Claude (Opus/Sonnet) | Julgamento, síntese, auditoria, decisão de design | Varredura longa em repo grande |
| Kimi (K2) | Contexto longo, extração, primeira passada | Entrega final sem revisão do Claude |
| GPT-5.6 Sol | Capacidade de fronteira: arquitetura difícil, decisão de design, auditoria final e trabalho profissional complexo | Varredura ou transformação mecânica em volume quando custo/latência importam |
| GPT-5.6 Terra | Equilíbrio entre inteligência e custo: implementação cotidiana, revisão de código e síntese com julgamento moderado | Usar como máximo automático sem medir ganho sobre Terra/Luna |
| GPT-5.6 Luna | Alto volume sensível a custo: busca, extração, classificação, boilerplate e primeira passada | Decisão final de alto risco sem revisão por Terra/Sol |
| GPT-5.5 | Compatibilidade com fluxos já calibrados; segunda opinião em tarefa profissional complexa | Escolha nova por padrão quando a família 5.6 estiver disponível e testada |
| GPT-5.4 | Trabalho cotidiano com custo menor e comportamento já conhecido | Arquitetura ou auditoria mais difícil se 5.6 estiver disponível |
| GPT-5.4 Mini | Subtarefas focadas, agentes auxiliares, triagem e transformação simples em volume | Síntese final, ambiguidade alta ou mudanças amplas no repositório |
| Qwen3.8-27B Q4_K_M local (Ollama) | Texto privado: classificação, extração, primeira passada e transformação mecânica | Trabalho interativo ou síntese crítica na RTX 4070 de 12 GB: a quantização de 17,1 GB usa também RAM e fica lenta |
| Gemini | Fallback opcional, multimodal | Não é membro fixo; usar só quando os outros falham |

### Esforço de raciocínio na família GPT-5.6

| Nível | Usar em | Exemplo MEGABRAIN |
|---|---|---|
| `low` | Latência e volume | localizar arquivos, extrair decisões, formatar dados |
| `medium` | Ponto de partida recomendado | implementar mudança delimitada e rodar testes |
| `high` / `xhigh` | Ambiguidade ou risco com ganho de qualidade mensurável | arquitetura, debugging difícil, revisão de migração |
| `max` | Casos mais difíceis em que qualidade domina custo e tempo | auditoria final de mudança crítica ou plano com risco de perda de dados |

Não usar `max` como padrão. Comparar primeiro `medium`, depois `high`/`xhigh`;
reservar `max` quando a rubrica mostrar ganho. Sol, Terra e Luna compartilham a
mesma janela nominal de contexto na API; a diferença principal é capacidade,
custo e volume, não o tamanho do arquivo que cada um consegue receber.

## Regra prática

1. **Comece pelo custo eficiente** (Kimi ou GPT-5.6 Luna) se a tarefa é ler,
   extrair ou transformar muito texto/código.
2. **Passe para o julgamento** (Claude, GPT-5.6 Terra ou Sol) quando precisar
   decidir, auditar, escrever texto final ou fechar design.
3. **Use fallback** (Gemini, outro) quando um agente trava, ou quando precisa
   de segunda opinião sem viés do primeiro.
4. **Handoff sempre com trava** (`TRAVADO_POR`) e arquivos de estado
   (`ESTADO.md`, `HANDOFF.md`, `DECISOES.md`).

## Como isso costuma dar errado

- Usar o agente de contexto grande para decidir: produz slop rápido.
- Usar o agente de julgamento para varredura: queima contexto caro.
- Handoff sem trava: merge conflict ou trabalho duplicado.
- Fallback sem instrução clara: o terceiro agente não sabe qual gate seguir.
- Confundir janela de contexto com qualidade de julgamento: caber no prompt não
  significa decidir bem.
- Selecionar `max` por reflexo: aumenta latência e custo sem ganho garantido.

## Fonte da família GPT-5.6

Roteamento baseado na documentação oficial da OpenAI consultada em 2026-08-14:
`https://developers.openai.com/api/docs/guides/latest-model` e
`https://developers.openai.com/api/docs/models/compare`. Revalidar antes de
alterar preços, limites, aliases ou disponibilidade.

## Versão integrada

Este guia é a versão multi-IA do megabrain. Ele é opcional e pode ser lido
junto com `MEGABRAIN.md` seção 9 (roteamento de arquitetura), ou separado
quando o projeto só precisa do protocolo base.
