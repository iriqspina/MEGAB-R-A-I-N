# GerenteNeuron

Chat unificado local para todas as IAs + gerente geral de projetos. Roda no
navegador, só com a stdlib do Python. Nenhuma credencial sai da máquina.

## Primeira vez

```
configurar.cmd
```

Um comando só. Ele cria o ambiente com `cryptography`, cria o cofre, pergunta
cada API key (sem ecoar na tela), testa a conectividade de cada provedor e
confere a tabela de preços. Pode rodar de novo quando quiser: pula o que já
está feito e só pede o que falta.

Depois, `run.cmd` abre o app e pede a senha mestre.

**A chave de recuperação é gravada em
`%USERPROFILE%\gerenteneuron-chave-de-recuperacao.txt`, fora da pasta do
cofre — de propósito.** Cofre e chave na mesma pasta anulam a senha mestre para
quem tem acesso ao disco. Mova o arquivo para um pendrive ou para o seu
gerenciador de senhas.

<details>
<summary>Passo a passo manual, se preferir</summary>

```
python gerenteneuron\setup-crypto.py
gerenteneuron\.venv\Scripts\python gerenteneuron\setup-vault.py
gerenteneuron\.venv\Scripts\python gerenteneuron\mb-vault.py add OPENAI_API_KEY sk-...
gerenteneuron\.venv\Scripts\python gerenteneuron\mb-vault.py add ANTHROPIC_API_KEY sk-ant-...
```

`setup-vault.py --saida <caminho>` escolhe onde gravar a chave de recuperação;
ele recusa qualquer caminho dentro da pasta do cofre.
</details>

## Recuperação de senha

Com a chave de recuperação em mãos:

```
gerenteneuron\.venv\Scripts\python gerenteneuron\mb-vault.py reset --recovery <chave>
```

Aceita a chave crua ou o conteúdo inteiro do arquivo colado. No app, o botão
"Esqueci a senha" faz o mesmo. A chave usada é queimada e outra é gerada, também
fora da pasta do cofre.

## Abas

### Chat IA

- Modo **Auto**: escolhe o modelo mais barato da classe adequada à pergunta.
- Modo **Manual**: você escolhe o provedor/modelo.
- **Reforçar**: reenvia para a classe acima (`cheap → standard → deep`).
- **👍/👎**: alimenta `data/feedback.jsonl` e o `/api/eval`.
- O rodapé de cada resposta mostra modelo, custo estimado e quais candidatos
  foram pulados antes — a fila de fallback deixa de ser invisível.

### Gerente

- Recebe pedidos gerais e identifica projeto + intenção (`status`, `acao`,
  `pergunta`, `geral`).
- Projetos ficam em `projetos.json` (não versionado). O app não varre o disco.

## Modelos e preços

`pricing.json` é a fonte única: lista de modelos, classe (`quick`, `standard`,
`deep`) e preço por 1M de tokens. **A ordem da fila do roteador é derivada
desse arquivo**, do mais barato ao mais caro — trocar de modelo é editar o JSON,
não o código.

```
python gerenteneuron/mb-modelos.py --listar     # tabela ordenada por custo
python gerenteneuron/mb-modelos.py --conferir   # bate contra a API dos provedores
```

`--conferir` sai com código 1 quando a tabela está vencida (`revalidar_em_dias`)
ou lista modelo que o provedor não oferece mais. O app mostra o mesmo aviso no
topo do chat. Preço de modelo muda; tabela velha faz o roteador "economizar"
com número inventado.

Preços atuais conferidos em **2026-08-16** — fontes registradas dentro do
próprio `pricing.json`.

## Estratégia de roteamento

| Sinal na mensagem | Estratégia | Classe |
|---|---|---|
| código, debug, traceback, refactor | `local_code` | local primeiro, depois `standard` |
| resumir, extrair, traduzir, pergunta curta | `cheap` | `quick` |
| explanação, síntese, texto médio | `standard` | `standard` |
| arquitetura, auditoria, decisão, trade-off, texto longo | `deep` | `deep` |

Dentro da classe, o mais barato disponível vai primeiro. Provedor sem key nunca
entra na fila. Se tudo falhar, o mock responde — o app nunca fica mudo.

## Testes

```
testar.cmd
```
ou
```
python gerenteneuron/tests/test_gerenteneuron.py
```

37 casos, stdlib pura, sem dependência. Cobrem: integridade e ordenação de
`pricing.json`, classificação de estratégia, montagem da fila, propagação do
histórico, checagem de origem HTTP, casamento de projeto e o ciclo completo do
cofre — criação, senha errada, recuperação, queima da chave usada e a garantia
de que a chave de recuperação nunca cai dentro da pasta do cofre. Rode antes de
qualquer commit que toque no roteador ou no cofre.

## Segurança

- Credenciais ficam cifradas no cofre local (Fernet + PBKDF2 600k).
- A chave de recuperação nasce fora da pasta do cofre, com permissão 0600.
  `setup-vault.py` recusa gravá-la lá dentro, e o app avisa no console e em
  `/api/vault/status` se encontrar uma sobra de instalação antiga.
- `.env`, `projetos.json`, `data/`, `vault/` e `.venv/` estão no `.gitignore`.
- O servidor escuta só em `127.0.0.1` e recusa requisição com `Origin` ou `Host`
  de fora do localhost — sem isso, qualquer aba aberta no navegador conseguia
  falar com a API e gastar suas chaves.
- `/api/vault/unlock` trava por 5 minutos após 5 senhas erradas.
- Gravar chave pelo diálogo "Configurar chaves" escreve `.env` em texto puro.
  Funciona, mas o cofre é o caminho recomendado.

## Aprendizado e qualidade

- Feedback em `data/feedback.jsonl`; `/api/eval` gera estatísticas e sugestões.
- `aspirar.cmd` roda `mb-aspirador.py` no código do app.
- `LICOES.md` guarda o que já deu errado aqui.
