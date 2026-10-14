// =====================================================================
//  AJUSTES DO MEGABRAIN-MOD — o único arquivo que você precisa mexer
// =====================================================================
//
//  Como mexer:
//   1. Pra ligar ou desligar uma peça, troque true por false (ou o contrário).
//   2. Nas listas, cada item vai entre aspas simples e termina com vírgula.
//   3. Salve. O mod recarrega sozinho quando o Claude termina a próxima
//      resposta (ou na hora, se você salvou com o Claude parado).
//
//  Se quebrar (faltou uma aspa ou vírgula): aparece uma linha cinza no
//  Claude dizendo que o megabrain-mod não carregou. Peça pro Claude:
//  "conserta o AJUSTES.ts do megabrain-mod". Seu projeto não é afetado;
//  só o mod fica desligado até consertar.
//
//  Também dá pra pedir direto: "no megabrain-mod, desliga o TL;DR" — o
//  Claude edita este arquivo por você.
// =====================================================================

import type { Ajustes } from './hooks/regras'

export const AJUSTES: Ajustes = {
  // ─── 1. FAIXA ACIMA DO CAMPO DE DIGITAR ───────────────────────────
  // Uma linha fixa: projeto · trava · arquivos mexidos · bastão · AUDITAR.
  // Botões "painel" e "ocultar" na própria faixa. /mb traz de volta.
  faixa: true,

  // Bússola: embaixo da faixa, o 1º pedido da sessão e o pedido atual
  // (até 8 palavras cada). O texto inteiro aparece no painel /mb.
  bussola: true,

  // Sessões: na faixa, quantas conversas de IA você tem neste PC (Claude no
  // app e no terminal, Codex 1, Codex 2, ZCode) e quantas estão trabalhando
  // agora. /sessoes (ou o botão "sessões") abre a lista com título e projeto.
  // Só lê o que cada programa já guarda no disco; não mexe em nada.
  sessoes: true,
  sessoesJanelaHoras: 12, // mostra o que teve atividade nas últimas N horas
  sessoesAtualizarSegundos: 60, // de quanto em quanto tempo relê
  python: 'python', // programa que roda o coletor (coletor/mb_sessoes.py)

  // ─── 2. VIGIA DE SLOP (gate AUDITAR) ──────────────────────────────
  // Depois de cada resposta do Claude, procura os termos da lista abaixo.
  vigiaSlop: true,

  // Achou slop ou faltou TL;DR? true = além do aviso na tela, o mod deixa
  // um bilhete escondido pro Claude corrigir na próxima resposta.
  // false = só avisa você.
  avisarOClaude: true,

  // Termos banidos. Maiúscula e acento não importam.
  // Terminou com * = vale qualquer final (robust* pega robusto, robusta).
  // Sem * = só a palavra ou frase exata.
  // Texto dentro de `código` ou bloco de código é ignorado.
  // Fonte: motor/referencias/260810_anti-slop.md (camada 1) + protocolo.
  palavrasBanidas: [
    // inglês
    'delve*',
    'leverag*',
    'robust*',
    'seamless*',
    'holistic*',
    'unlock',
    'elevate',
    'curated',
    'tapestry',
    'game-changer',
    "let's dive in",
    // português
    'alavanc*',
    'potencializ*',
    'impactante*',
    'no mundo de hoje',
    'no cenário atual',
    'vale destacar',
    'vale ressaltar',
    'é importante ressaltar',
    'cabe ressaltar',
    'em suma',
    'em resumo',
    'em conclusão',
    'sinergia',
    'disruptiv*',
    'entregar valor',
    'fazer a diferença',
    // estrutura
    'não é apenas',
    'espero que ajude',
    'espero ter ajudado',
  ],

  // ─── 3. TL;DR NO TOPO ─────────────────────────────────────────────
  // Resposta longa tem que abrir com TL;DR (nas 2 primeiras linhas).
  exigirTldr: true,
  // Respostas com menos linhas que isso contam como papo (N0) e passam.
  tldrAPartirDeLinhas: 8,

  // ─── 4. GUARDA DE COMANDOS PERIGOSOS ──────────────────────────────
  // 'perguntar' = o Claude abre a caixa de autorização antes de rodar.
  //               Atenção: no modo "sem permissões" (bypass) o Claude
  //               pode aprovar a caixa sozinho. Se quiser trava de verdade,
  //               use 'bloquear'.
  // 'bloquear'  = recusa sempre; o Claude tem que te pedir no chat e você
  //               roda (ex.: pelo 11_enviar-pro-github.cmd).
  // 'desligado' = não vigia nada.
  guardaComandos: 'perguntar',

  // Se um comando tiver estas palavras, nesta ordem, a guarda age.
  // Vale pro terminal do Claude e pro Desktop Commander.
  comandosVigiados: [
    'git push',
    'git commit',
    'git reset --hard',
    'git clean',
    'git rebase',
    'git merge',
    'git branch -D',
    'git stash drop',
    'rm -r',
    'Remove-Item -Recurse',
    'rmdir /s',
    'rd /s',
    'del /s',
    'taskkill',
    'Stop-Process',
  ],

  // ─── 5. ARQUIVOS QUE O CLAUDE NÃO EDITA ───────────────────────────
  // Recusa na hora (o Claude recebe o motivo e procura outro caminho).
  protegerArquivos: true,

  // Arquivos com segredo (senha, chave). * = qualquer coisa.
  arquivosSecretos: [
    '.env',
    '.env.local',
    '.env.production',
    '*.pem',
    '*.key',
    'id_rsa',
    'id_ed25519',
  ],

  // Pastas que são CÓPIA gerada por script. Edita-se a fonte e roda o
  // gerador; editar a cópia some na próxima geração.
  pastasGeradas: [
    'motor/plugin-megabrain-claude/skills',
    '_github/export',
    '_github/repo-local',
  ],

  // ─── 6. LEMBRETES (não bloqueiam, só avisam o Claude) ─────────────
  // Mexeu em .cmd → lembra: CRLF, sem BOM, ASCII (regra 260824).
  // (Editar .cmd com edit_block do Desktop Commander é sempre recusado
  //  quando protegerArquivos está ligado.)
  lembrarCmd: true,

  // Arquivo NOVO nestas pastas sem prefixo AAMMDD_ → lembra de renomear.
  exigirDataNoNome: true,
  pastasComData: ['00_PARA-VOCE', '03_docs', '04_visuais'],

  // ─── 7. PASSAR O BASTÃO ───────────────────────────────────────────
  // A partir de quantos arquivos mexidos a faixa cobra ESTADO e HANDOFF.
  bastaoAPartirDe: 3,

  // ─── 8. ONDE O MOD PROCURA O ESTADO DO MEGABRAIN ──────────────────
  // Pastas (a partir da pasta aberta no Claude) onde podem estar o
  // ESTADO.md e o HANDOFF.md. '' = a própria pasta aberta.
  // Procura na ordem e para no primeiro que achar.
  pastasDeEstado: ['', 'memoria/estado', 'MEGABRAIN'],
}
