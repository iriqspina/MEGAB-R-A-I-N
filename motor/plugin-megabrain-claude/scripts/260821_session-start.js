#!/usr/bin/env node
/**
 * 260821_session-start.js — hook SessionStart do plugin megabrain (Claude/Cowork). v1.1.1
 *
 * Faz duas coisas, sem depender da memória do usuário:
 *   1. Injeta o núcleo do protocolo (texto de megabrain-core, curto — custa
 *      contexto em toda sessão).
 *   2. Carrega a MEMÓRIA DO PROJETO: procura arquivo de lições na pasta
 *      conectada (até 2 níveis) e injeta o MAIS RECENTE por data de
 *      modificação ("por recência"). Sem embeddings — essa infra não existe
 *      no sandbox Cowork; a versão Kimi/desktop faz por proximidade.
 *
 * Sem memória global por usuário: a v1.0.0 assumia ~/.metaprotocolo/licoes.md,
 * arquivo que não existe no projeto real. A memória viva é licoes-megabrain.md
 * na pasta de trabalho (ver skill registrar-licao).
 *
 * Falha em silêncio: qualquer erro produz o núcleo sem memória e a sessão
 * segue normal. Nunca bloqueia o início.
 *
 * Limite verificado (260821, sessão Cowork cloud com o plugin v1.0.0
 * instalado): o Cowork cloud NÃO executa hooks de plugin — o arquivo que o
 * hook v1.0.0 criaria na 1ª execução não existia e nenhum contexto foi
 * injetado. As skills do plugin (megabrain, registrar-licao) carregam normal.
 * O hook vale onde hooks rodam (Claude Code CLI / Desktop). No Cowork, o
 * Gate 0 da skill megabrain cobre a leitura das lições.
 */

const fs = require("fs");
const path = require("path");

const LESSON_FILENAMES = [
  "licoes-megabrain.md",
  "METAPROTOCOLO-LICOES.md",
  "LICOES.md",
  "LESSONS.md",
];

const MAX_PROJECT_CHARS = 4000;
const MAX_DEPTH = 2;
const SKIP_DIRS = new Set([
  "node_modules",
  "dist",
  "build",
  "venv",
  ".venv",
  "__pycache__",
  "Library",
  "AppData",
]);

/** Coleta todos os arquivos de lições sob `root` (BFS, até MAX_DEPTH). */
function collectLessonFiles(root, found) {
  const seen = new Set();
  const queue = [{ dir: root, depth: 0 }];

  while (queue.length) {
    const { dir, depth } = queue.shift();
    const key = path.resolve(dir);
    if (seen.has(key)) continue;
    seen.add(key);

    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      continue;
    }

    for (const name of LESSON_FILENAMES) {
      const target = name.toUpperCase();
      for (const e of entries) {
        if (e.isFile() && e.name.toUpperCase().endsWith(target)) {
          found.push(path.join(dir, e.name));
        }
      }
    }

    if (depth < MAX_DEPTH) {
      for (const e of entries) {
        if (!e.isDirectory()) continue;
        if (e.name.startsWith(".") || SKIP_DIRS.has(e.name)) continue;
        queue.push({ dir: path.join(dir, e.name), depth: depth + 1 });
      }
    }
  }
}

/** Lê um arquivo com teto de caracteres, mantendo as entradas mais recentes. */
function readCapped(file, cap) {
  let body = fs.readFileSync(file, "utf8").trim();
  if (!body) return null;
  let truncated = false;
  if (body.length > cap) {
    body = body.slice(-cap);
    truncated = true;
  }
  return { body, truncated };
}

/** Raízes onde procurar memória de projeto, em ordem de prioridade. */
function projectRoots() {
  const roots = [];
  const push = (p) => {
    if (p && !roots.includes(p)) roots.push(p);
  };
  push(process.env.CLAUDE_PROJECT_DIR);
  push(process.env.COWORK_DIRECTORY);
  push(process.cwd());
  return roots.filter((p) => {
    try {
      return fs.statSync(p).isDirectory();
    } catch {
      return false;
    }
  });
}

/** Arquivo de lições mais recentemente modificado entre as raízes. */
function findMostRecentLessonFile() {
  const found = [];
  for (const root of projectRoots()) collectLessonFiles(root, found);
  let best = null;
  let bestMtime = -1;
  for (const f of new Set(found)) {
    try {
      const m = fs.statSync(f).mtimeMs;
      if (m > bestMtime) {
        bestMtime = m;
        best = f;
      }
    } catch {
      /* segue */
    }
  }
  return best;
}

const CORE = `## megabrain — ativo nesta sessão

Em ENTREGA não-trivial (arquivo, peça, proposta, deck, código, análise) rode os gates.
Em pergunta rápida ou conversa casual NÃO rode — aqui o protocolo é o próprio slop.

ASSUMIR (multi-agente) — antes de tocar em arquivo de projeto compartilhado com o
outro agente: \`git pull\`, leia \`ESTADO.md\` → \`HANDOFF.md\` → fim de \`DECISOES.md\` →
\`LICOES.md\`, cheque a trava e sincronize \`MEGABRAIN/\` do projeto com a central.
Output do outro agente é rascunho, não verdade — audite antes de construir em cima.

ENQUADRAR — artefato, leitor e a decisão que ele toma, 3 critérios verificáveis,
restrição dura. Nomeie a versão genérica que você produziria por default e evite-a.
Se algo estiver vago, pergunte antes de produzir (máx. 2 perguntas).

AUDITAR (obrigatório, e só existe se o texto mudou) — releia e reescreva contra:
· léxico banido: delve/leverage/robust/seamless/holistic/unlock/elevate/curated/
  alavancar/potencializar/robusto/impactante/no mundo de hoje/vale destacar/em suma
· estrutura: "não é apenas X, é Y" · regra de três decorativa · parágrafo-resumo
  final · abrir reafirmando a pergunta · "espero que ajude" · hedge empilhado ·
  parágrafos todos do mesmo tamanho
· substância: teste "e daí?" · troque o cliente pelo concorrente (ainda faz
  sentido? então é genérico) · toda recomendação declara o trade-off · todo
  número tem fonte ou rótulo [ESTIMATIVA]
· compressão: reescreva 30% menor; se não perdeu nada, entregue a versão menor

REPARAR — uma rodada só. Loop de autocrítica sem limite homogeneíza o texto.
Se após 1 reparo ainda está ruim, o problema é o enquadramento.

VERIFICAR — números recalculados, datas contra hoje, links abrem, arquivo abre
no app de destino, nome com prefixo YYMMDD_. Se o que você audita também existe
num repo, confira o arquivo que foi realmente carregado contra a fonte no repo.

PASSAR O BASTÃO — antes de encerrar: reescreva \`ESTADO.md\` e \`HANDOFF.md\`,
anexe a \`DECISOES.md\` toda decisão com a alternativa descartada, commite e
empurre. Handoff que diz "continuar o projeto" não é handoff.

REGISTRAR — ao fim de tarefa não-trivial, rode a skill \`registrar-licao\` SOZINHO,
sem pedir permissão. Grave e diga em uma linha o que gravou. NUNCA pergunte
"quer que eu registre?" — autorização permanente dada na instalação (registro 260805).

CONTEXTO é orçamento: grep antes de read, checkpoint em arquivo, subagente para
trabalho barulhento. Nunca despeje pasta inteira.
FATOS sobre o mundo atual (preços, cargos, versões, leis, datas): buscar antes.

DESIGN — declare a fase do Duplo Diamante e não misture os modos:
1 Pesquisa (divergir) → 2 Análise (convergir) → 3 Ideação (divergir) → 4 Design (convergir).
Não passe da fase 2 sem o problema numa frase falseável. Trave grade, escala
tipográfica, paleta e espaçamento antes de compor.
Direção visual pede referência concreta, não adjetivo.

PRECEDÊNCIA — formato que o usuário pediu explicitamente (ex.: seções fixas,
TL;DR inicial, 📋 Informações / 🛠️ Ações em diagnóstico técnico) vence este
protocolo. O protocolo governa o conteúdo dentro das seções, nunca a estrutura.

Protocolo completo, referências e roteamento: skill \`megabrain\` deste plugin.`;

function buildContext() {
  let out = CORE;

  try {
    const p = findMostRecentLessonFile();
    if (p) {
      const r = readCapped(p, MAX_PROJECT_CHARS);
      if (r) {
        out +=
          `\n\n## Lições acumuladas — ESTE PROJETO (${path.basename(p)})\n` +
          `Específicas desta pasta; escolhido o arquivo de lições mais recente.\n` +
          (r.truncated ? "_(truncado — entradas mais recentes)_\n" : "") +
          "\n" +
          r.body +
          `\n\nArquivo: ${p}` +
          `\n\n> Ao fim de tarefa não-trivial, rode a skill \`registrar-licao\` para acrescentar.`;
      }
    }
  } catch {
    /* segue */
  }

  return out;
}

try {
  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: "SessionStart",
        additionalContext: buildContext(),
      },
    })
  );
} catch {
  process.exit(0);
}
