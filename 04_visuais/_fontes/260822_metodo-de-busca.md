# Como eu busco referência a partir do que você fala

**260822.** Escrito porque você pediu para eu *aprender* a buscar do seu jeito.
Isto é o procedimento; o acervo que ele produz está em `09_visuais/`.

---

## O passo que quase todo mundo pula: traduzir antes de buscar

Você não fala em query, fala em sensação. Buscar a sensação literal no Google
devolve Dribbble. O que funciona é traduzir cada frase sua em **três coisas**
antes de abrir qualquer aba:

| você disse | eixo | negativo | território |
|---|---|---|---|
| "parece papel, acadêmico" | cor · substrato | ❌ marfim, caramelo, bege, serifa editorial | — |
| "futurista visualmente" | cor · textura · movimento | ❌ preto+neon (é o default de IA) | FUI, dev tools, dark UI real |
| "dinâmico" | movimento | ❌ animação decorativa/autoplay | scroll-driven, view transitions, feedback de estado |
| "compacto, acho rápido" | layout · densidade | ❌ card grande com muito respiro | observabilidade, terminal, jogo |
| "hierarquizado" | layout · tipografia | ❌ tudo do mesmo peso | design systems com escala documentada |
| "verde wildfire + vinho, corpo neutro" | cor | ❌ acento único; ❌ verde-sobre-preto puro | paletas de 3+ canais semânticos |

**O negativo é mais valioso que o positivo.** "Futurista" tem mil interpretações;
"futurista que não seja preto com neon" tem umas cinco. Cada ❌ que você me dá
corta 80% do espaço de busca — é por isso que a pasta `02_nao/` existe.

---

## Os cinco movimentos

**1. Territórios, não palavras-chave.** Nunca busco "dashboard futurista". Busco
por *onde o problema já foi resolvido*: cinema (FUI), instrumentação real
(aviação, monitoramento médico), jogos (UI sob estresse), observabilidade
(densidade extrema), terminal (limite de mono). Cada território devolve um
vocabulário diferente para o mesmo eixo.

**2. Varredura paralela e cega.** Disparo agentes em territórios distintos ao
mesmo tempo, sem eles saberem o que os outros acharam. Convergência entre dois
territórios independentes é sinal forte; o que aparece só num é curiosidade.

**3. Verificação por HTTP, e falha declarada.** Toda URL é testada. O que não
carrega **entra no relatório como falha** — nunca como referência descrita de
memória. Já bloquearam a busca: `lapa.ninja` (Cloudflare), `siteinspire`
(checkpoint), `refero.design` (SPA sem SSR — mas `styles.refero.design` é SSR e
funciona), `pinterest.com` (robots.txt), `fui.wtf` (DNS não resolve).

**4. Extração de mecanismo, não de screenshot.** A pergunta nunca é "é bonito?",
é **"que peça daqui eu consigo destacar e reusar?"**. Uma referência sem
mecanismo extraível é humor, não referência. Por isso cada specimen tem
*roubar* e *não roubar*: metade do valor está em saber o que ali é cenografia.

**5. Specimen no lugar de print.** Print de landing é 80% hero, envelhece com o
site e não dá pra comparar. O specimen reconstrói só o mecanismo, no mesmo
formato pra todos — e carrega a URL, porque o specimen é a leitura e o site é a
verdade.

---

## O que ainda não consigo, e o que resolve

| limite | por quê | como você destrava |
|---|---|---|
| **Screenshot de site real** | o container não alcança a web aberta (proxy só de registries) | rodar a captura na sua máquina, ou você arrastar prints pra `00_entrada/` |
| **Pinterest** | `robots.txt` proíbe acesso automatizado, e eu não contorno bloqueio | exportar os pins (Configurações → Privacidade → Baixar dados) e soltar em `00_entrada/`, ou colar 5–10 links diretos de imagem |
| **SPA pesada** (Modal, fal, Rive…) | WebFetch não executa JS; volta texto de marketing | são exatamente os casos em que o specimen ganha do print |

---

## Sobre o seu board do Pinterest

Não consegui ler — o Pinterest bloqueia leitura automatizada por `robots.txt`, e
eu não uso caminho alternativo para furar bloqueio declarado.

**Honestamente: um board de "site portfólio" provavelmente é geral demais para
este trabalho.** Portfólio de designer e painel de monitoramento contínuo têm
objetivos opostos — um quer impacto na primeira dobra e respiro, o outro quer
densidade e leitura rápida sob repetição. O que dele *serve* é o seu **gosto de
cor, tipo e textura**, não o layout.

O que eu faria: você abre o board, escolhe **8 a 12 pins** que representam a
sensação (não o layout), joga em `00_entrada/`, e eu extraio o eixo de cada um.
Doze pins escolhidos por você valem mais que duzentos que eu varri sozinho.

---

## Sugestão de estrutura (você pediu)

Sua pergunta real era: *como facilitar pra eu pegar as coisas?* Três regras.

**1. Separe acervo de implementação.** `09_visuais/` é seu (imagem, curadoria,
sim/não). `modelos/visuais/` é do código (tokens, mecânicas). Referência nunca
entra no código; token nunca entra no acervo. A ponte é `09_visuais/03_temas/`,
que registra *quais referências geraram qual tema*.

**2. Estado é pasta; assunto é subpasta.** Você quer arrastar — então o primeiro
nível tem que ser o que muda quando você decide (`entrada` → `sim`/`não`).
O eixo (cor, tipo, layout…) é o segundo nível, dentro de `sim`. O contrário
obrigaria a mover arquivo toda vez que você mudasse de ideia sobre o assunto.

**3. Nada aqui pode quebrar o megabrain.** Nenhum script lê `09_visuais/`.
Renomeie, mova, apague. O único acoplamento é textual: `03_temas/` *cita* a
referência que o inspirou — se você mover, o tema continua funcionando e só
perde a nota de proveniência.

**O que eu ainda mudaria mais pra frente**, quando o acervo passar de ~100 itens:
um `INDICE.md` gerado por script varrendo os nomes de arquivo, para você
pesquisar por eixo sem abrir pasta. Antes disso, é burocracia sem retorno.
