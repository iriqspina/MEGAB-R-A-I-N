"""Leva as respostas confirmadas de um relatório até um terminal bash com a IA escolhida.

O relatório isolado não executa rede nem processos; o despacho acontece no
servidor: grava prompt + respostas dentro do projeto, monta um script bash
inspecionável e abre uma janela nova do terminal rodando a CLI escolhida
(com modelo e effort de linha de comando, quando a CLI suporta).
"""
from __future__ import annotations
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

APP = Path(__file__).resolve().parent

# Catálogo das IAs de terminal desta máquina. 'padrão' omite a flag; 'outro'
# aceita texto livre do relatório (validado em _LIVRE). As listas espelham o
# seletor do motor/modelos/interacoes/261010_decisoes-respondiveis; a decisão
# final é sempre revalidada aqui.
#
# Batido em 20/10/2026 (comentário do <USUARIO> no painel "Enviar pro terminal")
# contra as fontes LOCAIS de cada vendor, sem gastar IA:
# - Codex (codex-cli 0.163.0): esforços do próprio app em ~/.codex/config.toml
#   (`enabled-reasoning-efforts`): low, medium, high, xhigh, ultra, max.
#   "minimal" saiu (não está no seletor); ultra e max entraram.
# - Claude Code 2.1.302 (`claude --help`): `--effort` aceita low, medium,
#   high, xhigh, max; `--model` aceita os aliases fable, opus, sonnet.
# - ZCode 0.16.9 (`zcode --help` completo, ajuste da revisão n2, + ~/.zcode/v2/
#   provider_config.json): `--model <provider/model>` vale para a execução
#   --prompt (ex.: zai/GLM-5.3; plano expõe GLM-5.3 e GLM-5.3-Flash). Sem flag
#   de effort — as variantes low/high/max ficam na sessão/config.
# - Gemini CLI 0.58.0: `-m` modelo; sem effort. Login quebrado desde 261014
#   (Antigravity) — nota mantida até nova sessão autenticada.
# - Kimi: conta cancelada em 16/09/2026 (decisão 260916e — não rotear p/ Kimi);
#   saiu do catálogo para não oferecer despacho que falha.
CATALOG = {
    'claude': {
        'nome': 'Claude Code', 'exe': 'claude', 'prompt_inicial': True,
        'modelos': ['padrão', 'fable', 'opus', 'sonnet', 'haiku', 'outro'],
        'efforts': ['padrão', 'low', 'medium', 'high', 'xhigh', 'max'],
    },
    'codex': {
        'nome': 'Codex', 'exe': 'codex', 'prompt_inicial': True,
        'modelos': ['padrão', 'gpt-6.1-sol', 'outro'],
        'efforts': ['padrão', 'low', 'medium', 'high', 'xhigh', 'ultra', 'max'],
    },
    'zcode': {
        'nome': 'ZCode (GLM)', 'exe': 'zcode', 'prompt_inicial': True,
        'modelos': ['padrão', 'zai/GLM-5.3', 'zai/GLM-5.3-Flash', 'outro'],
        'efforts': ['—'],
        'nota': 'modelo vai por --model provider/model; esforço (low/high/max) fica na sessão',
    },
    'gemini': {
        'nome': 'Gemini', 'exe': 'gemini', 'prompt_inicial': True,
        'modelos': ['padrão', 'gemini-2.5-pro', 'gemini-2.5-flash', 'outro'],
        'efforts': ['—'],
        'nota': 'sem effort no Gemini CLI; login pendente desde 261014',
    },
}

# Aceita '/' pelo formato provider/model do ZCode (zai/GLM-5.3).
_LIVRE = re.compile(r'^[A-Za-z0-9._:/\-\[\]]{1,80}$')
_TESTE = os.environ.get('MEGBRAIN_DISPATCH_TEST') == '1'


def _posix(path: Path) -> str:
    """Caminho com barra normal, aceito por bash e pelas CLIs no Windows."""
    return str(path).replace('\\', '/')


def validar(body: dict) -> tuple[str, str, str]:
    """Confere ia/modelo/effort contra o catálogo; devolve os valores prontos."""
    ia = body.get('ia')
    if ia not in CATALOG:
        opcoes = ', '.join(sorted(CATALOG))
        raise ValueError(f'IA de terminal desconhecida. Use uma destas: {opcoes}.')
    entrada = CATALOG[ia]
    modelo = body.get('modelo') or 'padrão'
    if modelo not in entrada['modelos']:
        if not _LIVRE.match(modelo):
            raise ValueError('Modelo inválido.')
    else:
        modelo = 'padrão' if modelo == 'padrão' else modelo
    effort = body.get('effort') or 'padrão'
    if effort != 'padrão' and effort not in entrada['efforts']:
        raise ValueError('Effort inválido para esta IA.')
    exe = shutil.which(entrada['exe'])
    if not exe and not _TESTE:
        raise ValueError(f"{entrada['nome']} não está instalado neste computador (comando '{entrada['exe']}' não encontrado).")
    return ia, modelo, effort


def _linha_cli(ia: str, modelo: str, effort: str, prompt_var: str, prompt_txt: str) -> str:
    """Linha de terminal que entrega o prompt na CLI escolhida."""
    if ia == 'claude':
        flags = []
        if modelo != 'padrão':
            flags.append(f'--model {modelo}')
        if effort != 'padrão':
            flags.append(f'--effort {effort}')
        return f'run claude {" ".join(flags)} "$PROMPT"'.replace('  ', ' ').strip()
    if ia == 'codex':
        flags = []
        if modelo != 'padrão':
            flags.append(f'-m {modelo}')
        if effort != 'padrão':
            flags.append(f"-c 'model_reasoning_effort=\"{effort}\"'")
        return f'run codex {" ".join(flags)} "$PROMPT"'.replace('  ', ' ').strip()
    if ia == 'zcode':
        # zcode sem subcomando abre a TUI e um prompt posicional vira "Unknown
        # command" (verificado 261014). -p entrega o despacho de uma vez no
        # terminal, sem passo manual de copiar. --model (provider/model) vai
        # ANTES de -p: `-p` seguido de outra flag é ambíguo no parser (0.16.9).
        if modelo != 'padrão':
            return f'run zcode --model {modelo} -p "$PROMPT"'
        return 'run zcode -p "$PROMPT"'
    if ia == 'gemini':
        flags = f'-m {modelo}' if modelo != 'padrão' else ''
        # Gemini CLI recusa pasta não confiável no modo não interativo (verificado
        # 261014 em VAMO); o despacho roda no projeto, então declara confiança
        # explícita — é a rota documentada para ambientes automatizados.
        return f'GEMINI_CLI_TRUST_WORKSPACE=true run gemini {flags} -i "$PROMPT"'.replace('  ', ' ').strip()
    # kimi saiu do catálogo em 261020 (conta cancelada 16/09, decisão 260916e); nenhuma IA nova
    # chega aqui sem linha de comando registrada.
    raise ValueError(f'Sem linha de comando registrada para "{ia}".')


def _bash_exe() -> str:
    for candidate in (shutil.which('bash'), r'C:\Program Files\Git\bin\bash.exe', r'C:\Program Files\Git\usr\bin\bash.exe'):
        if candidate and Path(candidate).is_file():
            return candidate
    raise ValueError('Git Bash não encontrado para abrir o terminal do despacho.')


def dispatch(path: Path, root: Path, body: dict) -> dict:
    from central_project_control import check_path
    check_path(root)
    """Grava o pacote no projeto e abre o terminal. Devolve o recibo para a página."""
    ia, modelo, effort = validar(body)
    entrada = CATALOG[ia]
    agora = dt.datetime.now()
    pasta = root / '.mb-dispatch' / (agora.strftime('%y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6])
    pasta.mkdir(parents=True, exist_ok=True)

    resumo = body.get('resumo_texto')
    if not isinstance(resumo, str) or not resumo.strip():
        raise ValueError('Resumo das respostas ausente; finalize antes de despachar.')
    resumo = resumo[:30000]
    respostas = body.get('respostas') if isinstance(body.get('respostas'), dict) else {}
    notas = body.get('notas') if isinstance(body.get('notas'), list) else []
    pacote = {
        'versao': 1, 'finalizado': True, 'enviado_em': agora.isoformat(timespec='seconds'),
        'titulo': str(body.get('titulo') or path.stem)[:200], 'relatorio': path.name,
        'projeto': str(root), 'ia': entrada['nome'], 'modelo': modelo, 'effort': effort,
        'respostas': respostas, 'notas': notas, 'resumo_texto': resumo,
    }
    if len(json.dumps(pacote, ensure_ascii=False)) > 400000:
        raise ValueError('Pacote de respostas grande demais para despachar.')

    respostas_json = pasta / 'respostas.json'
    respostas_json.write_text(json.dumps(pacote, ensure_ascii=False, indent=2), encoding='utf-8')
    prompt_txt = pasta / 'prompt.txt'
    prompt_txt.write_text(
        'DESPACHO MEGABRAIN — respostas confirmadas pelo <USUARIO>\n'
        f"Relatório: {path.name}\nProjeto: {root}\nEnviado em: {agora.isoformat(timespec='seconds')}\n"
        f"IA escolhida: {entrada['nome']} (modelo: {modelo}, effort: {effort})\n"
        '\n' + resumo + '\n\n'
        'Instrução: estas são as decisões dele para este relatório. Leia ESTADO.md/HANDOFF.md do '
        'projeto se existirem, aja nas respostas dentro do projeto e mantenha a pasta '
        '00_PARA-VOCE como porta de entrega. O pacote completo está em respostas.json ao lado deste prompt.\n',
        encoding='utf-8',
    )

    p_prompt, p_json = _posix(prompt_txt), _posix(respostas_json)
    cli = _linha_cli(ia, modelo, effort, '$PROMPT', p_prompt)
    if _TESTE:
        cli = f'echo "[TESTE] executaria: {cli}"'
    nota = entrada.get('nota')
    script = pasta / 'abrir.sh'
    script.write_text('\n'.join([
        '#!/usr/bin/env bash',
        f'# Despacho MEGABRAIN · {agora.strftime("%d/%m/%Y %H:%M")} · {path.name}',
        'clear',
        'echo "════════════════════════════════════════════════════"',
        f'echo " RESPOSTAS DO <USUARIO> · {entrada["nome"]}"',
        f'echo " projeto: {_posix(root)}"',
        'echo "════════════════════════════════════════════════════"',
        f'cat \'{p_prompt}\'',
        'echo',
        'echo " arquivo completo: ' + p_json + '"',
        nota and f'echo " nota: {nota}"' or 'true',
        'echo "════════════════════════════════════════════════════"',
        'run(){ local n="$1"; shift; local c; for c in "$n" "$n.cmd" "$n.exe"; do if command -v "$c" >/dev/null 2>&1; then "$c" "$@"; return; fi; done; echo ""; echo "⚠ \'$n\' não encontrado neste terminal. As respostas continuam em ' + p_prompt + '"; }',
        f'PROMPT="$(cat \'{p_prompt}\')"',
        cli,
        'echo',
    ] + ([] if _TESTE else ['read -p "Enter para fechar…" ignored']) + [
        '',
    ]), encoding='utf-8', newline='\n')

    bash = _bash_exe()
    p_script = _posix(script)
    wt = shutil.which('wt.exe')
    if wt:
        subprocess.Popen([wt, '-d', str(root), bash, '-l', p_script], cwd=str(root))
        terminal = 'Windows Terminal'
    else:
        subprocess.Popen([bash, '-l', p_script], cwd=str(root), creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP)
        terminal = 'console bash'

    log = root / '.mb-log'
    log.mkdir(parents=True, exist_ok=True)
    registro = dict(pacote)
    registro.update(terminal=terminal, script=str(script), at=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'))
    with (log / f'despachos-{agora.strftime("%y%m%d")}.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(registro, ensure_ascii=False) + '\n')

    return {
        'ok': True, 'ia': entrada['nome'], 'modelo': modelo, 'effort': effort,
        'terminal': terminal, 'script': str(script), 'respostas': str(respostas_json),
        'message': f"Terminal {terminal} aberto com {entrada['nome']}" + (f' (modelo {modelo}, effort {effort})' if modelo != 'padrão' or effort != 'padrão' else '') + '. As respostas dele aparecem lá e a IA já recebe.',
    }
