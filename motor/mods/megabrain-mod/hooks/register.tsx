// megabrain-mod: o protocolo megabrain dentro do Claude Code.
// Liga cada peça ao evento certo do Claude. Os valores ficam em AJUSTES.ts;
// as regras (o que é slop, que comando é perigoso...) em regras.ts.

import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, ToolCallInput } from 'claude-code'

import { AJUSTES } from '../AJUSTES'
import {
  AUDITORIA_VAZIA,
  acharSlop,
  anotarPedido,
  bilheteAuditoria,
  comandoVigiado,
  ehCmd,
  ehDaPessoa,
  ehLicao,
  faltaData,
  hojeAAMMDD,
  lerSaidaSessoes,
  lerProjeto,
  limparPedido,
  linhasDaBussola,
  montarPainel,
  montarPainelSessoes,
  nomeBase,
  pedacoSessoes,
  pedacosDaFaixa,
  projetoVazio,
  qualArquivoDeEstado,
  recusaDeArquivo,
  resumoAjustes,
  rumoDoHistorico,
  sessoesComErro,
  temTldr,
  textoGuarda,
  travaLivre,
} from './regras'
import type { Tom } from './regras'

const PAINEL = 'megabrain-painel'
const PAINEL_SESSOES = 'megabrain-sessoes'

const projeto = atom({ plugin: 'megabrain-mod', key: 'projeto' } as const, null)
const editados = atom({ plugin: 'megabrain-mod', key: 'editados' } as const, [])
const lidos = atom({ plugin: 'megabrain-mod', key: 'lidos' } as const, [])
const auditoria = atom({ plugin: 'megabrain-mod', key: 'auditoria' } as const, AUDITORIA_VAZIA)
const registrou = atom({ plugin: 'megabrain-mod', key: 'registrou' } as const, false)
const faixaOculta = atom({ plugin: 'megabrain-mod', key: 'faixaOculta' } as const, false)
const rumo = atom({ plugin: 'megabrain-mod', key: 'rumo' } as const, null)
const sessoes = atom({ plugin: 'megabrain-mod', key: 'sessoes' } as const, null)

// Ferramentas que escrevem arquivo: as do Claude e as do Desktop Commander.
const ESCRITA = /^(Write|Edit|MultiEdit|NotebookEdit)$|(^|__)(write_file|edit_block)$/
const ESCRITA_NOVA = /^Write$|(^|__)write_file$/
const LEITURA = /^Read$|(^|__)(read_file|read_multiple_files)$/

const campo = (x: unknown, chave: string): string | undefined => {
  if (x === null || typeof x !== 'object') return undefined
  const valor = (x as Record<string, unknown>)[chave]
  return typeof valor === 'string' && valor !== '' ? valor : undefined
}

const caminhoDe = (e: ToolCallInput): string | undefined =>
  campo(e, 'file_path') ?? campo(e, 'notebook_path') ?? campo(e, 'path')

const caminhoDosAjustes = ($: EngineInterface): string => {
  const raiz = $.plugin.root
  return `${raiz}${raiz.includes('\\') ? '\\' : '/'}AJUSTES.ts`
}

/** Procura ESTADO.md/HANDOFF.md nas pastasDeEstado e guarda o que leu. */
const carregarProjeto = async ($: EngineInterface): Promise<void> => {
  const raiz = await $.session.root().catch(() => '')
  const nome = raiz === '' ? '—' : nomeBase(raiz)
  const procurado: string[] = []
  for (const pasta of AJUSTES.pastasDeEstado) {
    const base = pasta.replace(/[\\/]+$/, '')
    const caminhoEstado = base === '' ? 'ESTADO.md' : `${base}/ESTADO.md`
    procurado.push(caminhoEstado)
    if (!(await $.fs.exists(caminhoEstado).catch(() => false))) continue
    const estado = await $.fs.read(caminhoEstado).catch(() => '')
    const handoff = await $.fs.read(base === '' ? 'HANDOFF.md' : `${base}/HANDOFF.md`).catch(() => '')
    await update($, projeto, () => lerProjeto(nome, base, estado, handoff, procurado))
    return
  }
  await update($, projeto, () => projetoVazio(nome, procurado))
}

/** Roda o coletor (coletor/mb_sessoes.py, só leitura) e guarda a lista. */
const carregarSessoes = async ($: EngineInterface): Promise<void> => {
  const raiz = $.plugin.root
  const barra = raiz.includes('\\') ? '\\' : '/'
  const script = `${raiz}${barra}coletor${barra}mb_sessoes.py`
  try {
    const r = await $.process.run(
      [AJUSTES.python, script, '--json', '--horas', String(AJUSTES.sessoesJanelaHoras)],
      { timeoutMs: 20000 },
    )
    const lido =
      r.exitCode === 0 ? lerSaidaSessoes(r.stdout) : sessoesComErro(`coletor saiu com código ${r.exitCode}: ${r.stderr.slice(0, 160)}`)
    await update($, sessoes, () => lido)
  } catch (erro) {
    await update($, sessoes, () => sessoesComErro(String(erro).slice(0, 200))).catch(() => undefined)
  }
}

const abrirSessoes = async ($: EngineInterface): Promise<void> => {
  await $.ui.open({ id: PAINEL_SESSOES, title: 'sessões' })
  await carregarSessoes($)
}

const abrirPainel = async ($: EngineInterface): Promise<void> => {
  await update($, faixaOculta, () => false)
  await carregarProjeto($)
  await $.ui.open({ id: PAINEL, title: 'megabrain' })
}

const COR: Record<Tom, { color?: string; bold?: boolean; dimColor?: boolean }> = {
  titulo: { bold: true },
  ok: { color: 'success' },
  alerta: { color: 'warning', bold: true },
  neutro: {},
  apagado: { dimColor: true },
}

export const register: Register = on => {
  // ── início da sessão: comandos + leitura do estado (gate ASSUMIR) ──
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'mb',
      description: 'megabrain: abre o painel (estado, trava, gates desta sessão)',
    })
    if (AJUSTES.sessoes) {
      await $.command.register({
        name: 'sessoes',
        description: 'megabrain: lista as sessões de IA deste PC (Claude, Codex 1 e 2, ZCode)',
      })
      // claude -p e workers da orquestração também carregam o mod: sem tela, sem coletor no relógio
      if (e.isInteractive) {
        void carregarSessoes($).catch(() => undefined)
        $.clock.every(Math.max(15, AJUSTES.sessoesAtualizarSegundos) * 1000, () => {
          void carregarSessoes($).catch(() => undefined)
        })
      }
    }
    await $.command.register({
      name: 'mb-ajustes',
      description: 'megabrain: mostra onde mudar o megabrain-mod e o que está ligado',
    })
    await carregarProjeto($)
    // Bússola: ligado no meio da sessão, reconstrói o 1º pedido pelo histórico.
    if ((await read($, rumo)) === null) {
      const doHistorico = rumoDoHistorico(await $.session.messages().catch(() => []))
      if (doHistorico !== null) await update($, rumo, () => doHistorico)
    }
    const p = await read($, projeto)
    if (p !== null && p.temMegabrain && !travaLivre(p.trava)) {
      $.ui.toast(`⚠ megabrain: ${p.nome} está travado por ${p.trava}`, { timeoutMs: 8000 })
    }
    return next(e)
  })

  // ── bússola: anota cada pedido da pessoa (nunca barra o pedido) ──
  on('prompt.submit', async ($, e, next) => {
    const texto = limparPedido(e.text)
    if (texto !== '' && ehDaPessoa(e.origin)) await update($, rumo, anterior => anotarPedido(anterior, texto))
    return next(e)
  }).catch(($, e, next) => next(e))

  // /clear começa outra conversa: o próximo pedido vira o 1º.
  on('session.end', async ($, e, next) => {
    if (e.reason === 'clear') await update($, rumo, () => null)
    return next(e)
  })

  on('command.run', { command: 'mb' }, async $ => {
    await abrirPainel($)
    return { text: 'Painel do megabrain aberto.' }
  })

  on('command.run', { command: 'sessoes' }, async $ => {
    await abrirSessoes($)
    return { text: montarPainelSessoes(await read($, sessoes), [await $.session.id()]) }
  })

  on('command.run', { command: 'mb-ajustes' }, async $ => ({
    text: resumoAjustes(AJUSTES, caminhoDosAjustes($)),
  }))

  // ── cada ferramenta: guardas antes, registro e lembretes depois ──
  on('tool.call', async ($, e, next) => {
    const ferramenta = String(e.tool)
    const caminho = caminhoDe(e)
    const escreve = caminho !== undefined && ESCRITA.test(ferramenta)

    if (AJUSTES.guardaComandos === 'bloquear') {
      const comando = campo(e, 'command')
      const item = comando === undefined ? undefined : comandoVigiado(comando, AJUSTES.comandosVigiados)
      if (item !== undefined) return { deny: textoGuarda(item) }
    }

    if (escreve && AJUSTES.protegerArquivos) {
      const recusa = recusaDeArquivo(ferramenta, caminho, AJUSTES)
      if (recusa !== undefined) return { deny: recusa }
    }

    const ehNovo =
      escreve && AJUSTES.exigirDataNoNome && ESCRITA_NOVA.test(ferramenta)
        ? !(await $.fs.exists(caminho).catch(() => true))
        : false

    const feito = await next(e)
    if (feito.deny !== undefined || feito.isError === true) return feito

    const lembretes: string[] = []
    if (escreve) {
      await update($, editados, lista => (lista.includes(caminho) ? lista : [...lista, caminho].slice(-300)))
      const qual = qualArquivoDeEstado(caminho)
      if (qual === 'ESTADO.md' || qual === 'HANDOFF.md') await carregarProjeto($)
      if (ehLicao(caminho)) await update($, registrou, () => true)
      if (AJUSTES.lembrarCmd && ehCmd(caminho)) {
        lembretes.push(
          '[megabrain-mod · VERIFICAR] Arquivo .cmd alterado: confirme CRLF, sem BOM e ASCII no miolo (regra 260824). Na central: python bin\\mb-testar.py.',
        )
      }
      if (ehNovo && faltaData(caminho, AJUSTES.pastasComData)) {
        const hoje = hojeAAMMDD(await $.clock.now())
        lembretes.push(
          `[megabrain-mod · VERIFICAR] Arquivo novo sem prefixo de data: ${nomeBase(caminho)}. Padrão: ${hoje}_nome (hoje = ${hoje}). Renomeie.`,
        )
      }
    }
    if (caminho !== undefined && LEITURA.test(ferramenta)) {
      const qual = qualArquivoDeEstado(caminho)
      if (qual !== undefined) await update($, lidos, lista => (lista.includes(qual) ? lista : [...lista, qual]))
    }
    if (ferramenta === 'Skill' && /registrar-licao/.test(campo(e, 'skill') ?? '')) {
      await update($, registrou, () => true)
    }

    return lembretes.length === 0 ? feito : { ...feito, context: [...(feito.context ?? []), ...lembretes] }
  }).catch(($, e, next) => next(e))

  // ── guarda de comandos no modo 'perguntar': abre a caixa de autorização ──
  on('tool.check', async ($, e, next) => {
    const abaixo = await next(e)
    if (AJUSTES.guardaComandos !== 'perguntar' || abaixo.decision !== 'allow') return abaixo
    const comando = campo(e.input, 'command')
    const item = comando === undefined ? undefined : comandoVigiado(comando, AJUSTES.comandosVigiados)
    return item === undefined
      ? abaixo
      : { decision: 'ask', reason: `megabrain-mod: "${item}" pede autorização do Usuário (contrato do megabrain).` }
  }).catch(($, e, next) => next(e))

  // ── fim de cada resposta: gate AUDITAR (slop + TL;DR) ──
  on('turn.complete', async ($, e, next) => {
    const resultado = await next(e)
    if (e.agentId !== undefined || e.reason !== 'answer' || e.answer.trim() === '') return resultado

    const palavras = AJUSTES.vigiaSlop ? acharSlop(e.answer, AJUSTES.palavrasBanidas) : []
    const semTldr = AJUSTES.exigirTldr && temTldr(e.answer, AJUSTES.tldrAPartirDeLinhas) === false

    await update($, auditoria, a => ({
      respostas: a.respostas + 1,
      comSlop: a.comSlop + (palavras.length > 0 ? 1 : 0),
      semTldr: a.semTldr + (semTldr ? 1 : 0),
      ultimasPalavras: palavras,
      ultimaSemTldr: semTldr,
    }))

    if (palavras.length > 0 || semTldr) {
      const aviso = [
        palavras.length > 0 ? `slop: ${palavras.map(w => `"${w}"`).join(', ')}` : '',
        semTldr ? 'sem TL;DR no topo' : '',
      ]
        .filter(t => t !== '')
        .join(' · ')
      $.ui.toast(`🚫 AUDITAR — ${aviso}`, { timeoutMs: 7000 })
      if (AJUSTES.avisarOClaude) {
        await $.session
          .append({ message: { type: 'user', content: [{ type: 'text', text: bilheteAuditoria(palavras, semTldr) }] } })
          .catch(() => undefined)
      }
    }
    return resultado
  })

  // ── faixa acima do campo de digitar ──
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (!AJUSTES.faixa || e.props.hasSurvey || (await read($, faixaOculta))) return next(e)
    const { Box, Text, Button } = $.ui.resolve(e)
    const pedacos = pedacosDaFaixa(await read($, projeto), await read($, editados), await read($, auditoria), AJUSTES)
    const bussola = AJUSTES.bussola ? linhasDaBussola(await read($, rumo)) : []
    const pedacoDeSessoes = AJUSTES.sessoes ? pedacoSessoes(await read($, sessoes)) : null
    if (pedacoDeSessoes !== null) pedacos.push(pedacoDeSessoes)
    return (
      <Box flexDirection="column">
        <Box flexDirection="row" flexWrap="wrap" columnGap={1}>
          {pedacos.map((p, i) => (
            <Text {...COR[p.tom]}>
              {i > 0 ? '· ' : ''}
              {p.texto}
            </Text>
          ))}
          <Button key="painel" label="painel" onPress={() => abrirPainel($)} />
          {AJUSTES.sessoes && <Button key="sessoes" label="sessões" onPress={() => abrirSessoes($)} />}
          <Button key="ocultar" label="ocultar" onPress={() => update($, faixaOculta, () => true)} />
        </Box>
        {bussola.map(l => (
          <Text {...COR[l.tom]} wrap="truncate-end">
            {l.texto}
          </Text>
        ))}
      </Box>
    )
  })

  // ── painel /sessoes ──
  on('ui.render', { component: 'Pane', requestId: PAINEL_SESSOES }, async ($, e) => {
    const { Box, Markdown, Button } = $.ui.resolve(e)
    const texto = montarPainelSessoes(await read($, sessoes), [await $.session.id()])
    return (
      <Box flexDirection="column" rowGap={1}>
        <Markdown key="sessoes-texto" text={texto} />
        <Box flexDirection="row" flexWrap="wrap" columnGap={1}>
          <Button key="sessoes-atualizar" label="atualizar" onPress={() => carregarSessoes($)} />
        </Box>
      </Box>
    )
  })

  // ── painel /mb ──
  on('ui.render', { component: 'Pane', requestId: PAINEL }, async ($, e) => {
    const { Box, Markdown, Button } = $.ui.resolve(e)
    const texto = montarPainel({
      projeto: await read($, projeto),
      editados: await read($, editados),
      lidos: await read($, lidos),
      auditoria: await read($, auditoria),
      registrou: await read($, registrou),
      ajustes: AJUSTES,
      rumo: AJUSTES.bussola ? await read($, rumo) : null,
    })
    return (
      <Box flexDirection="column" rowGap={1}>
        <Markdown key="painel-texto" text={texto} />
        <Box flexDirection="row" flexWrap="wrap" columnGap={1}>
          <Button key="atualizar" label="atualizar" onPress={() => carregarProjeto($)} />
          <Button
            key="ajustes"
            label="copiar caminho dos ajustes"
            onPress={async press => {
              const caminho = caminhoDosAjustes($)
              const copia = await $.ui.copy({ text: caminho, surface: press.surface })
              $.ui.toast(copia.isCopied ? `Copiado: ${caminho}` : caminho, { timeoutMs: 8000 })
            }}
          />
          <Button key="zerar" label="zerar contadores" onPress={() => update($, auditoria, () => AUDITORIA_VAZIA)} />
        </Box>
      </Box>
    )
  })
}
