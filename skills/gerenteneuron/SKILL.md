---
name: gerenteneuron
description: Gerente geral dos projetos do usuário. Acesso principal pelo app local GerenteNeuron. Recebe pedidos gerais, identifica qual projeto/skill ativar (/portfolio, /rodada, /financeirodasilva, /megabrain etc.) e monta o próximo passo. Também funciona como chat multi-IA quando o pedido não é de projeto.
---

# /gerenteneuron — gerente geral de projetos + chat multi-IA

O GerenteNeuron é o ponto único de entrada. Ele pode operar em dois modos:

1. **Gerente de projetos**: você manda um pedido geral; ele identifica o projeto,
   a intenção (status, ação, pergunta) e diz qual skill invocar.
2. **Chat multi-IA**: você conversa com uma ou várias IAs; ele escolhe o modelo
   mais barato capaz de responder bem.

## Quando usar

- "Quero ver o status de tudo".
- "Atualiza o portfólio" / "como está o Financeiro da Silva?" / "revisa a rodada".
- "Preciso de um chat só para falar com todas as IAs".
- "Abre o GerenteNeuron".

## Como abrir

```
/gerenteneuron
```

Isso inicia o app local no navegador:

```
python <MEGABRAIN_ROOT>/gerenteneuron/app.py
```

## O que o app faz

### Aba "Chat IA"

- Envia sua mensagem para o modelo escolhido pelo roteador de custo/capacidade.
- Permite override manual do provedor/modelo.
- Conecta OpenAI (ChatGPT), Anthropic (Claude), Gemini, Moonshot/Kimi e Ollama local.
- **Local-first para código**: Ollama/Qwen processa código, debug e refactor sem gastar tokens pagos.
- **Boost**: clique em "Reforçar" se a resposta for fraca; o app reenvia para um modelo maior.
- **Feedback**: 👍/👎 alimenta o aprendizado de rotas.

### Aba "Gerente"

- Lê `gerenteneuron/projetos.json` para saber quais projetos estão ativos.
- Classifica a intenção: `status`, `acao`, `pergunta`, `geral`.
- Identifica o projeto pela mensagem (palavras-chave + nome).
- Responde com:
  - qual projeto foi reconhecido;
  - qual skill invocar (`/portfolio`, `/rodada`, `/financeirodasilva`, `/tlou`, `/megabrain` etc.);
  - o prompt pronto para você colar na skill.

## Configurar projetos ativos

Edite ou crie `gerenteneuron/projetos.json` (modelo em `projetos.json.example`):

```json
{
  "projetos": [
    {
      "id": "portfolio",
      "nome": "Portfólio",
      "skill": "/portfolio",
      "descricao": "Site de portfólio no WordPress.",
      "keywords": ["portfolio", "site", "wordpress", "case"]
    }
  ]
}
```

O GerenteNeuron só conhece os projetos listados ali. Não varre seu disco.

## Regras

- O GerenteNeuron **orquestra**, não substitui as skills. Quando ele apontar
  para `/portfolio`, `/rodada` ou `/megabrain`, a execução real continua na
  skill de destino, com seus próprios gates.
- Para entregas (código, design, documento), a skill apontada ainda roda
  enquadrar → auditar → verificar → passar o bastão.
- Nunca armazene credenciais em arquivo versionado.

## Como isso costuma dar errado

- Não cadastrar projetos em `projetos.json` e esperar que o GerenteNeuron adivinhe.
- Confundir os dois modos: pedir "status do portfólio" na aba Chat IA faz o
  roteador escolher um modelo, mas não invoca a skill `/portfolio`.
- Esquecer que o GerenteNeuron não executa ações sozinho — ele prepara o
  próximo passo para a skill correta.
