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
| GPT-4o / GPT-5 | Fallback, segunda opinião, geração de imagem | Tarefa que exige leitura de projeto inteiro |
| Gemini | Fallback opcional, multimodal | Não é membro fixo; usar só quando os outros falham |

## Regra prática

1. **Comece pelo contexto grande** (Kimi, GPT) se a tarefa é ler, extrair ou
   transformar muito texto/código.
2. **Passe para o julgamento** (Claude) quando precisar decidir, auditar,
   escrever texto final ou fechar design.
3. **Use fallback** (Gemini, outro) quando um agente trava, ou quando precisa
   de segunda opinião sem viés do primeiro.
4. **Handoff sempre com trava** (`TRAVADO_POR`) e arquivos de estado
   (`ESTADO.md`, `HANDOFF.md`, `DECISOES.md`).

## Como isso costuma dar errado

- Usar o agente de contexto grande para decidir: produz slop rápido.
- Usar o agente de julgamento para varredura: queima contexto caro.
- Handoff sem trava: merge conflict ou trabalho duplicado.
- Fallback sem instrução clara: o terceiro agente não sabe qual gate seguir.

## Versão integrada

Este guia é a versão multi-IA do megabrain. Ele é opcional e pode ser lido
junto com `MEGABRAIN.md` seção 9 (roteamento de arquitetura), ou separado
quando o projeto só precisa do protocolo base.
