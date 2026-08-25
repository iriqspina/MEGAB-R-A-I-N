#!/usr/bin/env python3
"""
mb_registro.py — o que o <USUARIO> CLICA e o que ele CHAMA, declarado num lugar só.

Por que existe (260825, decisão 260825l): ele pediu "clica no script 3" em vez
de "clica no publicar-e-fotografar". Número só serve se não mudar. Se sair da
ordem alfabética da pasta, entra um botão novo e o 3 vira outro na semana
seguinte — e a frase que eu escrevi na resposta de hoje passa a apontar pro
lugar errado.

Aqui o número é DECLARADO. Regras:
  1. Botão novo entra NO FIM, com o próximo número livre.
  2. Número de botão aposentado NUNCA é reusado — vira buraco na sequência.
  3. Este arquivo manda; `bin/mb-numerar-acoes.py` renomeia o disco pra bater,
     e `bin/mb-relatorio-vivo.py` monta o painel a partir daqui.

Duas listas, dois leitores diferentes:
  ACOES  — o que ele clica na pasta 01_acoes/ (numerado, aparece no painel)
  ROTINA — o que roda de vez em quando, por comando (sem número, retrátil)
"""

from __future__ import annotations

# (número, apelido do arquivo sem prefixo, o que faz em uma linha, quando usar)
ACOES = [
    (1, "ABRIR-RELATORIO",
     "Regenera e abre este painel.",
     "Sempre que sentar no PC e quiser saber onde as coisas estão."),
    (2, "compreender-padroes",
     "Cruza pendências, cérebro, docs, visuais e telemetria e aponta o que já se repete e ainda não virou modelo.",
     "Quando sentir que está refazendo a mesma coisa e não sabe o quê."),
    (3, "abrir-cerebro-obsidian",
     "Abre memoria/cerebro no Obsidian, com o grafo de wikilinks montado.",
     "Pra navegar o que você sabe (cliente, mercado, referência) em vez de procurar por pasta."),
    (4, "novo-projeto",
     "Cria um projeto novo já com uma cópia do megabrain dentro.",
     "No começo de qualquer trabalho que vá durar mais de uma sessão."),
    (5, "sincronizar-projetos",
     "Leva a central (lições, VERSAO, skills) para as cópias de megabrain dos projetos.",
     "Depois de mexer na central. Se não rodar, os projetos ficam com a memória velha."),
    (6, "sincronizar-identidade",
     "Leva seu perfil e o contrato de resposta para os 6 agentes (Claude, Gemini, Kimi ×2, Codex, output style).",
     "Depois de editar memoria/identidade/. Nunca edite as cópias — só a fonte."),
    (7, "instalar-identidade",
     "Primeira instalação do perfil numa máquina nova.",
     "Uma vez por computador. Depois disso é o 6 que mantém."),
    (8, "refresh-plugin-kimi",
     "Atualiza o plugin do Kimi a partir da central, com backup e conferência de hash do hook.",
     "Depois de mexer em skill ou no hook. Sem isso o Kimi roda a versão velha."),
    (9, "abrir-kimi-visual",
     "Abre o Kimi já apontado para a pasta visual.",
     "Quando for trabalhar peça visual com o Kimi."),
    (10, "publicar-e-fotografar",
     "Gera o pacote público sanitizado e espelha no clone local do repositório.",
     "Antes de subir qualquer coisa pro GitHub. Ele NÃO faz push."),
    (11, "enviar-pro-github",
     "Sobe o pacote público. Pede confirmação.",
     "Só depois do 10, e só quando você quiser publicar de verdade."),
]

# Comandos que rodam de vez em quando. Sem número: você não procura por eles
# na pasta, você chama quando precisa — e a IA sabe qual é.
ROTINA = [
    ("python bin/mb-testar.py",
     "Roda a suíte inteira.",
     "Depois de qualquer mexida em bin/. Verde é pré-requisito de entrega."),
    ("python bin/mb-preflight.py --repo .",
     "Confere git, skills instaladas × fonte, fatos vencidos, resíduo de nome antigo e CRLF dos .cmd.",
     "Gate 0: no começo da sessão, antes de editar."),
    ("python bin/mb-sync.py --dir . status",
     "Diz se algum agente está com a trava do projeto.",
     "Antes de escrever em arquivo compartilhado com outra IA."),
    ("python bin/mb-indice-licoes.py --indexar --force",
     "Reindexa as lições para o hook conseguir injetar as relevantes.",
     "Depois de acrescentar lição na mão."),
    ("python bin/mb-relatorio-dna.py",
     "Regenera o relatório que explica o PROTOCOLO para quem chega de fora.",
     "Quando o protocolo mudar de forma, não a cada sessão."),
    ("python bin/mb-numerar-acoes.py",
     "Confere se os números dos botões batem com este registro (dry-run).",
     "Depois de acrescentar um botão em 01_acoes/."),
    ("python bin/mb-recuperar-megabrain.py",
     "Utilitário de desastre: restaura a central a partir de backup.",
     "Só quando algo se perdeu. Leia o cabeçalho dele antes."),
]

# Skills DELE. As de plugin de terceiro (cloudflare, figma, adobe, wordpress,
# canva) ficam de fora de propósito: são 30+ e ele não as escreveu nem as
# mantém. Se quiser uma aqui, acrescente — a lista é declarada, não varrida.
#   (nome, de onde vem, o que faz, gatilho)
SKILLS_DELE = [
    ("megabrain", "central",
     "O protocolo: gates 0–7 de entrega anti-slop, Duplo Diamante, roteamento e regras de ouro.",
     "/megabrain · abrir ou retomar projeto · qualquer entrega complexa"),
    ("grelhar", "central",
     "Entrevista em rodadas que esvazia o briefing antes de produzir. Pergunta numerada COM recomendação; fato é do agente, decisão é sua.",
     "/grelhar · \"me grelha\" · automático no Gate 1"),
    ("ingerir", "central",
     "Pega fonte bruta (artigo, PDF, transcrição, briefing) e destila em página de wiki e card de pessoa no cérebro.",
     "/ingerir · \"joga no cérebro\" · arquivo novo em cerebro/raw/"),
    ("traycer", "central",
     "O Traycer rodando sob os gates: o que ele faz, o que volta pra ESTADO/HANDOFF/DECISOES.",
     "/traycer · epic, core flow, tech plan, ticket breakdown"),
    ("conclusao-megabrain", "central",
     "Ponteiro para o Gate 6. Fecha ESTADO/HANDOFF/DECISOES e esgota execução autônoma antes de te perguntar algo.",
     "/conclusao-megabrain · \"fecha isso\""),
    ("registrar-licao", "plugin",
     "Grava uma lição no formato GATILHO / LIÇÃO / ATALHO.",
     "/registrar-licao · depois de errar e descobrir por quê"),
    ("portfolio", "projeto",
     "Router do seu portfólio (WordPress + Kadence + Figma): mede o estado real e encaminha o próximo passo.",
     "/portfolio · mexer no site, num case ou no Figma"),
    ("tlou", "projeto",
     "Contexto do case TLOU (Foroni × Naughty Dog): protótipo no Figma e conversão pra WordPress.",
     "/tlou"),
    ("conferir-case", "projeto",
     "Confere uma página de projeto contra o briefing — 1:1 com o editor e com a identidade da apresentação.",
     "/conferir-case · auditar ou validar um case"),
    ("sync-portfoliohs", "projeto",
     "Sincroniza os 4 lados do portfólio: workspace, pasta de design, child theme no Local e o Figma.",
     "/sync-portfoliohs"),
    ("writing-for-agents", "Matt Pocock (MIT)",
     "Como escrever documento que agente lê: SKILL.md, AGENTS.md, CLAUDE.md.",
     "/writing-for-agents · ao criar ou editar skill"),
    ("research", "Matt Pocock (MIT)",
     "Investiga uma pergunta contra fonte primária e devolve as descobertas como arquivo .md no repo.",
     "/research · alimenta o /ingerir"),
    ("wait-what", "Matt Pocock (MIT)",
     "Detector de \"isso não fez sentido\": para e reformula a última mensagem em vez de seguir em frente.",
     "/wait-what · quando a resposta anterior não bateu"),
]


def acao_por_numero(n: int):
    for item in ACOES:
        if item[0] == n:
            return item
    return None


def nome_arquivo(n: int, apelido: str) -> str:
    return f"{n:02d}_{apelido}.cmd"
