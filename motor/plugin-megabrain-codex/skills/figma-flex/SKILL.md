---
name: figma-flex
description: Router agnóstico de contorno de limites de capability. Use quando a IA atual não conseguir executar diretamente o que o usuário pediu — no Figma, no PC, em automações ou em qualquer ferramenta. A skill fornece um protocolo micro-genérico que qualquer agente pode seguir inspecionando suas próprias tools, sem assumir nome específico de tool nem arquitetura.
---

# /figma-flex — contornar limites de capability (protocolo micro-genérico)

Esta skill não dá superpoderes. Ela fornece um roteiro que qualquer IA pode seguir quando a própria arquitetura não tem a capability nativa para executar um pedido.

**Princípio:** nunca assuma que outra IA tem as mesmas tools que você. Sempre inspecione as tools disponíveis na sessão atual antes de decidir.

## 1 · Quando invocar

- Usuário pede "faz igual o [outro agente]" ou "use meu PC como o [outro agente]".
- Usuário pede para abrir app, clicar em botão, navegar na UI, editar arquivo em app fechado, ou executar ação que não tem tool nativa.
- Antes de prometer: abrir Figma, trocar arquivo, editar canvas, exportar asset, rodar script no desktop, etc.
- Uma tool retorna erro de capability não suportada ou retorna menos do que o esperado.
- Usuário diz "mas o outro agente consegue...".

## 2 · Algoritmo de decisão (seguir na ordem)

```
PASSO 1: LISTAR TOOLS DISPONÍVEIS
- Obtenha a lista de tools/functions/MCP servers disponíveis nesta sessão.
- Anote nomes, categorias e o que cada uma faz.
- Se houver documentação de tools, leia antes de prosseguir.

PASSO 2: CLASSIFICAR A TAREFA PELO VERBO
Leia o pedido do usuário e classifique o verbo principal:
- LER    → precisa de tool de leitura (arquivo, API, metadata, screenshot)
- ESCREVER → precisa de tool de escrita (editar arquivo, editar node, API write)
- ABRIR/FOCAR/CLICAR → precisa de controle de UI ou automação
- EXECUTAR → precisa de tool de execução de código/comando
- AUTENTICAR → precisa de interação humana (OAuth, 2FA, biometria)

PASSO 3: MAPEAR CAPABILITY NATIVA
Para cada sub-tarefa, pergunte:
- "Eu tenho uma tool que faz isso diretamente?"
- Se SIM → execute.
- Se NÃO → vá para PASSO 4.

PASSO 4: GERAR MENU DE CONTORNO
Ordene as alternativas do menor para o maior esforço do usuário:
A. Leitura/auditoria parcial — o que a IA atual consegue sozinha.
B. Script/plugin local — usuário executa no próprio PC; IA escreve o código.
C. Outro agente/ferramenta — que tem a capability nativa.
D. Ação manual do usuário — IA instrui; usuário clica/arrasta/aprova.
E. Inviável — falta permissão, API, plano pago ou não existe caminho seguro.

PASSO 5: INDICAR O USUÁRIO E EXECUTAR A ESCOLHA
- Apresente o menu com a alternativa recomendada primeiro.
- Explique por que cada uma funciona ou não.
- Pergunte qual prefere.
- Execute apenas a escolha. Não execute múltiplas alternativas ao mesmo tempo.
```

## 3 · Como inspecionar suas próprias tools

Cada agente faz isso de forma diferente. Tente nesta ordem:

1. **Listar tools disponíveis** — procure por função equivalente a listar tools/MCP servers/ferramentas.
2. **Ler documentação de tools** — se existir, leia antes de usar.
3. **Testar a tool mais barata** — faça uma chamada de leitura/validação antes de prometer resultados.
4. **Se não souber como listar tools**, execute o equivalente a `help`, `--help`, ou consulte o sistema.

**Nunca assuma:** se você vê `mcp__figma__*` em outra sessão, isso não garante que você tenha agora. Verifique.

## 4 · Classificação de tarefas por domínio

Use esta tabela para classificar rapidamente. Substitua os exemplos de tool pelos nomes reais que você encontrou no PASSO 1.

| Domínio | LER | ESCREVER | ABRIR/CLICAR | EXECUTAR | AUTENTICAR |
|---|---|---|---|---|---|
| **Arquivos locais** | tool de leitura de arquivo | tool de edição/escrita de arquivo | usuário abre app | shell/execução | raro |
| **Figma** | MCP Figma local (metadata, screenshot, design context) | plugin Figma local ou outro agente | usuário navega no app | plugin/script | OAuth remoto |
| **Navegador/web** | fetch/HTTP GET | API POST/PUT via HTTP | usuário interage | script headless | OAuth/API key |
| **Windows desktop** | ler arquivos, listar processos | editar arquivos | usuário ou script de automação | shell/script | biometria/2FA |
| **Serviços online** | API GET | API POST/PUT/PATCH | painel web | webhook/script | OAuth |

## 5 · Matriz de decisão genérica

| Situação | O que fazer | Exemplo |
|---|---|---|
| Tenho tool nativa de leitura | Faço sozinho | Ler arquivo, screenshot de frame |
| Tenho tool nativa de escrita | Faço sozinho, mas confirme se for destrutivo | Editar arquivo de projeto |
| Não tenho tool de escrita para o app | Menu: script/plugin / outro agente / manual | Editar texto no Figma |
| Não tenho controle de UI | Menu: usuário manual / script de automação / outro agente | Abrir Photoshop, clicar menu |
| Requer autenticação humana | Sempre usuário aprova; IA só prepara | OAuth, 2FA, login |
| Tool nativa existe mas falha | Diagnostique: app aberto? permissão? formato? | MCP Figma retorna erro |
| Nenhuma alternativa viável | Diga claramente por quê e o que mudaria | App sem API, sem automação segura |

## 6 · Protocolo de indicação ao usuário

Sempre que precisar de escolha, use esta estrutura mínima:

```
"Para fazer [X], eu não consigo sozinho porque [capability ausente].
Alternativas:
- A) [o que a IA faz sozinho, se houver]
- B) [usuário executa script/plugin que a IA prepara]
- C) [outro agente/ferramenta com a capability nativa]
- D) [usuário faz manualmente]
- E) [inviável — motivo]
Qual prefere?"
```

Nunca prometa sem confirmar quando envolver:
- abrir/alterar app no desktop;
- OAuth/autenticação;
- plugin/script sendo executado;
- outro agente assumindo;
- alteração fora do escopo atual.

## 7 · Figma — exemplo de aplicação

### 7.1 · Inspecionar tools de Figma

Procure por tools equivalentes a:
- `get_metadata` — listar páginas/frames.
- `get_design_context` — extrair tokens/medidas/cores.
- `get_screenshot` — renderizar node.
- `get_variable_defs`, `get_motion_context`, `get_figjam` — extras.

Se não encontrar nenhuma, o Figma MCP não está disponível. Vá para contorno manual ou outro agente.

### 7.2 · Checklist de leitura

- [ ] Servidor local responde (equivalente a `curl http://127.0.0.1:3845/mcp` retorna `400`).
- [ ] Chamada de metadata retorna o arquivo esperado.
- [ ] O arquivo aberto é o que o usuário quer.

### 7.3 · Escrita no canvas

O MCP Figma local é tipicamente read-only. Se você não tem tool de escrita:

| Caminho | Quem executa |
|---|---|
| Plugin Figma local | usuário roda; IA escreve o código |
| Outro agente com capability de escrita | outro agente |
| Figma REST API | IA via HTTP, mas limitada |
| Automação de UI | usuário ou script frágil |

## 8 · PC / Windows — exemplo de aplicação

### 8.1 · Inspecionar tools de PC

Procure por tools equivalentes a:
- Leitura/escrita de arquivo.
- Execução shell/comando.
- Listar processos/janelas.
- Controle de UI (raro).

### 8.2 · Contorno padrão

1. **Arquivos/comandos** → use tool nativa de leitura/execução.
2. **UI de app** → usuário manual ou script que a IA prepara.
3. **App com API** → use a API via HTTP.
4. **Autenticação** → usuário aprova; IA prepara o fluxo.

## 9 · Anti-padrões (não fazer)

- ❌ "Não consigo." sem explicar por quê ou oferecer alternativa.
- ❌ "Vou fazer" sem ter a tool nativa.
- ❌ Assumir que outra IA tem as mesmas tools.
- ❌ Executar múltiplas alternativas sem escolha do usuário.
- ❌ Dar desculpas genéricas como "limitações técnicas" sem especificar.

## 10 · Checklist final antes de agir

- [ ] Listei minhas tools disponíveis.
- [ ] Classifiquei o pedido pelo verbo (ler/escrever/abrir/executar/autenticar).
- [ ] Verifiquei se tenho tool nativa para cada sub-tarefa.
- [ ] Se não tenho, gerei menu de contorno.
- [ ] Indiquei o usuário antes de escolher.
- [ ] Execute apenas a alternativa escolhida.
