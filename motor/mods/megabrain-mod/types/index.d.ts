// Contrato de estado do megabrain-mod: o que o mod guarda durante a sessão.
// Você não precisa mexer aqui.

export type Projeto = {
  /** Nome da pasta aberta no Claude. */
  nome: string
  /** Achou ESTADO.md em alguma das pastasDeEstado? */
  temMegabrain: boolean
  /** Pasta onde o ESTADO.md foi achado ('' = a própria pasta aberta). */
  pasta: string
  /** Linha MODO: do ESTADO.md. */
  modo: string
  /** Primeiro título "## ..." do ESTADO.md (o estado vigente). */
  vigente: string
  /** Primeira linha "TL;DR:" do ESTADO.md. */
  tldr: string
  /** Valor de TRAVADO_POR: no HANDOFF.md ("livre" quando ninguém trava). */
  trava: string
  /** Bloco PARA VOCÊ do HANDOFF.md. */
  paraVoce: string
  /** Onde o mod procurou o ESTADO.md. */
  procurado: string[]
}

export type Auditoria = {
  /** Respostas do Claude auditadas nesta sessão. */
  respostas: number
  /** Quantas tinham léxico banido. */
  comSlop: number
  /** Quantas eram longas e não abriam com TL;DR. */
  semTldr: number
  /** Termos banidos achados na última resposta. */
  ultimasPalavras: string[]
  /** A última resposta faltou TL;DR? */
  ultimaSemTldr: boolean
}

export type Rumo = {
  /** 1º pedido da pessoa nesta sessão (sem os avisos do sistema). */
  primeiro: string
  /** Pedido mais recente. */
  atual: string
  /** Quantos pedidos a pessoa fez nesta sessão. */
  n: number
}

export type Sessao = {
  /** Claude, Claude terminal, Codex 1, Codex 2, ZCode. */
  fonte: string
  id: string
  /** Todos os ids que apontam pra esta sessão (app + conversa). */
  ids: string[]
  titulo: string
  projeto: string
  cwd: string
  ultima_ms: number
  idade_s: number
  /** agora (≤ 2 min) · recente (≤ 1 h) · parada (dentro da janela). */
  estado: 'agora' | 'recente' | 'parada'
  /** claude -p e codex exec: trabalhadores, não conversas suas. */
  automacao: boolean
}

export type Sessoes = {
  gerado_ms: number
  horas: number
  fontes: Record<string, { ok: boolean; n: number; erro?: string }>
  sessoes: Sessao[]
  /** Preenchido quando o coletor nem rodou (Python ausente, erro). */
  erro?: string
}

declare module 'claude-code' {
  interface PluginState {
    'megabrain-mod': {
      projeto: Projeto | null
      editados: string[]
      lidos: string[]
      auditoria: Auditoria
      registrou: boolean
      faixaOculta: boolean
      rumo: Rumo | null
      sessoes: Sessoes | null
    }
  }
}
