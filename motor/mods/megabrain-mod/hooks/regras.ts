// Regras do megabrain-mod: funções puras (sem `$`), testadas em tests/.
// Os valores (listas, liga/desliga) ficam em AJUSTES.ts, não aqui.

import type { Auditoria, Projeto, Rumo, Sessao, Sessoes } from '../types'

export type ModoGuarda = 'perguntar' | 'bloquear' | 'desligado'

export type Ajustes = {
  faixa: boolean
  bussola: boolean
  sessoes: boolean
  sessoesJanelaHoras: number
  sessoesAtualizarSegundos: number
  python: string
  vigiaSlop: boolean
  avisarOClaude: boolean
  palavrasBanidas: readonly string[]
  exigirTldr: boolean
  tldrAPartirDeLinhas: number
  guardaComandos: ModoGuarda
  comandosVigiados: readonly string[]
  protegerArquivos: boolean
  arquivosSecretos: readonly string[]
  pastasGeradas: readonly string[]
  lembrarCmd: boolean
  exigirDataNoNome: boolean
  pastasComData: readonly string[]
  bastaoAPartirDe: number
  pastasDeEstado: readonly string[]
}

export const ARQUIVOS_DE_ESTADO = ['ESTADO.md', 'HANDOFF.md', 'DECISOES.md', 'LICOES.md'] as const
export type ArquivoDeEstado = (typeof ARQUIVOS_DE_ESTADO)[number]

export const AUDITORIA_VAZIA: Auditoria = {
  respostas: 0,
  comSlop: 0,
  semTldr: 0,
  ultimasPalavras: [],
  ultimaSemTldr: false,
}

// ─── texto ──────────────────────────────────────────────────────────

const escapar = (s: string): string => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

export const semAcento = (s: string): string =>
  s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

/** Tira blocos ``` e `trechos` de código: termo citado ali não é slop. */
export const limparCodigo = (texto: string): string =>
  texto.replace(/```[\s\S]*?```/g, ' ').replace(/`[^`\n]*`/g, ' ')

/** Texto normalizado + de onde veio cada caractere, pra devolver a palavra original. */
const mapear = (texto: string): { norma: string; origem: number[] } => {
  let norma = ''
  const origem: number[] = []
  for (let i = 0; i < texto.length; i++) {
    for (const ch of semAcento(texto.charAt(i))) {
      norma += ch
      origem.push(i)
    }
  }
  return { norma, origem }
}

const LETRA = /[a-z0-9]/

/**
 * Termos banidos achados no texto, como aparecem nele, sem repetir.
 * Item com * no fim casa qualquer final; sem *, só a palavra/frase exata.
 */
export const acharSlop = (texto: string, lista: readonly string[]): string[] => {
  const limpo = limparCodigo(texto)
  const { norma, origem } = mapear(limpo)
  const achados: string[] = []
  const vistos = new Set<string>()
  for (const item of lista) {
    const bruto = item.trim()
    const prefixo = bruto.endsWith('*')
    const termo = semAcento(prefixo ? bruto.slice(0, -1) : bruto).trim()
    if (termo === '') continue
    const corpo = termo.split(/\s+/).map(escapar).join('\\s+')
    const fim = prefixo ? '' : '(?![a-z0-9])'
    const achado = new RegExp(`(^|[^a-z0-9])(${corpo})${fim}`).exec(norma)
    if (achado === null) continue
    const inicio = achado.index + (achado[1] ?? '').length
    let final = inicio + (achado[2] ?? '').length
    if (prefixo) while (final < norma.length && LETRA.test(norma.charAt(final))) final++
    const de = origem[inicio] ?? 0
    const ate = (origem[final - 1] ?? de) + 1
    const palavra = limpo.slice(de, ate).replace(/\s+/g, ' ')
    const chave = semAcento(palavra)
    if (!vistos.has(chave)) {
      vistos.add(chave)
      achados.push(palavra)
    }
  }
  return achados
}

/**
 * A resposta abre com TL;DR? null quando é curta (papo, N0) e não precisa.
 * Aceita o TL;DR na 1ª ou 2ª linha não vazia (um título antes passa). As linhas
 * de abertura que o contrato manda pôr antes dele (🪞 ECO, 🧭 bússola) não contam.
 */
export const temTldr = (texto: string, aPartirDeLinhas: number): boolean | null => {
  const linhas = texto
    .split('\n')
    .map(l => l.trim())
    .filter(l => l !== '')
  if (linhas.length < aPartirDeLinhas) return null
  let inicio = 0
  while (/^(🪞|🧭)/u.test(linhas[inicio] ?? '')) inicio += 1
  return linhas.slice(inicio, inicio + 2).some(l => /^tl\s*;?\s*dr/i.test(l.replace(/^[^a-z0-9]+/i, '')))
}

// ─── comandos ───────────────────────────────────────────────────────

/** Um comando quebrado em trechos (&&, ||, ;, |, quebra de linha), cada um em palavras. */
const trechos = (comando: string): string[][] =>
  semAcento(comando)
    .split(/&&|\|\||[;|\n]/)
    .map(t =>
      t
        .trim()
        .split(/\s+/)
        .map(p => p.replace(/^["'(]+|["')]+$/g, ''))
        .filter(p => p !== ''),
    )

const casa = (pedido: string, palavra: string): boolean =>
  pedido.startsWith('-')
    ? palavra.startsWith(pedido)
    : palavra === pedido || palavra === `${pedido}.exe` || palavra.endsWith(`/${pedido}`) || palavra.endsWith(`\\${pedido}`)

/**
 * O item da lista que o comando aciona, se algum: as palavras do item têm
 * que aparecer nessa ordem dentro de um mesmo trecho do comando.
 * Flag (-r) casa pelo começo: "rm -r" pega "rm -rf".
 */
export const comandoVigiado = (comando: string, lista: readonly string[]): string | undefined => {
  const partes = trechos(comando)
  return lista.find(item => {
    const pedido = semAcento(item).trim().split(/\s+/).filter(p => p !== '')
    if (pedido.length === 0) return false
    return partes.some(palavras => {
      let i = 0
      for (const palavra of palavras) {
        const alvo = pedido[i]
        if (alvo !== undefined && casa(alvo, palavra)) i++
      }
      return i === pedido.length
    })
  })
}

export const textoGuarda = (item: string): string =>
  `megabrain-mod: "${item}" precisa de autorização do <USUARIO> (contrato: mutação git, apagar em massa e matar processo só com ok dele). ` +
  'Pergunte no chat e espere a resposta. Para mudar esta regra: guardaComandos em AJUSTES.ts do megabrain-mod.'

// ─── caminhos ───────────────────────────────────────────────────────

export const nomeBase = (caminho: string): string => caminho.split(/[\\/]/).filter(p => p !== '').pop() ?? caminho

const normalizarCaminho = (caminho: string): string =>
  `/${caminho.replace(/\\/g, '/').toLowerCase().replace(/^\/+/, '')}`

const normalizarPasta = (pasta: string): string =>
  pasta.replace(/\\/g, '/').toLowerCase().replace(/^\/+|\/+$/g, '')

const globParaRegex = (glob: string): RegExp =>
  new RegExp(`^${glob.split('*').map(escapar).join('.*')}$`, 'i')

export const ehSecreto = (caminho: string, padroes: readonly string[]): string | undefined => {
  const nome = nomeBase(caminho)
  return padroes.find(p => p.trim() !== '' && globParaRegex(p.trim()).test(nome))
}

export const naPastaGerada = (caminho: string, pastas: readonly string[]): string | undefined => {
  const alvo = normalizarCaminho(caminho)
  return pastas.find(p => {
    const pasta = normalizarPasta(p)
    return pasta !== '' && alvo.includes(`/${pasta}/`)
  })
}

/** Arquivo dentro de uma pastaComData sem nenhum trecho começando com AAMMDD. */
export const faltaData = (caminho: string, pastas: readonly string[]): boolean => {
  const alvo = normalizarCaminho(caminho)
  for (const p of pastas) {
    const pasta = normalizarPasta(p)
    if (pasta === '') continue
    const onde = alvo.indexOf(`/${pasta}/`)
    if (onde < 0) continue
    const resto = alvo
      .slice(onde + pasta.length + 2)
      .split('/')
      .filter(s => s !== '')
    if (resto.length === 0) continue
    return !resto.some(s => /^\d{6}([_\-. ]|$)/.test(s))
  }
  return false
}

export const ehCmd = (caminho: string): boolean => /\.(cmd|bat)$/i.test(caminho)

export const qualArquivoDeEstado = (caminho: string): ArquivoDeEstado | undefined => {
  const nome = nomeBase(caminho).toUpperCase()
  return ARQUIVOS_DE_ESTADO.find(a => a.toUpperCase() === nome)
}

export const ehLicao = (caminho: string): boolean => /licoes/.test(semAcento(nomeBase(caminho)))

/**
 * Por que o Claude não pode escrever neste arquivo, ou undefined se pode.
 * `ferramenta` é o nome da ferramenta (Write, Edit, ...__edit_block).
 */
export const recusaDeArquivo = (ferramenta: string, caminho: string, ajustes: Ajustes): string | undefined => {
  const segredo = ehSecreto(caminho, ajustes.arquivosSecretos)
  if (segredo !== undefined) {
    return `megabrain-mod: ${nomeBase(caminho)} guarda segredo (regra "${segredo}") e não se edita por aqui. Se precisar mudar, peça ao <USUARIO>.`
  }
  if (ehCmd(caminho) && /edit_block$/.test(ferramenta)) {
    return 'megabrain-mod: .cmd não se edita com edit_block (corrompe CRLF e encoding, regra 260824). Reescreva o arquivo inteiro em bytes: CRLF, sem BOM, ASCII no miolo.'
  }
  const gerada = naPastaGerada(caminho, ajustes.pastasGeradas)
  if (gerada !== undefined) {
    return `megabrain-mod: ${gerada} é cópia gerada por script. Edite a fonte (ex.: motor/skills/) e rode o gerador; editar a cópia some na próxima geração.`
  }
  return undefined
}

// ─── datas ──────────────────────────────────────────────────────────

/** AAMMDD no relógio de São Paulo (UTC-3, sem horário de verão desde 2019). */
export const hojeAAMMDD = (agoraMs: number): string => {
  const d = new Date(agoraMs - 3 * 3600 * 1000)
  const dois = (n: number) => String(n).padStart(2, '0')
  return `${String(d.getUTCFullYear()).slice(2)}${dois(d.getUTCMonth() + 1)}${dois(d.getUTCDate())}`
}

// ─── estado do megabrain ────────────────────────────────────────────

const pegar = (texto: string, re: RegExp): string => (re.exec(texto)?.[1] ?? '').trim()

const cortar = (texto: string, max: number): string =>
  texto.length > max ? `${texto.slice(0, max - 1).trimEnd()}…` : texto

export const travaLivre = (trava: string): boolean => /^(livre|—|-|)$/i.test(trava.trim())

export const projetoVazio = (nome: string, procurado: string[]): Projeto => ({
  nome,
  temMegabrain: false,
  pasta: '',
  modo: '',
  vigente: '',
  tldr: '',
  trava: '',
  paraVoce: '',
  procurado,
})

/** Lê o que importa do ESTADO.md e do HANDOFF.md. */
export const lerProjeto = (nome: string, pasta: string, estado: string, handoff: string, procurado: string[]): Projeto => {
  const blocoParaVoce = /MB:PARA-VOCE:ATUAL:INICIO\s*-->([\s\S]*?)<!--\s*MB:PARA-VOCE:ATUAL:FIM/.exec(handoff)?.[1] ?? ''
  const paraVoce = blocoParaVoce
    .replace(/<!--|-->/g, ' ')
    .replace(/^\s*#+.*$/gm, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  return {
    nome,
    temMegabrain: true,
    pasta,
    modo: pegar(estado, /^MODO:\s*(.+)$/m),
    vigente: cortar(pegar(estado, /^##\s+(.+)$/m), 140),
    tldr: cortar(pegar(estado, /TL;DR:\s*(.+)$/m), 320),
    trava: pegar(handoff, /TRAVADO_POR:\s*([^\s.·|,;]+)/) || '—',
    paraVoce: cortar(paraVoce, 400),
    procurado,
  }
}

// ─── o que a faixa e o painel mostram ───────────────────────────────

export type Tom = 'titulo' | 'ok' | 'alerta' | 'neutro' | 'apagado'
export type Pedaco = { texto: string; tom: Tom }

const faltaNoBastao = (editados: readonly string[]): string[] =>
  (['ESTADO.md', 'HANDOFF.md'] as const).filter(a => !editados.some(c => qualArquivoDeEstado(c) === a))

/** Os pedaços da faixa, na ordem em que aparecem. */
export const pedacosDaFaixa = (
  p: Projeto | null,
  editados: readonly string[],
  a: Auditoria,
  ajustes: Ajustes,
): Pedaco[] => {
  const pedacos: Pedaco[] = [{ texto: '🧠 megabrain', tom: 'titulo' }]
  if (p === null) pedacos.push({ texto: 'lendo…', tom: 'apagado' })
  else if (!p.temMegabrain) pedacos.push({ texto: `${p.nome} · sem megabrain aqui`, tom: 'apagado' })
  else {
    pedacos.push({ texto: p.nome, tom: 'neutro' })
    pedacos.push(travaLivre(p.trava) ? { texto: 'trava livre', tom: 'ok' } : { texto: `trava: ${p.trava}`, tom: 'alerta' })
  }
  pedacos.push({ texto: `✏️ ${editados.length}`, tom: editados.length === 0 ? 'apagado' : 'neutro' })
  if (p?.temMegabrain === true && editados.length >= ajustes.bastaoAPartirDe) {
    const falta = faltaNoBastao(editados)
    pedacos.push(
      falta.length === 0
        ? { texto: 'bastão ✓', tom: 'ok' }
        : { texto: `bastão: falta ${falta.map(f => f.replace('.md', '')).join(' e ')}`, tom: 'alerta' },
    )
  }
  if (!ajustes.vigiaSlop && !ajustes.exigirTldr) return pedacos
  if (a.respostas === 0) pedacos.push({ texto: 'AUDITAR —', tom: 'apagado' })
  else if (a.ultimasPalavras.length === 0 && !a.ultimaSemTldr) pedacos.push({ texto: 'AUDITAR ✓', tom: 'ok' })
  else {
    const partes = a.ultimasPalavras.slice(0, 3).map(w => `"${w}"`)
    if (a.ultimasPalavras.length > 3) partes.push(`+${a.ultimasPalavras.length - 3}`)
    if (a.ultimaSemTldr) partes.push('sem TL;DR')
    pedacos.push({ texto: `AUDITAR ⚠ ${partes.join(', ')}`, tom: 'alerta' })
  }
  return pedacos
}

// ── bússola: de onde a sessão partiu e onde está agora (BUSSOLA-VISUAL 260916) ──

const ORIGENS_DA_PESSOA = ['composer', 'bridge', 'sdk', 'unclassified', 'slack-ping']

/** Pedido digitado pela pessoa? Notificação, agendamento e plugin não contam. */
export const ehDaPessoa = (origem: { kind: string; asUser?: true }): boolean =>
  ORIGENS_DA_PESSOA.includes(origem.kind) || (origem.kind === 'plugin' && origem.asUser === true)

/** Tira blocos injetados (<system-reminder>…</system-reminder>) e espaços sobrando. */
export const limparPedido = (texto: string): string =>
  texto
    .replace(/<([a-zA-Z][\w-]*)[^>]*>[\s\S]*?<\/\1>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 2000)

/** Até `palavras` palavras, com … quando cortou. */
export const resumirPedido = (texto: string, palavras = 8): string => {
  const lista = texto.split(' ')
  return lista.length <= palavras ? texto : `${lista.slice(0, palavras).join(' ')}…`
}

export const anotarPedido = (anterior: Rumo | null, texto: string): Rumo =>
  anterior === null ? { primeiro: texto, atual: texto, n: 1 } : { ...anterior, atual: texto, n: anterior.n + 1 }

/** Rumo reconstruído do histórico (mod ligado no meio da sessão). */
export const rumoDoHistorico = (
  mensagens: readonly { role: string; text: string; toolResults?: readonly unknown[] }[],
): Rumo | null => {
  const pedidos = mensagens
    .filter(m => m.role === 'user' && (m.toolResults?.length ?? 0) === 0)
    .map(m => limparPedido(m.text))
    .filter(t => t !== '')
  const primeiro = pedidos[0]
  const atual = pedidos[pedidos.length - 1]
  return primeiro === undefined || atual === undefined ? null : { primeiro, atual, n: pedidos.length }
}

/** As linhas da bússola na faixa: começou e agora (uma só quando são o mesmo). */
export const linhasDaBussola = (r: Rumo | null): Pedaco[] => {
  if (r === null) return []
  if (r.n <= 1 || r.primeiro === r.atual) return [{ texto: `🧭 pedido ${r.n}: "${resumirPedido(r.atual)}"`, tom: 'neutro' }]
  return [
    { texto: `🧭 começou: "${resumirPedido(r.primeiro)}"`, tom: 'apagado' },
    { texto: `↳ agora (pedido ${r.n}): "${resumirPedido(r.atual)}"`, tom: 'neutro' },
  ]
}

// ── sessões: todas as conversas de IA deste PC (Claude, Codex 1 e 2, ZCode) ──

/** Lê a saída do coletor; qualquer formato estranho vira erro legível. */
export const lerSaidaSessoes = (stdout: string): Sessoes => {
  const d = JSON.parse(stdout) as Partial<Sessoes>
  if (!Array.isArray(d.sessoes) || typeof d.fontes !== 'object' || d.fontes === null) {
    throw new Error('saída do coletor sem lista de sessões')
  }
  return { gerado_ms: Number(d.gerado_ms) || 0, horas: Number(d.horas) || 0, fontes: d.fontes, sessoes: d.sessoes }
}

export const sessoesComErro = (erro: string): Sessoes => ({ gerado_ms: 0, horas: 0, fontes: {}, sessoes: [], erro })

export const idadeLegivel = (s: number): string =>
  s < 90 ? 'agora' : s < 3600 ? `há ${Math.round(s / 60)} min` : `há ${String(Math.round(s / 360) / 10).replace('.', ',')} h`

const conversas = (d: Sessoes): Sessao[] => d.sessoes.filter(s => !s.automacao)

/** Pedaço da faixa: quantas conversas e quantas trabalhando agora. */
export const pedacoSessoes = (d: Sessoes | null): Pedaco | null => {
  if (d === null) return null
  if (d.erro !== undefined) return { texto: '🗂 sessões: não li', tom: 'alerta' }
  const lista = conversas(d)
  const agora = lista.filter(s => s.estado === 'agora').length
  return {
    texto: `🗂 ${lista.length} ${lista.length === 1 ? 'sessão' : 'sessões'}${agora > 0 ? ` · ${agora} agora` : ''}`,
    tom: agora > 0 ? 'ok' : 'neutro',
  }
}

const ICONE: Record<Sessao['estado'], string> = { agora: '🟢', recente: '🟡', parada: '⚪' }
const GRUPO: Record<Sessao['estado'], string> = {
  agora: 'Trabalhando agora (até 2 min)',
  recente: 'Mexidas na última hora',
  parada: 'Paradas',
}

/** O painel /sessoes em markdown. `minhas` = ids desta sessão (marca "← esta"). */
export const montarPainelSessoes = (d: Sessoes | null, minhas: readonly string[]): string => {
  if (d === null) return 'Lendo as sessões…'
  if (d.erro !== undefined) {
    return `## 🗂 Sessões de IA neste PC\n\nNão consegui ler: ${d.erro}\n\nO coletor precisa do Python no PATH (\`python\` em AJUSTES.ts).`
  }
  const lista = conversas(d)
  const linhas = [`## 🗂 Sessões de IA neste PC · ${lista.length} nas últimas ${d.horas} h`]
  for (const estado of ['agora', 'recente', 'parada'] as const) {
    const grupo = lista.filter(s => s.estado === estado)
    if (grupo.length === 0) continue
    linhas.push('', `### ${ICONE[estado]} ${GRUPO[estado]} (${grupo.length})`, '')
    for (const s of grupo) {
      const esta = s.ids.some(id => minhas.includes(id)) ? ' ← esta' : ''
      linhas.push(`- **${s.titulo}**${esta} · ${s.fonte} · ${s.projeto} · ${idadeLegivel(s.idade_s)}`)
    }
  }
  if (lista.length === 0) linhas.push('', `Nenhuma conversa de IA mexida nas últimas ${d.horas} h.`)
  const auto = d.sessoes.filter(s => s.automacao)
  if (auto.length > 0) {
    const agora = auto.filter(s => s.estado === 'agora').length
    linhas.push('', `⚙️ +${auto.length} automações (claude -p, codex exec)${agora > 0 ? `, ${agora} rodando agora` : ''}`)
  }
  const falhas = Object.entries(d.fontes).filter(([, f]) => !f.ok)
  if (falhas.length > 0) linhas.push('', `Não lidas: ${falhas.map(([n, f]) => `${n} (${f.erro ?? 'erro'})`).join(' · ')}`)
  return linhas.join('\n')
}

export type DadosDoPainel = {
  projeto: Projeto | null
  editados: readonly string[]
  lidos: readonly string[]
  auditoria: Auditoria
  registrou: boolean
  ajustes: Ajustes
  rumo?: Rumo | null
}

const marca = (ok: boolean | null): string => (ok === null ? '·' : ok ? '✅' : '⚠️')

/** O painel /mb em markdown. */
export const montarPainel = (d: DadosDoPainel): string => {
  const p = d.projeto
  const linhas: string[] = []
  if (p === null) return 'Lendo o estado do megabrain…'
  linhas.push(`## 🧠 megabrain · ${p.nome}`)
  if (!p.temMegabrain) {
    linhas.push('', `Sem ESTADO.md nesta pasta. Procurei em: ${p.procurado.map(c => `\`${c}\``).join(', ')}.`)
    linhas.push('Se o seu fica em outra pasta, acrescente em `pastasDeEstado` no AJUSTES.ts.')
  } else {
    linhas.push('')
    if (p.vigente) linhas.push(`**Estado vigente:** ${p.vigente}`)
    if (p.tldr) linhas.push(`**TL;DR:** ${p.tldr}`)
    linhas.push(`**Trava:** ${travaLivre(p.trava) ? 'livre ✅' : `${p.trava} ⚠️`}${p.modo ? ` · **Modo:** ${p.modo}` : ''}`)
    linhas.push(`**👤 Para você:** ${p.paraVoce || 'nada pendente no HANDOFF.'}`)
  }

  const lidosFaltando = ARQUIVOS_DE_ESTADO.filter(a => !d.lidos.includes(a))
  const leuBase = d.lidos.includes('ESTADO.md') && d.lidos.includes('HANDOFF.md')
  const a = d.auditoria
  const falta = faltaNoBastao(d.editados)
  const bastaoConta = p?.temMegabrain === true && d.editados.length > 0

  if (d.rumo != null) {
    linhas.push('', `### 🧭 Rumo da sessão (${d.rumo.n} ${d.rumo.n === 1 ? 'pedido' : 'pedidos'})`, '')
    linhas.push(`**Começou:** ${d.rumo.primeiro}`)
    if (d.rumo.n > 1) linhas.push(`**Agora:** ${d.rumo.atual}`)
  }

  linhas.push('', '### Gates desta sessão', '', '| gate | situação |', '|---|---|')
  linhas.push(
    `| ${marca(p?.temMegabrain ? leuBase : null)} ASSUMIR | ${
      d.lidos.length === 0 ? 'não leu ESTADO/HANDOFF nesta sessão' : `leu ${d.lidos.join(', ')}`
    }${d.lidos.length > 0 && lidosFaltando.length > 0 ? ` · falta ${lidosFaltando.join(', ')}` : ''} |`,
  )
  linhas.push(
    `| ${marca(a.respostas === 0 ? null : a.ultimasPalavras.length === 0 && !a.ultimaSemTldr)} AUDITAR | ${
      a.respostas
    } respostas · ${a.comSlop} com slop · ${a.semTldr} sem TL;DR${
      a.ultimasPalavras.length > 0 ? ` · última: ${a.ultimasPalavras.map(w => `"${w}"`).join(', ')}` : ''
    } |`,
  )
  linhas.push('| · VERIFICAR | o mod não mede: número recalculado, arquivo aberto, link testado |')
  linhas.push(
    `| ${marca(bastaoConta ? falta.length === 0 : null)} PASSAR O BASTÃO | ${
      d.editados.length === 0
        ? 'nenhum arquivo mexido'
        : falta.length === 0
          ? `${d.editados.length} arquivos mexidos, ESTADO e HANDOFF atualizados`
          : `${d.editados.length} arquivos mexidos, falta ${falta.join(' e ')}`
    } |`,
  )
  linhas.push(`| ${marca(d.editados.length === 0 ? null : d.registrou)} REGISTRAR | ${d.registrou ? 'lição registrada' : 'registrar-licao não rodou'} |`)

  if (d.editados.length > 0) {
    linhas.push('', `### Arquivos mexidos (${d.editados.length})`, '')
    for (const c of d.editados.slice(-15)) linhas.push(`- \`${c}\``)
    if (d.editados.length > 15) linhas.push(`- … e mais ${d.editados.length - 15}`)
  }
  return linhas.join('\n')
}

/** Bilhete escondido pro Claude quando a resposta saiu fora do contrato. */
export const bilheteAuditoria = (palavras: readonly string[], semTldr: boolean): string => {
  const problemas: string[] = []
  if (palavras.length > 0) problemas.push(`usou termos banidos: ${palavras.map(w => `"${w}"`).join(', ')}`)
  if (semTldr) problemas.push('não abriu com TL;DR')
  return (
    `[megabrain-mod · gate AUDITAR] Sua última resposta ${problemas.join(' e ')}. ` +
    'Nas próximas, siga o contrato de resposta: TL;DR no topo em resposta com entrega, sem léxico banido (reescreva a frase, não troque por sinônimo). ' +
    'Não comente este aviso com o <USUARIO>.'
  )
}

/** Texto do /mb-ajustes. */
export const resumoAjustes = (ajustes: Ajustes, caminho: string): string => {
  const sim = (v: boolean) => (v ? 'ligado' : 'desligado')
  return [
    `Ajustes do megabrain-mod: ${caminho}`,
    '',
    `- faixa: ${sim(ajustes.faixa)} · bússola (1º pedido e pedido atual): ${sim(ajustes.bussola)}`,
    `- sessões de IA do PC: ${sim(ajustes.sessoes)} (janela ${ajustes.sessoesJanelaHoras} h, atualiza a cada ${ajustes.sessoesAtualizarSegundos} s)`,
    `- vigia de slop: ${sim(ajustes.vigiaSlop)} (${ajustes.palavrasBanidas.length} termos) · bilhete pro Claude: ${sim(ajustes.avisarOClaude)}`,
    `- TL;DR no topo: ${sim(ajustes.exigirTldr)} (a partir de ${ajustes.tldrAPartirDeLinhas} linhas)`,
    `- guarda de comandos: ${ajustes.guardaComandos} (${ajustes.comandosVigiados.length} comandos)`,
    `- arquivos protegidos: ${sim(ajustes.protegerArquivos)} (${ajustes.arquivosSecretos.length} padrões de segredo, ${ajustes.pastasGeradas.length} pastas geradas)`,
    `- lembrete de .cmd: ${sim(ajustes.lembrarCmd)} · data no nome: ${sim(ajustes.exigirDataNoNome)}`,
    `- bastão cobrado a partir de ${ajustes.bastaoAPartirDe} arquivos`,
    '',
    'Abra o arquivo, mude true/false ou as listas e salve: o mod recarrega sozinho. Ou peça ao Claude: "no megabrain-mod, muda X".',
  ].join('\n')
}
