import { describe, expect, test } from 'claude-code/testing'

import { AJUSTES } from '../AJUSTES'
import {
  AUDITORIA_VAZIA,
  acharSlop,
  comandoVigiado,
  ehSecreto,
  faltaData,
  hojeAAMMDD,
  lerProjeto,
  montarPainel,
  naPastaGerada,
  lerSaidaSessoes,
  linhasDaBussola,
  montarPainelSessoes,
  pedacoSessoes,
  pedacosDaFaixa,
  recusaDeArquivo,
  rumoDoHistorico,
  temTldr,
} from '../hooks/regras'

const ESTADO = `# ESTADO — megabrain core

MODO: otimizado

## Vigente · 260916 · auditoria do Astra

TL;DR: trabalho aprovado e hooks restaurados.
`

const HANDOFF = `# HANDOFF
<!-- MB:PARA-VOCE:ATUAL:INICIO -->
## PARA VOCÊ
<!-- 260916 18:58 · nenhuma ação humana obrigatória. -->
<!-- MB:PARA-VOCE:ATUAL:FIM -->
Reversão: git checkout. TRAVADO_POR: livre. Nenhuma mutação git.
`

const BANDA = {
  hasSurvey: false,
  isWorking: false,
  maxRows: 6,
  bodyColumns: 140,
  scroll: { offset: 0, bodyRows: 5 },
  view: {},
}

describe('vigia de slop', () => {
  test('acha léxico banido com acento, plural e prefixo, como aparece no texto', () => {
    const texto = 'Uma solução robusta que vai potencializar tudo. Em suma, ficou ótimo.'
    expect(acharSlop(texto, AJUSTES.palavrasBanidas)).toEqual(['robusta', 'potencializar', 'Em suma'])
  })

  test('ignora termo citado em código', () => {
    expect(acharSlop('A lista bane `robusto` e:\n```\nalavancar\n```', AJUSTES.palavrasBanidas)).toEqual([])
  })

  test('palavra exata não casa dentro de outra', () => {
    expect(acharSlop('O arquivo unlocked e elevated ficam fora.', AJUSTES.palavrasBanidas)).toEqual([])
  })

  test('frase de estrutura casa mesmo com quebra de linha', () => {
    expect(acharSlop('Espero que\najude!', AJUSTES.palavrasBanidas)).toEqual(['Espero que ajude'])
  })
})

describe('TL;DR', () => {
  const longa = (topo: string) => [topo, ...Array.from({ length: 9 }, (_, i) => `linha ${i}`)].join('\n')

  test('resposta curta não precisa', () => {
    expect(temTldr('oi\ntudo certo', 8)).toBeNull()
  })

  test('aceita **TL;DR:** e título antes', () => {
    expect(temTldr(longa('**TL;DR:** feito.'), 8)).toBe(true)
    expect(temTldr(longa('# Mod\nTL;DR: feito.'), 8)).toBe(true)
  })

  test('acusa resposta longa sem TL;DR', () => {
    expect(temTldr(longa('Vou começar explicando.'), 8)).toBe(false)
  })
})

describe('guarda de comandos', () => {
  test('pega git push mesmo depois de cd e com -C', () => {
    expect(comandoVigiado('cd /d "S:\\x" && git -C repo push origin main', AJUSTES.comandosVigiados)).toBe('git push')
  })

  test('flag casa pelo começo e PowerShell fora de ordem', () => {
    expect(comandoVigiado('rm -rf build', AJUSTES.comandosVigiados)).toBe('rm -r')
    expect(comandoVigiado('Remove-Item .\\out -Recurse -Force', AJUSTES.comandosVigiados)).toBe('Remove-Item -Recurse')
  })

  test('não pega comando inocente nem palavra em outro trecho', () => {
    expect(comandoVigiado('git status && echo push', AJUSTES.comandosVigiados)).toBeUndefined()
    expect(comandoVigiado('python bin\\mb-testar.py', AJUSTES.comandosVigiados)).toBeUndefined()
  })

  test('no modo perguntar, a guarda troca allow por ask', async ($, on) => {
    on('tool.check', () => ({ decision: 'allow' }))
    const vigiado = await $.tool.check({ tool: 'Bash', input: { command: 'git push origin main' } })
    expect(vigiado.decision).toBe('ask')
    const livre = await $.tool.check({ tool: 'Bash', input: { command: 'git status' } })
    expect(livre.decision).toBe('allow')
  })
})

describe('arquivos', () => {
  test('segredo, cópia gerada e data no nome', () => {
    expect(ehSecreto('C:\\proj\\.env', AJUSTES.arquivosSecretos)).toBe('.env')
    expect(ehSecreto('C:\\proj\\.env.example', AJUSTES.arquivosSecretos)).toBeUndefined()
    expect(naPastaGerada('S:\\MB\\_github\\export\\README.md', AJUSTES.pastasGeradas)).toBe('_github/export')
    expect(naPastaGerada('S:\\MB\\motor\\skills\\megabrain\\SKILL.md', AJUSTES.pastasGeradas)).toBeUndefined()
    expect(faltaData('S:\\MB\\00_PARA-VOCE\\relatorio.html', AJUSTES.pastasComData)).toBe(true)
    expect(faltaData('S:\\MB\\00_PARA-VOCE\\261006_mod\\LEIAME.md', AJUSTES.pastasComData)).toBe(false)
    expect(faltaData('S:\\MB\\bin\\script.py', AJUSTES.pastasComData)).toBe(false)
  })

  test('edit_block em .cmd é recusado, Write não', () => {
    expect(recusaDeArquivo('mcp__desktop-commander__edit_block', 'S:\\MB\\01_acoes\\x.cmd', AJUSTES)).toContain('CRLF')
    expect(recusaDeArquivo('Write', 'S:\\MB\\01_acoes\\x.cmd', AJUSTES)).toBeUndefined()
  })

  test('o mod recusa escrever .env', async ($, on) => {
    on('tool.call', () => ({ result: {} as never }))
    const r = await $.tool.call({ tool: 'Write', file_path: '/proj/.env', content: 'SEGREDO=1' })
    expect(r.deny).toContain('segredo')
  })

  test('data de hoje no relógio de São Paulo', () => {
    // 2026-10-07 01:30 UTC = 2026-10-06 22:30 em São Paulo
    expect(hojeAAMMDD(Date.UTC(2026, 9, 7, 1, 30))).toBe('261006')
  })
})

describe('estado do megabrain', () => {
  test('lê modo, vigente, TL;DR, trava e PARA VOCÊ', () => {
    const p = lerProjeto('MEGA B R A I  N', 'memoria/estado', ESTADO, HANDOFF, [])
    expect(p.modo).toBe('otimizado')
    expect(p.vigente).toBe('Vigente · 260916 · auditoria do Astra')
    expect(p.tldr).toBe('trabalho aprovado e hooks restaurados.')
    expect(p.trava).toBe('livre')
    expect(p.paraVoce).toBe('260916 18:58 · nenhuma ação humana obrigatória.')
  })

  test('faixa cobra o bastão a partir de 3 arquivos', () => {
    const p = lerProjeto('MB', '', ESTADO, HANDOFF, [])
    const textos = pedacosDaFaixa(p, ['a.ts', 'b.ts', 'memoria/estado/ESTADO.md'], AUDITORIA_VAZIA, AJUSTES).map(x => x.texto)
    expect(textos).toContain('bastão: falta HANDOFF')
    expect(textos).toContain('trava livre')
  })

  test('painel mostra os gates', () => {
    const texto = montarPainel({
      projeto: lerProjeto('MB', '', ESTADO, HANDOFF, []),
      editados: ['x.ts'],
      lidos: ['ESTADO.md'],
      auditoria: AUDITORIA_VAZIA,
      registrou: false,
      ajustes: AJUSTES,
    })
    expect(texto).toContain('ASSUMIR')
    expect(texto).toContain('PASSAR O BASTÃO')
    expect(texto).toContain('registrar-licao não rodou')
  })
})

describe('faixa na tela', () => {
  test('depois de uma resposta com slop, a faixa mostra AUDITAR ⚠ (terminal e desktop)', async ($, on) => {
    on('turn.complete', (_, e) => ({ text: e.answer }))
    await $.turn.complete({
      answer: 'Uma abordagem robusta.',
      durationMs: 10,
      isAborted: false,
      turnId: 't1',
      reason: 'answer',
    })
    for (const surface of ['terminal', 'desktop'] as const) {
      const ui = await $.ui.mount({ plugin: 'megabrain-mod', surface, component: 'AbovePrompt', props: BANDA })
      expect(await ui.find({ type: 'Text', text: /AUDITAR ⚠ "robusta"/ })).toBeDefined()
      expect(await ui.find({ key: 'painel' })).toBeDefined()
      await ui.unmount()
    }
  })

  test('painel /mb desenha em terminal, desktop e celular', async $ => {
    for (const surface of ['terminal', 'desktop', 'mobile'] as const) {
      const ui = await $.ui.mount({
        plugin: 'megabrain-mod',
        surface,
        component: 'Pane',
        requestId: 'megabrain-painel',
        props: {
          title: 'megabrain',
          isFocused: true,
          bodyColumns: 100,
          placement: 'dock',
          scroll: { offset: 0, bodyRows: 30 },
          view: {},
        },
      })
      expect(await ui.find({ key: 'atualizar' })).toBeDefined()
      expect(await ui.find({ key: 'zerar' })).toBeDefined()
      await ui.unmount()
    }
  })
})

describe('bússola', () => {
  test('histórico: tira aviso do sistema e ignora retorno de ferramenta', () => {
    expect(
      rumoDoHistorico([
        { role: 'user', text: '<system-reminder>contexto injetado</system-reminder>\nquero criar mods' },
        { role: 'assistant', text: 'ok' },
        { role: 'user', text: '', toolResults: [{}] },
        { role: 'user', text: 'e agora testa' },
      ]),
    ).toEqual({ primeiro: 'quero criar mods', atual: 'e agora testa', n: 2 })
    expect(rumoDoHistorico([])).toBe(null)
  })

  test('linhas: corta em 8 palavras e junta quando só há um pedido', () => {
    expect(linhasDaBussola({ primeiro: 'um dois três quatro cinco seis sete oito nove', atual: 'oi', n: 3 })).toEqual([
      { texto: '🧭 começou: "um dois três quatro cinco seis sete oito…"', tom: 'apagado' },
      { texto: '↳ agora (pedido 3): "oi"', tom: 'neutro' },
    ])
    expect(linhasDaBussola({ primeiro: 'oi', atual: 'oi', n: 1 })).toEqual([{ texto: '🧭 pedido 1: "oi"', tom: 'neutro' }])
  })

  test('na faixa: 1º pedido e atual, sem contar notificação; /clear zera', async ($, on) => {
    on('prompt.submit', (_, e) => ({ text: e.text }))
    on('session.end', (_, e) => ({ sessionId: e.sessionId }))
    const pedir = (text: string, kind: 'composer' | 'task-notification' = 'composer') =>
      $.prompt.submit({ text, wait: false, origin: { kind } })

    await pedir('Eu fiquei sabendo que agora o Claude tem os mods, então eu queria criar os meus')
    await pedir('task finished', 'task-notification')
    await pedir('encaixa a bússola no mod')
    for (const surface of ['terminal', 'desktop'] as const) {
      const ui = await $.ui.mount({ plugin: 'megabrain-mod', surface, component: 'AbovePrompt', props: BANDA })
      expect(await ui.find({ type: 'Text', text: '🧭 começou: "Eu fiquei sabendo que agora o Claude tem…"' })).toBeDefined()
      expect(await ui.find({ type: 'Text', text: '↳ agora (pedido 2): "encaixa a bússola no mod"' })).toBeDefined()
      expect(await ui.find({ key: 'painel' })).toBeDefined()
      await ui.unmount()
    }

    await $.session.end({ reason: 'clear', sessionId: 's1', resume: { id: 's1' } })
    await pedir('conversa nova')
    const ui = await $.ui.mount({ plugin: 'megabrain-mod', surface: 'desktop', component: 'AbovePrompt', props: BANDA })
    expect(await ui.find({ type: 'Text', text: '🧭 pedido 1: "conversa nova"' })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /começou/ })).toBeUndefined()
  })
})

const SAIDA = JSON.stringify({
  gerado_ms: 1,
  horas: 12,
  fontes: { Claude: { ok: true, n: 2 }, 'Codex 1': { ok: true, n: 1 }, ZCode: { ok: false, n: 0, erro: 'banco do ZCode não encontrado' } },
  sessoes: [
    { fonte: 'Claude', id: 'local_a', ids: ['local_a', 'cli-a'], titulo: 'Entender e criar mods', projeto: 'MEGA B R A I N', cwd: 'S:/x', ultima_ms: 1, idade_s: 10, estado: 'agora', automacao: false },
    { fonte: 'Codex 1', id: 'c1', ids: ['c1'], titulo: 'Verificar envio de WhatsApp', projeto: 'Portfolio', cwd: 'S:/p', ultima_ms: 1, idade_s: 1700, estado: 'recente', automacao: false },
    { fonte: 'Codex 2', id: 'c2', ids: ['c2'], titulo: '(sem nome)', projeto: 'Bounty Hunter', cwd: 'S:/b', ultima_ms: 1, idade_s: 30, estado: 'agora', automacao: true },
  ],
})

describe('sessões', () => {
  test('lê a saída do coletor e recusa formato estranho', () => {
    expect(lerSaidaSessoes(SAIDA).sessoes.length).toBe(3)
    expect(() => lerSaidaSessoes('{"fontes":{}}')).toThrow()
  })

  test('faixa conta só conversas; automação fica de fora', () => {
    expect(pedacoSessoes(lerSaidaSessoes(SAIDA))).toEqual({ texto: '🗂 2 sessões · 1 agora', tom: 'ok' })
    expect(pedacoSessoes(null)).toBe(null)
  })

  test('painel agrupa por estado, marca esta sessão, conta automações e fonte não lida', () => {
    const texto = montarPainelSessoes(lerSaidaSessoes(SAIDA), ['cli-a'])
    expect(texto).toContain('### 🟢 Trabalhando agora (até 2 min) (1)')
    expect(texto).toContain('- **Entender e criar mods** ← esta · Claude · MEGA B R A I N · agora')
    expect(texto).toContain('- **Verificar envio de WhatsApp** · Codex 1 · Portfolio · há 28 min')
    expect(texto).toContain('⚙️ +1 automações (claude -p, codex exec), 1 rodando agora')
    expect(texto).toContain('Não lidas: ZCode (banco do ZCode não encontrado)')
    expect(texto).not.toContain('(sem nome)')
  })

  test('/sessoes roda o coletor e a faixa mostra a contagem (terminal e desktop)', async ($, on) => {
    const rodados: string[][] = []
    on('ui.open', () => ({ value: undefined }))
    on('session.id', () => ({ value: 'cli-a' }))
    on('process.run', (_, e) => {
      rodados.push([...e.argv])
      return { value: { exitCode: 0, stdout: SAIDA, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
    })
    const r = await $.command.run({
      command: 'sessoes',
      args: '',
      origin: { kind: 'composer' },
      presentation: { isFullscreen: false, columns: 100 },
    })
    expect(rodados[0]?.slice(-3)).toEqual(['--json', '--horas', '12'])
    expect(rodados[0]?.[1]).toMatch(/coletor[\\/]mb_sessoes\.py$/)
    expect(r.text).toContain('← esta')
    for (const surface of ['terminal', 'desktop'] as const) {
      const ui = await $.ui.mount({ plugin: 'megabrain-mod', surface, component: 'AbovePrompt', props: BANDA })
      expect(await ui.find({ type: 'Text', text: /🗂 2 sessões · 1 agora/ })).toBeDefined()
      expect(await ui.find({ key: 'sessoes' })).toBeDefined()
      await ui.unmount()
    }
  })

  test('coletor quebrado vira aviso, não erro', async ($, on) => {
    on('ui.open', () => ({ value: undefined }))
    on('session.id', () => ({ value: 'x' }))
    on('process.run', () => ({ value: { exitCode: 2, stdout: '', stderr: 'python: not found', isStdoutTruncated: false, isStderrTruncated: false } }))
    const r = await $.command.run({
      command: 'sessoes',
      args: '',
      origin: { kind: 'composer' },
      presentation: { isFullscreen: false, columns: 100 },
    })
    expect(r.text).toContain('Não consegui ler: coletor saiu com código 2: python: not found')
    const ui = await $.ui.mount({ plugin: 'megabrain-mod', surface: 'desktop', component: 'AbovePrompt', props: BANDA })
    expect(await ui.find({ type: 'Text', text: /sessões: não li/ })).toBeDefined()
  })
})

describe('TL;DR com abertura do contrato', () => {
  test('linhas 🪞 ECO e 🧭 bússola antes do TL;DR não disparam o aviso', () => {
    const resposta = [
      '🪞 ECO: entendi "sessões" = conversas de IA do PC.',
      '🧭 MEGA B R A I N · começou: "mods" · agora: "sessões" · passo 3/3',
      '**TL;DR + /leigolanguage:** pronto.',
      '1. a',
      '2. b',
      '3. c',
      '4. d',
      '5. e',
      '6. f',
    ].join('\n')
    expect(temTldr(resposta, 8)).toBe(true)
    expect(temTldr(resposta.replace('**TL;DR + /leigolanguage:** pronto.', 'Pronto.'), 8)).toBe(false)
  })
})
