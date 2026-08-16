# Auditoria — advogado do diabo do megabrain

**Alvo:** `github.com/iriqspina/MEGAB-R-A-I-N`, branch `main`, baixado em
2026-08-16. `VERSAO.txt` publicado declarava **v4.9**.
**Método:** zip público baixado limpo, hash de todos os arquivos, execução real
dos scripts em Python 3.12, leitura cruzada entre `SKILL.md`, `MEGABRAIN.md`,
`dna/` e os `.cmd`. Nenhum achado abaixo é impressão — cada um tem comando que
reproduz.

## Placar

| Severidade | Achados | Fechados na v5.1 | Abertos |
|---|---|---|---|
| Alta — quebra em uso | 6 | 6 | 0 |
| Média — custa tempo e confiança | 5 | 5 | 0 |
| Baixa — higiene | 3 | 3 | 0 |

---

## Alta

### A1 · A skill que o agente carrega não é a do repositório

```
md5  cópia instalada   1bdc3b45…   380 linhas
md5  repositório        7a06f777…   449 linhas
```

A cópia instalada trava um caminho absoluto pessoal em nove pontos. Fora
daquela máquina, cada referência do protocolo é link morto: o agente lê
"carregue `referencias\260810_anti-slop.md`", tenta, não acha, segue sem — e a
auditoria anti-slop, que é o gate que separa entrega de slop, roda de memória.

Pior é a direção da divergência. O repositório ganhou `<MEGABRAIN_ROOT>`, gate
de versão e `5b`. A cópia instalada manteve três regras que o repositório
**perdeu**: conferir hash do arquivo carregado, testar o caminho em vez de
confiar na citação, e gravar lição sem perguntar. A regra que o repositório
apagou é exatamente a que teria detectado essa deriva.

**Fechado:** as três regras voltaram ao Gate 5; o painel mostra hash e bytes de
cada arquivo, e traz o comando de conferência da cópia instalada.

### A2 · O protocolo se auto-referencia errado

`SKILL.md` v4.9, linha 49: *"**7 (bastão)**"*. O gate do bastão é o **6**
(linha 319); o 7 é Aprender. O TL;DR também omitia `5b`, obrigatório antes de
qualquer envio externo. E `dna/dna.json` usa uma terceira numeração, com
"Reparar" promovido a gate 5 e Aprender no 8.

Três numerações no mesmo pacote. Um protocolo cujo resumo aponta para o gate
errado reprova no próprio Gate 5.

**Fechado:** cadeia única `0 → 7`, `5b` virou `5.1` dentro do Gate 5, `dna/`
regerado a partir do arquivo corrigido.

### A3 · Nenhum dos cinco `.cmd` da raiz roda

- `abrir-kimi-visual.cmd` — `cd /d <USER_HOME>`, placeholder literal.
- `sincronizar-identidade.cmd` — placeholder **e** caminho preso a
  `Python314\python.exe`.
- `novo-projeto.cmd` — `set "FONTE=<MEGABRAIN_ROOT>"`, `<PROJETOS_ROOT>`.
- `publicar-github.cmd` — commitava com mensagem fixa `"megabrain v3.1"`,
  quatro versões atrás, gravada em todo commit futuro.

São modelos vestidos de executável: quem clona dá dois cliques e recebe erro.

**Fechado:** os cinco foram para `scripts/` e reescritos com `%~dp0`,
`%USERPROFILE%` e `where python`. `novo-projeto.cmd` pergunta a pasta de
projetos **uma vez** e guarda em `scripts/.mb-projetos.cmd` (ignorado pelo
git). `publicar-github.cmd` lê a versão de `VERSAO.txt`.

### A4 · `/conclusao-megabrain` é dependência fantasma

`SKILL.md` linha 325 manda rodar `/conclusao-megabrain` como **passo 1 do Gate
6**. A skill não está no pacote — e não está de propósito:
`bin/mb-generate-template.py` lista `skills/conclusao-megabrain` no conjunto
`EXCLUIR`. O protocolo publicado depende de uma peça que o publicador remove na
porta.

Fora da máquina do autor, o Gate 6 quebra na primeira linha. Gate que quebra no
primeiro passo é gate que o agente aprende a pular inteiro.

**Fechado:** o passo virou descrição do que fazer, com a skill marcada como
atalho opcional.

### A5 · A única garantia real do protocolo não funciona no uso documentado

Achado novo desta rodada, e o mais caro dos cinco.

`bin/mb-sync.py`, v4.9 linha 136:

```python
return u.resolve_within(args_dir, Path(".").resolve())
```

A trava exige que `--dir` esteja **dentro do diretório atual**. O comando que o
próprio `SKILL.md` documenta roda o script pelo caminho da central apontando
para um projeto que vive em outro lugar do disco. Reprodução:

```
$ cd <MEGABRAIN_ROOT>
$ python bin/mb-sync.py --dir /caminho/do/projeto status
ERRO: caminho fora da área permitida
exit=1
```

O `SKILL.md` chama isso de "garantia de script em vez de disciplina de
markdown", e `MEGABRAIN.md` faz disso a regra de ouro 21. Na prática, quem
seguiu a documentação recebeu erro, e a trava virou o que ela existia para
substituir: um bloco de markdown editado na mão.

A contenção também não protegia nada — o caminho vem do próprio usuário, e a
escrita é sempre um `HANDOFF.md` dentro da pasta que ele apontou.

**Fechado:** `--dir` agora aceita qualquer pasta existente, com erro claro para
caminho inexistente ou arquivo. Coberto por teste de regressão
(`test_dir_fora_do_cwd_funciona`), que falha contra o script v4.9.

Bônus da mesma leitura: sem arquivo de identidade, o `lock` gravava
`USUARIO: <USUARIO>` literal no `HANDOFF.md` — a trava não identificava
ninguém. Agora cai para o login do sistema operacional.

### A6 · O gerador do relatório DNA quebra ao rodar

Achado ao regenerar o DNA para fechar o M5. `bin/mb-relatorio-dna.py` linha
159 declara uma aresta `("g7", "g8")` no grafo de nós. `g8` nunca existiu na
lista `NOS` — resíduo da numeração antiga (0 a 8, com "Reparar" como gate
separado) que o A2 já tinha identificado no `dna.json`, só que aqui o resíduo
estava no **código do gerador**, não no artefato gerado.

```
KeyError: 'g8'
```

A ferramenta que existe para consertar o artefato desatualizado (M5) estava
ela mesma desatualizada, e do mesmo jeito — numeração de gate presa a uma
versão anterior do protocolo. Confirma o padrão do A1/A2: a deriva de versão
não é um evento isolado, é a falha default de qualquer cópia que não roda
teste.

**Fechado:** aresta removida; `dna/` regenerado e validado em v5.1.

---

## Média

### M1 · Dois arquivos, mesmo hash, duas fontes futuras

`SKILL.md` == `skills/megabrain/SKILL.md` (`7a06f777…`, idênticos).
`MEGABRAIN.md` == `260810_MEGABRAIN.md` (`bfefcf72…`, idênticos).

Hoje é redundância. Na primeira edição em um só lado, é fork silencioso — o
mesmo mecanismo do A1, agora dentro do próprio repo. Os scripts já elegeram um
lado: `mb-check-version.py` e `mb-sync-projeto-para-central.py` mapeiam
`skills/megabrain/SKILL.md`. O da raiz é a cópia sem dono.

**Fechado:** cópias sem dono removidas.

### M2 · Duas versões do mesmo script na mesma pasta

`bin/mb-sync.py` (9.594 bytes) e `bin/260810_mb-sync.py` (5.389 bytes).

O antigo não tem campo `USUARIO`, aceita `release` sem `--agente` e não tem
`--force` protegido: libera trava alheia sem perguntar. Manter a versão insegura
ao lado, com nome quase igual, é esperar um autocomplete infeliz.

**Fechado:** o antigo saiu do pacote.

### M3 · `requirements.txt` promete dez dependências que ninguém importa

`filelock`, `platformdirs`, `mistune`, `nh3`, `pydantic`, `structlog`,
`watchdog`, `rich`, `pytest`, `ruff` — busca em `bin/`: **zero ocorrências**.

```
grep -rl "filelock\|pydantic\|structlog\|watchdog\|mistune" bin/   # vazio
```

`pip install -r requirements.txt` baixa onze pacotes e não muda uma linha de
comportamento. É lista de intenções com nome de arquivo de build.

**Fechado:** virou `docs/dependencias-sugeridas.txt`, com a nota de que o núcleo
roda em stdlib pura.

### M4 · Zero teste, num pacote que pedia `pytest`

`mb-sync.py` é o componente que transforma disciplina em garantia. Não havia um
único teste provando que a trava trava, que `release` recusa trava alheia, ou
que `status` devolve o código de saída certo.

Regra de ouro 21 do `MEGABRAIN.md`: garantia real é script, não markdown. O
corolário que faltava: **script sem teste é markdown com extensão `.py`** — e o
A5 é a prova, porque passou despercebido por quatro versões.

**Fechado:** `tests/test_mb_sync.py`, 7 casos, roda sem dependência
(`python tests/test_mb_sync.py`). Contra a v4.9, falha.

### M5 · A vitrine estava quatro versões atrás

`VERSAO.txt` dizia v4.9; `dna/dna.json` e `dna/RELATORIO-DNA.html` diziam v4.5,
gerados em 2026-08-14, com a numeração errada do A2. O `dna/README.md` diz
"nunca editar na mão; rode o script de novo" — e o script não foi rodado.

Artefato gerado que não é regerado no Gate 6 é artefato que mente.

**Fechado:** `dna/` e o painel são regerados no mesmo ciclo em que a versão sobe.

---

## Baixa

### B1 · Raiz com 18 entradas e duas convenções de nome

Cinco `.cmd` com prefixo `260810_` e um sem. Prefixo de data faz sentido em
documento que se acumula; em executável chamado pelo nome, é ruído — e a
convenção nem era seguida por todos. `LEIAME.md` existia só para dizer que o
conteúdo está no `README.md`, justificando-se com *"fica só por não poder ser
apagado depois de escrito"*, o que não é verdade.

**Fechado:** raiz com 7 entradas, `.cmd` todos em `scripts/`, sem prefixo.

### B2 · `LEIAME.txt` estava na fonte, mas só faz sentido na cópia

Dizia "NÃO EDITE os arquivos desta pasta / a fonte manda". Correto dentro de
`projeto/MEGABRAIN/`. Na raiz da fonte, instruía a não editar a própria fonte.

**Fechado:** virou `modelos/LEIAME-copia-de-projeto.txt`, copiado pelo
`novo-projeto.cmd` para dentro do projeto derivado.

### B3 · O README descrevia `bin/` melhor que o `SKILL.md`

Quem lê o protocolo pelo agente nunca descobria que existe `mb-aspirador.py`,
`mb-relatorio-projeto.py` ou `mb-backup-central.py`. A seção 9 falava em
"script em `bin/`" de forma genérica. As ferramentas existem e são boas —
faltava a linha que as convoca.

**Fechado:** o painel lista toda mecânica com o comando pronto para copiar, já
com o caminho da instalação do usuário.

---

## O que não vou reclamar

O núcleo está certo, e isso é raro. Gates que exigem reescrita em vez de
anúncio. `DECISOES.md` append-only guardando a alternativa descartada, que é o
único conteúdo do arquivo que envelhece bem. Contexto tratado como orçamento
compartilhado entre agentes. Reparo limitado a uma rodada, com a explicação
certa: loop de autocrítica converge para média homogênea. O léxico anti-slop é
específico o bastante para ser executável — a maioria dos guias desse tipo para
em "evite jargão".

Os treze achados são de manutenção e empacotamento, não de tese. É a diferença
entre um protocolo errado e um protocolo certo que envelheceu quatro versões em
duas semanas — sem teste que avisasse.

## A crítica que sobra depois de tudo corrigido

**O protocolo não tem gate para si mesmo.** Ele manda auditar entrega,
verificar caminho, registrar decisão — e nada disso apontava para o próprio
pacote. O A5 sobreviveu quatro versões porque ninguém rodou `mb-sync.py` num
projeto de verdade depois de mexer nele.

A correção estrutural não é uma regra a mais no `SKILL.md`. É o que a v5.1 faz
agora: `tests/` roda em segundos, `mb-arrumar.py --verificar` procura referência
quebrada, e o painel mostra o hash da cópia instalada ao lado do hash do repo.
Três garantias de script contra a única classe de erro que o protocolo, por
construção, não conseguia enxergar sozinho.
