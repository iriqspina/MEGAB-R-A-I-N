"""Ponte automática: comentário enviado ao projeto → planejador → orquestradores → workers.

Só biblioteca padrão. O servidor importa este módulo; as sessões de IA usam a
mesma lógica pela linha de comando bin/mb-ponte.py, sem passar pela API.

Cada ordem vive dentro do projeto em .mb-ponte/<ordem>/: pedido.json (comentários
literais), nos/<id>/ (TAREFA.md, no.json, saida.log, resultado.md), plano.json e
resultado.json escritos pelo planejador. O nó n0 é o planejador; ele pode abrir
orquestradores, que podem abrir outros orquestradores e workers, até
PROFUNDIDADE_MAX níveis e NOS_MAX nós por ordem.

A ponte não aumenta permissões: cada IA roda com a configuração que o próprio
usuário deu à sua CLI. Chaves de API saem do ambiente da sessão, para ela usar a
assinatura e nunca API paga.
"""
from __future__ import annotations

import datetime as dt
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

from central_bridge_routing import catalogo, presets, validar_rota, normalizar_pipeline

APP = Path(__file__).resolve().parent
CENTRAL = APP.parents[1]
CLI = CENTRAL / 'bin' / 'mb-ponte.py'
HOME = Path.home()
PASTA = '.mb-ponte'
PROFUNDIDADE_MAX = 3
NOS_MAX = 16
TIMEOUT_PADRAO = 3 * 3600
PAPEIS = ('planejador', 'orquestrador', 'worker', 'revisor')
MODOS = ('segundo_plano', 'janela')

# Catálogo: id curto que aparece para o usuário → CLI oficial do fornecedor.
# 'cota' liga ao registro de cotas do MegaBrain (dados/orcamento_ia.json).
VENDORS = {
    'claude': dict(nome='Claude', empresa='Anthropic', cli='Claude Code', exe='claude', cota='claude',
                   candidatos=[HOME / '.local/bin/claude.exe', HOME / '.local/bin/claude']),
    'gpt': dict(nome='GPT', empresa='OpenAI', cli='Codex · conta principal (Codex 1)', exe='codex', cota='codex',
                candidatos=[HOME / 'AppData/Local/Programs/OpenAI/Codex/bin/codex.exe'],
                env={'CODEX_HOME': str(HOME / '.codex')}, login=HOME / '.codex/auth.json'),
    'glm': dict(nome='GLM', empresa='Z.ai', cli='ZCode', exe='zcode', cota='zai', candidatos=[]),
    'gemini': dict(nome='Gemini', empresa='Google', cli='Gemini CLI', exe='gemini', cota='gemini_cli', candidatos=[],
                   env={'GEMINI_CLI_TRUST_WORKSPACE': 'true'}),
}
PREFERENCIA = ('claude', 'gpt', 'glm', 'gemini')
_SEM_API = ('ANTHROPIC_', 'OPENAI_', 'ZAI_')
_SESSAO = {'CLAUDECODE', 'CLAUDE_CODE_ENTRYPOINT', 'CLAUDE_CODE_SSE_PORT', 'CODEX_API_KEY', 'CODEX_BASE_URL',
           'CLAUDE_CODE_USE_BEDROCK', 'CLAUDE_CODE_USE_VERTEX', 'CLAUDE_CODE_USE_FOUNDRY'}


class PonteErro(ValueError):
    """Pedido recusado pela ponte; a mensagem vai para o usuário ou para a IA que pediu."""


def _validar_modo(vendor: str, modo: str) -> None:
    if vendor == 'glm' and modo == 'janela':
        raise PonteErro('GLM com modelo e esforço certificados exige segundo plano; modo janela não confirma esse perfil.')


# ── utilidades ──────────────────────────────────────────────────────────────

def agora() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')


def _ler(path: Path, padrao=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return {} if padrao is None else padrao


def _gravar(path: Path, valor) -> None:
    path = Path(path)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex[:6] + '.tmp')
    tmp.write_text(json.dumps(valor, ensure_ascii=False, indent=2), encoding='utf-8')
    for tentativa in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            # Windows recusa a troca enquanto outro processo lê o arquivo.
            time.sleep(0.05 * (tentativa + 1))
    os.replace(tmp, path)


def _posix(path) -> str:
    return str(path).replace('\\', '/')


def _vivo(pid) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == 'nt':
        # os.kill(pid, 0) encerra o processo no Windows; consulta pelo kernel.
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            return bool(k.GetExitCodeProcess(h, ctypes.byref(code))) and code.value == 259  # STILL_ACTIVE
        finally:
            k.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _cauda(path: Path, limite: int = 1200) -> str:
    try:
        with open(path, 'rb') as f:
            f.seek(0, 2)
            tamanho = f.tell()
            f.seek(max(0, tamanho - limite * 4))
            texto = f.read().decode('utf-8', errors='replace')
    except OSError:
        return ''
    texto = re.sub(r'\x1b\[[0-9;?]*[A-Za-z]', '', texto)
    return texto[-limite:]


def _conflito(erro: Exception) -> bool:
    return type(erro).__name__ == 'Conflict'


# ── fornecedores ativos ─────────────────────────────────────────────────────

def _npm_entrada(shim: str | None) -> list[str] | None:
    """Converte o atalho npm (zcode.cmd, gemini.cmd) em [node, arquivo.js].

    Chamar o .cmd com texto livre passa pelo cmd.exe; chamar o node direto evita
    a reinterpretação de aspas e caracteres do prompt.
    """
    if not shim:
        return None
    base = Path(shim)
    sh = base.with_suffix('') if base.suffix.lower() in {'.cmd', '.bat', '.ps1'} else base
    try:
        texto = sh.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return None
    achado = re.search(r'"\$basedir/(node_modules/[^"]+?\.(?:c?js|mjs))"', texto)
    node = shutil.which('node')
    if not achado or not node:
        return None
    js = sh.parent / achado.group(1)
    return [node, str(js)] if js.is_file() else None


def executavel(vid: str) -> list[str] | None:
    v = VENDORS[vid]
    for candidato in v['candidatos']:
        if Path(candidato).is_file():
            return [str(candidato)]
    achado = shutil.which(v['exe'])
    if not achado:
        return None
    return _npm_entrada(achado) or [achado]


def vendors(central: Path = CENTRAL) -> list[dict]:
    """IAs que este MegaBrain pode iniciar agora, na ordem de preferência.

    Ativa = CLI instalada + (quando o MegaBrain registra cotas) fornecedor
    registrado e não cancelado. Sem registro de cotas (instalação nova), basta a
    CLI. A cota vira aviso, não bloqueio: quem decide gastar é o usuário.
    """
    registro = _ler(Path(central) / 'dados/orcamento_ia.json')
    registro = registro if isinstance(registro, dict) else {}
    usa_registro = any(isinstance(v, dict) for v in registro.values())
    saida = []
    for vid in PREFERENCIA:
        v = VENDORS[vid]
        item = dict(id=vid, nome=v['nome'], empresa=v['empresa'], cli=v['cli'], ativo=False, motivo='', aviso='')
        exe = executavel(vid)
        entrada = registro.get(v['cota'])
        if not exe:
            item['motivo'] = f"{v['cli']} não está instalado neste computador."
        elif v.get('login') and not Path(v['login']).is_file():
            item['motivo'] = f"{v['cli']} sem login neste computador."
        elif usa_registro and not isinstance(entrada, dict):
            item['motivo'] = 'Não está entre as assinaturas registradas no MegaBrain.'
        elif isinstance(entrada, dict) and entrada.get('cancelado_em'):
            item['motivo'] = 'Assinatura cancelada no registro do MegaBrain.'
        else:
            item['ativo'] = True
            item['motivo'] = 'CLI instalada' + (' e assinatura registrada.' if usa_registro else '.')
            ritmo = entrada.get('pacing', {}) if isinstance(entrada, dict) else {}
            status = ritmo.get('status') if isinstance(ritmo, dict) else None
            if status in {'pause', 'desacelerar'}:
                item['aviso'] = 'Cota pede pausa.' if status == 'pause' else 'Cota pede para desacelerar.'
        saida.append(item)
    return saida


def ativos(central: Path = CENTRAL) -> list[str]:
    return [v['id'] for v in vendors(central) if v['ativo']]


# ── comandos das CLIs ───────────────────────────────────────────────────────

PROMPT = object()  # marcador: no script da janela vira "$PROMPT"


def argv(vid: str, prompt, raiz: Path, ultima: Path | None = None, interativo: bool = False,
         perfil: dict | None = None, sessao: str | None = None, settings: Path | None = None) -> list:
    exe = executavel(vid)
    if not exe:
        raise PonteErro(f"{VENDORS[vid]['cli']} não está instalado neste computador.")
    perfil = validar_rota(perfil) if perfil else None
    if perfil and perfil['vendor'] != vid:
        raise PonteErro('Perfil pertence a outro fornecedor.')
    if sessao and not re.fullmatch(r'[A-Za-z0-9_-]{8,160}', sessao):
        raise PonteErro('Identificador real de sessão inválido.')
    if vid == 'claude':
        opcoes = (['--model', perfil['modelo'], '--effort', perfil['effort']] if perfil else [])
        opcoes += ['--resume', sessao] if sessao else []
        if perfil and not interativo:
            opcoes += ['--output-format', 'json']
        return exe + opcoes + ([] if interativo else ['-p']) + [prompt]
    if vid == 'gpt':
        opcoes = (['-m', perfil['modelo'], '-c', 'model_reasoning_effort=' + json.dumps(perfil['effort'])] if perfil else [])
        if interativo:
            return exe + ['-C', str(raiz)] + opcoes + (['resume', sessao] if sessao else []) + [prompt]
        if sessao:
            # exec resume não aceita -C: cwd do processo já é a raiz congelada.
            return exe + ['exec', 'resume', '--skip-git-repo-check'] + opcoes + ['--json'] + (['-o', str(ultima)] if ultima else []) + [sessao, prompt]
        return exe + ['exec', '--skip-git-repo-check', '-C', str(raiz)] + opcoes + (['--json'] if perfil else []) + (['-o', str(ultima)] if ultima else []) + [prompt]
    if vid == 'glm':
        # O ZCode só recebe a primeira mensagem no modo --prompt (a TUI não aceita).
        opcoes = []
        if perfil:
            if settings is None:
                raise PonteErro('GLM exige configuração isolada do perfil antes de iniciar.')
            import model_clients
            node = shutil.which('node')
            if not node:
                raise PonteErro('Node não encontrado para o runtime GLM certificado.')
            exe = [node, str(model_clients.ZCODE)]
            opcoes += ['--settings', str(settings), '--json', '--no-color']
        return exe + ['--prompt', prompt, '--cwd', str(raiz)] + opcoes + (['--resume', sessao] if sessao else [])
    return exe + (['-i', prompt] if interativo else ['-p', prompt, '--yolo'])


def _limpar(chave: str) -> bool:
    return chave.startswith(_SEM_API) or chave in _SESSAO or chave.startswith('CLAUDE_CODE_SESSION')


def ambiente(vid: str, extra: dict | None = None) -> dict:
    env = {k: v for k, v in os.environ.items() if not _limpar(k)}
    env.update(VENDORS[vid].get('env', {}))
    env['PYTHONIOENCODING'] = 'utf-8'
    env.update(extra or {})
    return env


def _glm_isolado(no_dir: Path, perfil: dict, env: dict) -> Path:
    """Perfil do bundle desktop certificado, sem segredo no arquivo nem troca global."""
    import model_clients
    from urllib.parse import urlsplit
    bundle = Path(model_clients.ZCODE)
    if not bundle.is_file() or hashlib.sha256(bundle.read_bytes()).hexdigest() != model_clients.ZCODE_SHA256:
        raise PonteErro('Runtime GLM certificado ausente ou alterado; perfil não iniciado.')
    atual = _ler(Path(model_clients.ZCODE_CONFIG))
    provider = (atual.get('provider') or {}).get('zai') or {}
    options = provider.get('options') or {}
    endpoint = urlsplit(options.get('baseURL', ''))
    if (provider.get('kind') != 'anthropic' or endpoint.scheme != 'https' or endpoint.hostname != 'api.z.ai'
            or endpoint.path.rstrip('/') != '/api/anthropic' or not options.get('apiKey')):
        raise PonteErro('Assinatura Z.ai não confirmada na configuração local certificada.')
    modelo = copy.deepcopy((provider.get('models') or {}).get(perfil['modelo']))
    reasoning = modelo.get('reasoning', {}) if isinstance(modelo, dict) else {}
    if perfil['effort'] not in reasoning.get('levels', []) or not reasoning.get('providerOptionsByLevel', {}).get(perfil['effort']):
        raise PonteErro('Esforço GLM sem correspondência nativa comprovada no catálogo local.')
    reasoning['defaultLevel'] = perfil['effort']
    # A camada de projeto pode sobrepor settings. Recusar configuração concorrente
    # é preferível a executar Flash ou outro esforço silenciosamente.
    raiz = Path(_ler(no_dir.parents[1] / 'pedido.json')['projeto'])
    ancestrais = [raiz] + list(raiz.parents)
    limite = next((i for i, d in enumerate(ancestrais) if (d / '.git').exists()), None)
    camadas = ancestrais[:limite + 1] if limite is not None else [raiz]
    for camada in camadas:
        for nome in ('zcode.json', 'zcode.jsonc', '.zcode.json', '.zcode/config.json', '.zcode/setting.json'):
            if (camada / nome).exists():
                raise PonteErro('Configuração ZCode de projeto pode sobrepor o perfil: ' + str(camada / nome) + '. Revisão local necessária.')
    config = dict(model={'main': 'zai/' + perfil['modelo'], 'lite': 'zai/' + perfil['modelo']},
                  provider={'zai': dict(kind='anthropic', name='Z.ai',
                                      options=dict(baseURL=options['baseURL'], apiKeyRequired=True),
                                      models={perfil['modelo']: modelo})},
                  storage={'dir': str(no_dir / 'zcode-storage'), 'sessionDbPath': str(no_dir / 'zcode-session.sqlite')})
    settings = no_dir / 'zcode-perfil.json'
    if settings.exists():
        # A sessão mantém catálogo, endpoint e DB congelados. Credencial pode ser
        # renovada no ambiente filho sem reescrever a rota de uma sessão existente.
        anterior = _ler(settings)
        if anterior != config:
            raise PonteErro('Configuração GLM original difere do catálogo atual; retomada bloqueada para preservar modelo e sessão.')
    else:
        _gravar(settings, config)
    for k in list(env):
        if k.startswith('ZCODE_'):
            env.pop(k, None)
    env['ZAI_API_KEY'] = options['apiKey']
    env['ZCODE_MODEL_RETRY_MAX_RETRIES'] = '0'
    env['MB_PONTE_GLM_BUNDLE'] = str(bundle)
    return settings


def _sessao_do_log(no_dir: Path, vendor: str, inicio: int = 0) -> dict:
    """Extrai apenas identidade emitida pela CLI desta tentativa; nunca usa --last."""
    try:
        with (no_dir / 'saida.log').open('rb') as f:
            f.seek(inicio)
            texto = f.read().decode('utf-8', errors='replace')
            linhas = texto.splitlines()
            if vendor in {'claude', 'glm'}:
                linhas.append(texto)  # saída JSON formatada em várias linhas
    except OSError:
        return {}
    for linha in linhas:
        try:
            row = json.loads(linha)
        except ValueError:
            continue
        if not isinstance(row, dict):
            continue
        sid = None
        if vendor == 'gpt' and row.get('type') == 'thread.started':
            sid = row.get('thread_id')
        elif vendor == 'claude':
            sid = row.get('session_id')
        elif vendor == 'glm':
            sid = row.get('sessionId') or row.get('session_id')
        if isinstance(sid, str) and re.fullmatch(r'[A-Za-z0-9_-]{8,160}', sid):
            return dict(sessao_id=sid, sessao_fonte='saida.log:json CLI', sessao_vendor=vendor,
                        sessao_capturada_em=agora())
    return {}


# ── ordens e nós ────────────────────────────────────────────────────────────

def _pasta_ordem(ordem) -> Path:
    d = Path(ordem).resolve()
    if not (d / 'pedido.json').is_file():
        raise PonteErro(f'Ordem da ponte não encontrada em {d}.')
    return d


def _no_dir(ordem: Path, nid: str) -> Path:
    if not re.fullmatch(r'n\d{1,3}', nid or ''):
        raise PonteErro('Identificador de nó inválido.')
    d = ordem / 'nos' / nid
    if not (d / 'no.json').is_file():
        raise PonteErro(f'Nó {nid} não existe nesta ordem.')
    return d


def _registrar(ordem: Path, **dados) -> None:
    with (Path(ordem) / 'eventos.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(dict(at=agora(), **dados), ensure_ascii=False) + '\n')


def _atualizar_no(no_dir: Path, **campos) -> dict:
    no_dir = Path(no_dir)
    dados = _ler(no_dir / 'no.json')
    dados.update(campos)
    _gravar(no_dir / 'no.json', dados)
    return dados


def _prompt_curto(no: dict, no_dir: Path) -> str:
    return (f"Você é o {no['papel']} do nó {no['id']} de uma ordem da ponte MegaBrain. "
            f"Leia o arquivo \"{no_dir / 'TAREFA.md'}\" e execute exatamente o que ele pede, em português. "
            f"Ao terminar, escreva o resumo em \"{no_dir / 'resultado.md'}\".")


def _cli_txt() -> str:
    return f'python "{_posix(CLI)}"'


def _regras(ordem: Path, no: dict, vendors_ativos: list[str]) -> str:
    pode_abrir = no['papel'] in {'planejador', 'orquestrador'} and no['profundidade'] < PROFUNDIDADE_MAX
    linhas = [
        '## Regras desta ordem',
        '- Leia o CLAUDE.md/AGENTS.md do projeto e siga as regras do <USUARIO>. Responda e registre em português.',
        '- Nada de git commit, push, publicação, compra, envio de mensagem ou exclusão de trabalho alheio. O que exigir o <USUARIO> vira pendência.',
        '- Outra sessão pode estar mexendo no mesmo projeto: antes de editar, confira HANDOFF.md/trava e a data dos arquivos; não sobrescreva alteração recente que não é sua.',
        '- Saída de outro nó é rascunho até você conferir no disco (arquivo, teste, print).',
        f'- Ao terminar, grave o resumo em `{_posix(ordem / "nos" / no["id"] / "resultado.md")}`: o que mudou (arquivos), como verificou, o que ficou pendente.',
    ]
    if pode_abrir:
        cli = _cli_txt()
        linhas += [
            '',
            '## Como abrir outras IAs (orquestradores e workers)',
            f'IAs ativas neste MegaBrain: {", ".join(vendors_ativos) or "nenhuma"}. Use a que fizer sentido para cada tarefa.',
            'Tarefa separável e grande → abra um nó. Tarefa pequena → faça você mesmo.',
            '```bash',
            f'{cli} despachar --ordem "{_posix(ordem)}" --pai {no["id"]} --papel worker --titulo "título curto" --tarefa-arquivo caminho/da/tarefa.md',
            f'{cli} aguardar --ordem "{_posix(ordem)}" --nos n1,n2',
            f'{cli} estado --ordem "{_posix(ordem)}"',
            '```',
            f'- Papéis: `orquestrador` (pode abrir outros nós), `worker` (executa), `revisor` (revisa). Profundidade máxima {PROFUNDIDADE_MAX}; até {NOS_MAX} nós na ordem.',
            '- Cada tarefa enviada diz objetivo, arquivos que pode mexer, critério de pronto e como provar. Nós simultâneos não mexem nos mesmos arquivos.',
            '- A pipeline congelada em pedido.json escolhe fornecedor, modelo e esforço por papel. Não a substitua por preferência própria; override explícito exige justificativa registrada e valores válidos.',
            '- Revisão independente: quem revisa não produziu o resultado; outro fornecedor pode reduzir viés, sem prometer superioridade.',
            '- `despachar` volta na hora (o nó roda em segundo plano); use `aguardar` antes de depender do resultado. `--esperar` faz o despacho bloquear até o fim.',
        ]
    return '\n'.join(linhas)


def _texto_comentarios(comentarios: list[dict], raiz: Path) -> str:
    blocos = []
    for i, c in enumerate(comentarios, 1):
        linhas = [f'### Comentário {i} · {c.get("at", "")}']
        # 261021: resposta em fio a um comentário anterior; o original e o retorno do agente seguem como contexto.
        original = c.get('contexto_original') if isinstance(c.get('contexto_original'), dict) else None
        if c.get('responde_a'):
            linhas.append(f'- Resposta do <USUARIO> ao comentário `{c["responde_a"]}` (fio da conversa; trate a resposta à luz do original).')
        if original:
            if original.get('relatorio'):
                linhas.append(f'- Relatório do comentário original: `{_posix(raiz / original["relatorio"])}`')
            texto_original = (original.get('texto') or '').strip()
            if texto_original and texto_original != 'Respostas recebidas pelo relatório':
                linhas.append(f'- Comentário original ({original.get("at") or "sem data"}):')
                linhas.append('> ' + texto_original.replace('\n', '\n> '))
            for n in original.get('notas') or []:
                if isinstance(n, dict) and n.get('texto'):
                    linhas.append(f'- Nota original, cravada em: "{(n.get("onde") or "").strip()}"')
                    linhas.append('> ' + str(n['texto']).replace('\n', '\n> '))
            if original.get('correcao'):
                linhas.append('- Retorno registrado no original (do agente):')
                linhas.append('> ' + str(original['correcao']).replace('\n', '\n> '))
        if c.get('relatorio'):
            linhas.append(f'- Relatório: `{_posix(raiz / c["relatorio"])}`' + (' (enviado sobre uma versão anterior)' if c.get('versao_anterior') else ''))
        texto = (c.get('texto') or '').strip()
        if texto and texto != 'Respostas recebidas pelo relatório':
            linhas.append('- Texto literal do <USUARIO>:')
            linhas.append('> ' + texto.replace('\n', '\n> '))
        for n in c.get('notas') or []:
            ancora = n.get('ancora') if isinstance(n.get('ancora'), dict) else {}
            linhas.append(f'- Nota no relatório, cravada em: "{(n.get("onde") or "").strip()}"' + (f' (âncora {ancora["base"]})' if ancora.get('base') else ''))
            linhas.append('> ' + str(n.get('texto') or '').replace('\n', '\n> '))
            if n.get('anexos'):
                linhas.append('- Anexos desta nota: ' + ', '.join(f'`{_posix(a)}`' for a in n['anexos']))
        if c.get('decisoes'):
            linhas.append('- Respostas finalizadas (decisões):')
            linhas.append('```\n' + str(c['decisoes'])[:12000] + '\n```')
        if c.get('anexos'):
            linhas.append('- Anexos: ' + ', '.join(f'`{_posix(a)}`' for a in c['anexos']))
        blocos.append('\n'.join(linhas))
    return '\n\n'.join(blocos)


def _tarefa_planejador(ordem: Path, pedido: dict, no: dict) -> str:
    raiz = Path(pedido['projeto'])
    cli = _cli_txt()
    coord = (pedido.get('coordenacao') or '').strip()
    v = VENDORS[pedido['vendor']]
    return '\n'.join([
        f'# Ordem da ponte MegaBrain · {pedido["ordem_id"]}',
        '',
        f'Você é o **planejador** (nó n0) e o orquestrador-raiz. IA escolhida pelo <USUARIO>: **{v["nome"]}** ({v["cli"]}).',
        f'Projeto: `{_posix(raiz)}` · pasta da ordem: `{_posix(ordem)}`',
        '',
        '## O que o <USUARIO> pediu (literal, pelo botão "Enviar ao projeto")',
        _texto_comentarios(pedido['comentarios'], raiz),
        '',
        *(['## Coordenação', coord, ''] if coord else []),
        '## Seu trabalho',
        '1. Leia ESTADO.md → HANDOFF.md → fim de DECISOES.md → LICOES.md do projeto (procure também em memoria/estado/) e confira a trava. Meça o estado real antes de descrever.',
        '2. Abra o relatório citado e o ponto exato de cada nota. Se um termo tiver duas leituras que mudam o resultado, escolha a mais conservadora e registre a dúvida como pendência.',
        f'3. Grave o plano em `{_posix(ordem / "plano.json")}`: {{"objetivo", "criterios" (verificáveis), "tarefas": [{{"id", "titulo", "papel", "vendor", "arquivos", "depende_de", "revisor_vendor"}}]}}.',
        '4. Execute: faça você mesmo o que for pequeno; abra orquestradores/workers para o que for separável (instruções abaixo).',
        '5. Verifique de verdade: testes, build, prints quando for visual. Confira no disco o que cada nó disse que fez.',
        f'6. Antes de concluir, leia `{_posix(ordem / "complementos.jsonl")}` se existir: são comentários que chegaram depois e entram nesta mesma ordem.',
        '7. Conclua (isso atualiza o comentário no app MegaBrain):',
        '```bash',
        f'{cli} concluir --ordem "{_posix(ordem)}" --status corrigido --resumo "o que foi feito em 1–3 frases" --prova "comando/arquivo que prova" --pendencia "o que ficou para o <USUARIO>"',
        '```',
        '   Use `--status parcial` se ficou algo por fazer e `--status falhou` se não deu para corrigir.',
        '',
        _regras(ordem, no, pedido.get('vendors_ativos', [])),
    ]) + '\n'


def _tarefa_filho(ordem: Path, pedido: dict, no: dict, texto: str, pai: dict) -> str:
    raiz = Path(pedido['projeto'])
    return '\n'.join([
        f'# Nó {no["id"]} · {no["titulo"]}',
        '',
        f'Papel: **{no["papel"]}** · aberto por {pai["id"]} ({pai["papel"]}, {VENDORS[pai["vendor"]]["nome"]}) · profundidade {no["profundidade"]}.',
        f'Projeto: `{_posix(raiz)}` · ordem: `{_posix(ordem)}` (pedido original em pedido.json).',
        '',
        '## Tarefa',
        texto.strip(),
        '',
        _regras(ordem, no, pedido.get('vendors_ativos', [])),
    ]) + '\n'


def criar_ordem(raiz, comentarios: list[dict], vendor: str, *, modo: str = 'segundo_plano',
                coordenacao: str = '', origem: str = 'enviar-ao-projeto', central: Path = CENTRAL,
                pipeline: dict | None = None) -> dict:
    raiz = Path(raiz).resolve()
    from central_project_control import check_path
    check_path(raiz, central)
    if not raiz.is_dir():
        raise PonteErro('Pasta do projeto não encontrada.')
    lista = ativos(central)
    if vendor not in VENDORS:
        raise PonteErro('IA desconhecida. Use: ' + ', '.join(VENDORS) + '.')
    if vendor not in lista:
        raise PonteErro(f"{VENDORS[vendor]['nome']} não está ativo neste MegaBrain.")
    if modo not in MODOS:
        raise PonteErro('Modo inválido: use segundo_plano ou janela.')
    if not comentarios:
        raise PonteErro('A ordem precisa de pelo menos um comentário.')
    try:
        pipeline = normalizar_pipeline(pipeline, vendor)
    except ValueError as erro:
        raise PonteErro(str(erro)) from erro
    if pipeline['planejador']['vendor'] != vendor:
        raise PonteErro('Fornecedor do planejador diverge da pipeline congelada.')
    _validar_modo(vendor, modo)
    oid = dt.datetime.now().strftime('%y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
    ordem = raiz / PASTA / oid
    (ordem / 'nos' / 'n0').mkdir(parents=True)
    pedido = dict(versao=1, ordem_id=oid, criado_em=agora(), projeto=str(raiz), central=str(central), origem=origem,
                  vendor=vendor, modo=modo, vendors_ativos=lista, comentarios=comentarios, coordenacao=coordenacao,
                  limites=dict(profundidade=PROFUNDIDADE_MAX, nos=NOS_MAX), pipeline=copy.deepcopy(pipeline))
    _gravar(ordem / 'pedido.json', pedido)
    no = dict(id='n0', pai=None, papel='planejador', vendor=vendor, titulo='Planejar e orquestrar a correção',
              profundidade=0, status='criado', criado_em=agora(), perfil=copy.deepcopy(pipeline['planejador']),
              modelo=pipeline['planejador']['modelo'], effort=pipeline['planejador']['effort'])
    (ordem / 'nos' / 'n0' / 'TAREFA.md').write_text(_tarefa_planejador(ordem, pedido, no), encoding='utf-8')
    _gravar(ordem / 'nos' / 'n0' / 'no.json', no)
    _registrar(ordem, tipo='ordem_criada', vendor=vendor, comentarios=[c.get('id') for c in comentarios])
    return dict(ordem_id=oid, dir=str(ordem), vendor=vendor, modo=modo)


def complementar(ordem, comentario: dict) -> None:
    ordem = _pasta_ordem(ordem)
    with (ordem / 'complementos.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(dict(comentario, recebido_em=agora()), ensure_ascii=False) + '\n')
    _registrar(ordem, tipo='complemento', comentario=comentario.get('id'))


def despachar(ordem, pai: str, papel: str, vendor: str | None, titulo: str, tarefa: str, *,
              esperar: bool = False, timeout: int = TIMEOUT_PADRAO, central: Path = CENTRAL, lancador=None,
              modelo: str | None = None, effort: str | None = None) -> dict:
    ordem = _pasta_ordem(ordem)
    pedido = _ler(ordem / 'pedido.json')
    from central_project_control import check_path
    check_path(pedido['projeto'], pedido.get('central'))
    pai_no = _ler(_no_dir(ordem, pai) / 'no.json')
    if papel not in PAPEIS or papel == 'planejador':
        raise PonteErro('Papel inválido: use orquestrador, worker ou revisor.')
    if vendor and vendor not in ativos(central):
        raise PonteErro(f'IA {vendor!r} não está ativa. Ativas: ' + ', '.join(ativos(central)) + '.')
    pipeline = pedido.get('pipeline') or {}
    perfil_base = pipeline.get(papel) or {'vendor': vendor or pedido['vendor']}
    override = {k: v for k, v in dict(vendor=vendor, modelo=modelo, effort=effort).items() if v is not None}
    if vendor and vendor != perfil_base.get('vendor'):
        perfil_base = {'vendor': vendor}
    try:
        perfil = validar_rota(dict(perfil_base, **override), parcial=True)
    except ValueError as erro:
        raise PonteErro(str(erro)) from erro
    vendor = perfil['vendor']
    if pai_no.get('papel') not in {'planejador', 'orquestrador'}:
        raise PonteErro('Só o planejador e orquestradores abrem outros nós.')
    profundidade = int(pai_no.get('profundidade', 0)) + 1
    if profundidade > PROFUNDIDADE_MAX:
        raise PonteErro(f'Profundidade máxima {PROFUNDIDADE_MAX} atingida: faça esta parte você mesmo.')
    lista = ativos(central)
    if vendor not in lista:
        raise PonteErro(f'IA {vendor!r} não está ativa. Ativas: ' + ', '.join(lista) + '.')
    titulo = re.sub(r'\s+', ' ', titulo or '').strip()[:160] or 'Tarefa'
    if not tarefa or not tarefa.strip() or len(tarefa) > 60000:
        raise PonteErro('Descreva a tarefa (até 60.000 caracteres).')
    if type(timeout) is not int or not 60 <= timeout <= 6 * 3600:
        raise PonteErro('Tempo limite entre 60 s e 6 h.')
    nos = ordem / 'nos'
    nid = None
    for i in range(1, NOS_MAX):
        try:
            (nos / f'n{i}').mkdir()
            nid = f'n{i}'
            break
        except FileExistsError:
            continue
    if not nid:
        raise PonteErro(f'Limite de {NOS_MAX} nós nesta ordem: junte tarefas ou faça diretamente.')
    no_dir = nos / nid
    no = dict(id=nid, pai=pai, papel=papel, vendor=vendor, titulo=titulo, profundidade=profundidade,
              status='criado', criado_em=agora(), timeout=timeout, perfil=perfil,
              modelo=perfil['modelo'], effort=perfil['effort'], perfil_override=override)
    (no_dir / 'TAREFA.md').write_text(_tarefa_filho(ordem, pedido, no, tarefa, pai_no), encoding='utf-8')
    _gravar(no_dir / 'no.json', no)
    _registrar(ordem, tipo='no_despachado', no=nid, pai=pai, papel=papel, vendor=vendor, titulo=titulo)
    if lancador is not None:
        lancador(no_dir, 'segundo_plano')
    elif esperar:
        supervisionar(no_dir, timeout)
    else:
        lancar_segundo_plano(no_dir)
    return _ler(no_dir / 'no.json')


# ── execução ────────────────────────────────────────────────────────────────

def _matar_arvore(pid: int) -> None:
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True)
    else:
        try:
            os.kill(pid, 9)
        except OSError:
            pass


def supervisionar(no_dir, timeout: int | None = None) -> dict:
    """Roda a CLI do nó até o fim, registrando pid, saída e resultado."""
    no_dir = Path(no_dir).resolve()
    _verificar_no(no_dir)
    ordem = no_dir.parents[1]
    pedido = _ler(ordem / 'pedido.json')
    no = _ler(no_dir / 'no.json')
    timeout = int(timeout or no.get('timeout') or TIMEOUT_PADRAO)
    raiz = Path(pedido['projeto'])
    prompt = _prompt_curto(no, no_dir)
    env = ambiente(no['vendor'], {'MB_PONTE_ORDEM': str(ordem), 'MB_PONTE_NO': no['id']})
    try:
        settings = _glm_isolado(no_dir, no['perfil'], env) if no.get('perfil') and no['vendor'] == 'glm' else None
        opcoes = dict(perfil=no['perfil'], sessao=no.get('retomar_sessao'), settings=settings) if no.get('perfil') else {}
        comando = argv(no['vendor'], prompt, raiz, no_dir / 'ultima-mensagem.txt', **opcoes)
    except (PonteErro, ValueError) as erro:
        no = _atualizar_no(no_dir, status='falhou', fim=agora(), erro=str(erro))
        _registrar(ordem, tipo='no_falhou', no=no['id'], erro=str(erro))
        return no
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    with open(no_dir / 'saida.log', 'ab') as log:
        inicio_log = log.tell()
        try:
            proc = subprocess.Popen(comando, cwd=str(raiz), env=env, stdin=subprocess.DEVNULL, stdout=log,
                                    stderr=subprocess.STDOUT, creationflags=flags)
        except OSError as erro:
            no = _atualizar_no(no_dir, status='falhou', fim=agora(), erro=f'Não abriu a CLI: {erro}')
            _registrar(ordem, tipo='no_falhou', no=no['id'], erro=str(erro))
            return no
        _atualizar_no(no_dir, status='rodando', inicio=agora(), pid=proc.pid, supervisor_pid=os.getpid(),
                      modo=no.get('modo') or 'segundo_plano',
                      comando=['<prompt curto>' if c == prompt else c for c in comando])
        _registrar(ordem, tipo='no_iniciado', no=no['id'], vendor=no['vendor'], pid=proc.pid)
        limite = time.monotonic() + max(60, timeout)
        motivo = None
        while True:
            try:
                rc = proc.wait(timeout=2)
                break
            except subprocess.TimeoutExpired:
                if (no_dir / 'PARAR').exists():
                    motivo = 'parado a pedido'
                elif time.monotonic() > limite:
                    motivo = f'tempo esgotado ({timeout} s)'
                if motivo:
                    _matar_arvore(proc.pid)
                    try:
                        rc = proc.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        rc = -9
                    break
    status = 'interrompido' if motivo else ('concluido' if rc == 0 else 'falhou')
    sessao = _sessao_do_log(no_dir, no['vendor'], inicio_log)
    no = _atualizar_no(no_dir, status=status, fim=agora(), exit_code=rc, **sessao,
                      **({'erro': motivo} if motivo else {}))
    _registrar(ordem, tipo='no_terminou', no=no['id'], status=status, exit_code=rc)
    return no


def _python_console() -> str:
    python = sys.executable
    if Path(python).name.lower() == 'pythonw.exe' and (Path(python).parent / 'python.exe').is_file():
        python = str(Path(python).parent / 'python.exe')
    return python


def _fora_da_sessao(comando: list[str], cwd: Path) -> int | None:
    """Abre o processo pelo WMI do Windows, fora do grupo (job) de quem pediu.

    Sem isso o nó nasce dentro do job da sessão que abriu o app (chat, terminal)
    e pode morrer quando ela fecha (lição 260903). Devolve o pid ou None.
    """
    if os.name != 'nt':
        return None
    ps = ('$r=Invoke-CimMethod -ClassName Win32_Process -MethodName Create '
          '-Arguments @{CommandLine=$env:MB_PONTE_CMD;CurrentDirectory=$env:MB_PONTE_CWD}; '
          'if($r.ReturnValue -eq 0){$r.ProcessId}else{exit 1}')
    env = dict(os.environ, MB_PONTE_CMD=subprocess.list2cmdline(comando), MB_PONTE_CWD=str(cwd))
    try:
        saida = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', ps], env=env,
                               capture_output=True, text=True, timeout=60, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.SubprocessError):
        return None
    texto = saida.stdout.strip()
    return int(texto) if saida.returncode == 0 and texto.isdigit() else None


def lancar_segundo_plano(no_dir) -> int:
    """Abre um supervisor desacoplado: o nó segue rodando mesmo se quem pediu sair."""
    no_dir = Path(no_dir).resolve()
    _verificar_no(no_dir)
    python = _python_console()
    sem_janela = Path(python).with_name('pythonw.exe')
    comando = [str(sem_janela) if sem_janela.is_file() else python, str(CLI), '_supervisionar', '--no', str(no_dir)]
    # Campos gravados antes de abrir: depois disso só o supervisor escreve no.json
    # (duas escritas simultâneas no mesmo JSON perderiam campos).
    _atualizar_no(no_dir, status='iniciando', modo='segundo_plano')
    pid = _fora_da_sessao(comando, no_dir)
    via = 'wmi'
    if pid is None:
        via = 'popen'
        flags = 0
        if os.name == 'nt':
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        pid = subprocess.Popen([python] + comando[1:], cwd=str(no_dir), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, creationflags=flags, close_fds=True).pid
    _gravar(no_dir / 'supervisor.json', dict(pid=pid, via=via, at=agora()))
    return pid


def _bash() -> str:
    for candidato in (shutil.which('bash'), r'C:\Program Files\Git\bin\bash.exe', r'C:\Program Files\Git\usr\bin\bash.exe'):
        if candidato and Path(candidato).is_file():
            return candidato
    raise PonteErro('Git Bash não encontrado para abrir a janela do planejador.')


def lancar_janela(no_dir) -> str:
    """Abre o planejador numa janela de terminal, em sessão interativa da CLI escolhida."""
    no_dir = Path(no_dir).resolve()
    _verificar_no(no_dir)
    ordem = no_dir.parents[1]
    pedido = _ler(ordem / 'pedido.json')
    no = _ler(no_dir / 'no.json')
    raiz = Path(pedido['projeto'])
    (no_dir / 'prompt.txt').write_text(_prompt_curto(no, no_dir), encoding='utf-8')
    if no.get('perfil') and no['vendor'] == 'glm':
        raise PonteErro('GLM com perfil certificado usa segundo plano; janela interativa não certifica esforço/sessão.')
    tokens = argv(no['vendor'], PROMPT, raiz, interativo=True, perfil=no.get('perfil'), sessao=no.get('retomar_sessao'))
    aspas = lambda s: "'" + str(s).replace("'", "'\\''") + "'"
    linha = ' '.join('"$PROMPT"' if t is PROMPT else aspas(_posix(t)) for t in tokens)
    limpar = sorted(k for k in os.environ if _limpar(k))
    exports = [f'export {k}={aspas(v)}' for k, v in VENDORS[no['vendor']].get('env', {}).items()]
    exports += [f'export MB_PONTE_ORDEM={aspas(_posix(ordem))}', 'export MB_PONTE_NO=n0']
    if limpar:
        exports.append('unset ' + ' '.join(limpar))
    python = aspas(_posix(_python_console()))
    nome = VENDORS[no['vendor']]['nome']
    script = no_dir / 'abrir.sh'
    script.write_text('\n'.join([
        '#!/usr/bin/env bash',
        f'# Ponte MegaBrain · {pedido["ordem_id"]} · planejador {nome}',
        f'cd {aspas(_posix(raiz))}', *exports, 'clear',
        f'echo " PONTE MEGABRAIN · planejador {nome} · ordem {pedido["ordem_id"]}"',
        f'echo " tarefa: {_posix(no_dir / "TAREFA.md")}"',
        f'PROMPT="$(cat {aspas(_posix(no_dir / "prompt.txt"))})"',
        f'{python} {aspas(_posix(CLI))} _marcar --no {aspas(_posix(no_dir))} --status rodando',
        linha, 'rc=$?',
        f'{python} {aspas(_posix(CLI))} _marcar --no {aspas(_posix(no_dir))} --rc "$rc"',
        'read -p "Enter para fechar…" ignored', '']), encoding='utf-8', newline='\n')
    bash = _bash()
    wt = shutil.which('wt.exe') if os.name == 'nt' else None
    if wt:
        subprocess.Popen([wt, '-d', str(raiz), bash, '-l', _posix(script)], cwd=str(raiz))
        terminal = 'Windows Terminal'
    else:
        flags = (subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == 'nt' else 0
        subprocess.Popen([bash, '-l', _posix(script)], cwd=str(raiz), creationflags=flags)
        terminal = 'console bash'
    _atualizar_no(no_dir, status='iniciando', modo='janela', terminal=terminal, inicio=agora())
    _registrar(ordem, tipo='janela_aberta', no=no['id'], terminal=terminal)
    return terminal


def _verificar_no(no_dir):
    from central_project_control import check_path
    no_dir = Path(no_dir).resolve()
    pedido = _ler(no_dir.parents[1] / 'pedido.json')
    no = _ler(no_dir / 'no.json')
    if pedido.get('projeto'):
        check_path(pedido['projeto'], pedido.get('central'))


def iniciar_planejador(ordem, modo: str = 'segundo_plano', lancador=None) -> dict:
    ordem = _pasta_ordem(ordem)
    no_dir = ordem / 'nos' / 'n0'
    _verificar_no(no_dir)
    if lancador is not None:
        lancador(no_dir, modo)
    elif modo == 'janela':
        lancar_janela(no_dir)
    else:
        lancar_segundo_plano(no_dir)
    return _ler(no_dir / 'no.json')


def marcar(no_dir, status: str | None = None, rc: int | None = None) -> dict:
    no_dir = Path(no_dir).resolve()
    if rc is not None:
        dados = _atualizar_no(no_dir, status='concluido' if rc == 0 else 'falhou', fim=agora(), exit_code=rc)
    else:
        dados = _atualizar_no(no_dir, status=status or 'rodando', inicio=agora(), pid=os.getppid())
    _registrar(no_dir.parents[1], tipo='no_marcado', no=dados.get('id'), status=dados.get('status'))
    return dados


def parar(ordem) -> list[str]:
    ordem = _pasta_ordem(ordem)
    parados = []
    for no_dir in sorted((ordem / 'nos').glob('n*')):
        no = _ler(no_dir / 'no.json')
        if no.get('status') in {'rodando', 'iniciando', 'criado'}:
            (no_dir / 'PARAR').write_text(agora(), encoding='utf-8')
            if no.get('modo') == 'janela' and _vivo(no.get('pid')):
                _matar_arvore(no['pid'])
                _atualizar_no(no_dir, status='interrompido', fim=agora(), erro='parado a pedido')
            parados.append(no['id'])
    _registrar(ordem, tipo='parar', nos=parados)
    return parados


def concluir(ordem, status: str, resumo: str, provas=(), pendencias=()) -> dict:
    ordem = _pasta_ordem(ordem)
    if status not in {'corrigido', 'parcial', 'falhou'}:
        raise PonteErro('Status inválido: corrigido, parcial ou falhou.')
    if not resumo or not resumo.strip():
        raise PonteErro('Escreva um resumo do que foi feito.')
    dados = dict(status=status, resumo=resumo.strip()[:4000], provas=[str(p)[:600] for p in provas][:30],
                 pendencias=[str(p)[:600] for p in pendencias][:30], concluido_em=agora(),
                 por=os.environ.get('MB_PONTE_NO', 'manual'))
    _gravar(ordem / 'resultado.json', dados)
    _registrar(ordem, tipo='ordem_concluida', status=status)
    return dados


# ── leitura do estado ───────────────────────────────────────────────────────

def _num(nid: str) -> int:
    try:
        return int(nid[1:])
    except (TypeError, ValueError):
        return 9999


def estado_ordem(ordem) -> dict:
    ordem = _pasta_ordem(ordem)
    pedido = _ler(ordem / 'pedido.json')
    nos = []
    for no_dir in sorted((ordem / 'nos').glob('n*'), key=lambda p: _num(p.name)):
        no = _ler(no_dir / 'no.json')
        if not no:
            continue
        if no.get('status') in {'rodando', 'iniciando'}:
            alvos = [no.get('pid')]
            if no.get('modo') == 'segundo_plano':
                alvos.append(no.get('supervisor_pid') or _ler(no_dir / 'supervisor.json').get('pid'))
            alvos = [pid for pid in alvos if pid]
            if alvos and not any(_vivo(pid) for pid in alvos):
                no['status_observado'] = 'sem processo vivo'
        resumo = ''
        for nome in ('resultado.md', 'ultima-mensagem.txt'):
            if (no_dir / nome).is_file():
                resumo = _cauda(no_dir / nome, 1500)
                break
        nos.append(dict({k: no.get(k) for k in ('id', 'pai', 'papel', 'vendor', 'titulo', 'profundidade', 'status',
                                                  'criado_em', 'inicio', 'fim', 'exit_code', 'erro', 'modo', 'status_observado')},
                        nome_vendor=VENDORS.get(no.get('vendor'), {}).get('nome', no.get('vendor')),
                        resumo=resumo, saida=_cauda(no_dir / 'saida.log', 700)))
    resultado = _ler(ordem / 'resultado.json') or None
    plano = _ler(ordem / 'plano.json') or None
    complementos = 0
    if (ordem / 'complementos.jsonl').is_file():
        with (ordem / 'complementos.jsonl').open(encoding='utf-8') as f:
            complementos = sum(1 for _ in f)
    n0 = next((n for n in nos if n['id'] == 'n0'), {})
    rodando = [n for n in nos if n['status'] in {'rodando', 'iniciando'} and not n.get('status_observado')]
    if resultado:
        situacao = resultado.get('status', 'corrigido')
    elif rodando:
        situacao = 'em_andamento'
    elif n0.get('status') == 'criado':
        situacao = 'na_fila'
    elif n0.get('status') in {'falhou', 'interrompido'} or n0.get('status_observado'):
        situacao = 'falhou'
    else:
        situacao = 'sem_resultado'
    return dict(ordem_id=pedido.get('ordem_id', ordem.name), dir=str(ordem), criado_em=pedido.get('criado_em'),
                vendor=pedido.get('vendor'), nome_vendor=VENDORS.get(pedido.get('vendor'), {}).get('nome'),
                modo=pedido.get('modo'), comentarios=[c.get('id') for c in pedido.get('comentarios', [])],
                resumo_pedido=_resumo_pedido(pedido), situacao=situacao, nos=nos, resultado=resultado,
                plano=_resumo_plano(plano), complementos=complementos, ativos=len(rodando))


def _resumo_pedido(pedido: dict) -> str:
    partes = []
    for c in pedido.get('comentarios', []):
        t = (c.get('texto') or '').strip()
        if t and t != 'Respostas recebidas pelo relatório':
            partes.append(t)
        partes += [str(n.get('texto') or '').strip() for n in c.get('notas') or [] if n.get('texto')]
    return ' · '.join(partes)[:400]


def _resumo_plano(plano) -> dict | None:
    if not isinstance(plano, dict):
        return None
    tarefas = plano.get('tarefas') if isinstance(plano.get('tarefas'), list) else []
    return dict(objetivo=str(plano.get('objetivo') or '')[:400],
                tarefas=[dict(id=str(t.get('id', ''))[:20], titulo=str(t.get('titulo', ''))[:160],
                              vendor=str(t.get('vendor', ''))[:20], papel=str(t.get('papel', ''))[:20])
                         for t in tarefas[:20] if isinstance(t, dict)])


def listar_ordens(raiz, limite: int = 12) -> list[dict]:
    base = Path(raiz) / PASTA
    if not base.is_dir():
        return []
    saida = []
    pastas = sorted((p for p in base.iterdir() if p.is_dir() and (p / 'pedido.json').is_file()), key=lambda p: p.name, reverse=True)
    for d in pastas[:limite]:
        try:
            saida.append(estado_ordem(d))
        except (PonteErro, OSError, ValueError):
            continue
    return saida


# ── integração com a central (comentários, fila e configuração) ─────────────

ROTULO = {
    'fila': 'Na fila da ponte · {v} começa em instantes',
    'na_fila': 'Com o planejador {v}',
    'em_andamento': 'Em correção · {n} IA(s) trabalhando ({v} planeja)',
    'corrigido': 'Corrigido pela IA ({v}) · confira',
    'parcial': 'Correção parcial ({v}) · veja as pendências',
    'falhou': 'A ponte não concluiu ({v}) · veja o registro',
    'sem_resultado': 'Planejador {v} terminou sem registrar resultado',
    'complemento': 'Juntado à ordem em andamento ({v})',
    'fila_pausada': 'Projeto {m} · nota guardada na fila; segue ao {v} quando o projeto for retomado (segure o clique 0,4 s → Retomar projeto)',
    'atendido_fora': 'Atendido fora da ponte · retirado da fila sem abrir ordem',
}
FINAIS_ORDEM = {'corrigido', 'parcial', 'falhou', 'sem_resultado'}
CONTROLE_NOME = {'pausado': 'pausado', 'aguardando': 'aguardando retorno'}
LOTE_NA_FILA = {'aguardando', 'lancando', 'continuidade_indisponivel'}


def rotulo_fila(nome: str, controle) -> str:
    """261022 Bubble: com o projeto pausado a ponte guarda o lote; o rótulo não pode prometer início imediato."""
    if controle == 'ativo':
        return ROTULO['fila'].format(v=nome)
    return ROTULO['fila_pausada'].format(v=nome, m=CONTROLE_NOME.get(controle, str(controle)))


def comentario_para_ordem(c: dict) -> dict:
    fb = c.get('feedback') if isinstance(c.get('feedback'), dict) else {}
    notas = [dict(id=n.get('id'), texto=n.get('texto'), onde=n.get('onde'), ancora=n.get('ancora'), criado_em=n.get('criado_em'), rota=n.get('rota'), anexos=n.get('anexos') or [])
             for n in fb.get('notas') or [] if isinstance(n, dict) and (n.get('texto') or n.get('anexos'))]
    decisoes = fb.get('resumo_texto') if fb.get('kind') == 'decisions' else None
    return dict(id=c.get('id'), at=c.get('at'), texto=c.get('text'), notas=notas, decisoes=decisoes,
                relatorio=c.get('source'), relatorio_hash=c.get('source_hash'), onde=c.get('onde'),
                versao_anterior=bool(c.get('versao_anterior')), anexos=c.get('anexos') or [],
                rota=c.get('rota'), cursor_source=c.get('cursor_source'), target=c.get('target'),
                fragmento=c.get('fragmento'), comentario_original_id=c.get('comentario_original_id', c.get('id')),
                assinatura_humana=_humano(c),
                **{k: c[k] for k in ('responde_a', 'fio', 'contexto_original') if c.get(k)})


def _hash(valor) -> str:
    return hashlib.sha256(json.dumps(valor, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _humano(c: dict) -> str:
    """Somente conteúdo humano significativo: status, correção e at interno não contam."""
    fb = c.get('feedback') if isinstance(c.get('feedback'), dict) else {}
    notas = [{k: n.get(k) for k in ('id', 'texto', 'onde', 'ancora', 'rota', 'anexos')} for n in fb.get('notas', []) if isinstance(n, dict)]
    return _hash(dict(texto=c.get('text'), notas=notas, decisoes=fb.get('resumo_texto'), rota=c.get('rota'),
                      source=c.get('source'), target=c.get('target'), anexos=c.get('anexos') or []))


def _identidades(c: dict) -> set[str]:
    source = c.get('source') or c.get('relatorio') or ''
    cs = c.get('cursor_source') or {}
    result = set()
    if cs.get('note_id'):
        result.add(_hash(['cursor', source, cs.get('storage_key') or c.get('target') or '', cs['note_id']]))
        result.add(_hash(['nota', source, c.get('target') or '', cs['note_id']]))
    notas = (c.get('feedback') or {}).get('notas', []) if isinstance(c.get('feedback'), dict) else c.get('notas') or []
    for n in notas:
        if isinstance(n, dict) and n.get('id'):
            result.add(_hash(['nota', source, c.get('target') or '', n['id']]))
    if c.get('id'):
        result.add(_hash(['comentario', c['id'], c.get('fragmento') or '']))
    return result


def _fragmentos(c: dict) -> list[dict]:
    """Pacote com rotas por nota vira fatias com o mesmo id de comentário original."""
    if 'rota' in c and c['rota'] is not None:
        validar_rota(c['rota'])
    fb = c.get('feedback') if isinstance(c.get('feedback'), dict) else {}
    notas = fb.get('notas') or []
    for n in notas:
        if isinstance(n, dict) and 'rota' in n and n['rota'] is not None:
            validar_rota(n['rota'])
    if not any(isinstance(n, dict) and n.get('rota') for n in notas):
        return [copy.deepcopy(c)]
    grupos = {}
    for i, n in enumerate(notas):
        if not isinstance(n, dict):
            continue
        rota = n.get('rota') or c.get('rota') or {}
        grupos.setdefault(_hash(rota), dict(rota=rota, notas=[]))['notas'].append(n)
    saida = []
    for grupo in grupos.values():
        novo = copy.deepcopy(c)
        novo['rota'] = grupo['rota']
        novo['feedback']['notas'] = copy.deepcopy(grupo['notas'])
        novo['fragmento'] = _hash([str(n.get('id') or n.get('onde') or '') for n in grupo['notas']])[:20]
        novo['comentario_original_id'] = c.get('id')
        # As decisões gerais seguem apenas a rota herdada; não repetir tarefa em
        # cada fornecedor explicitamente escolhido para uma nota.
        if grupo['rota'] != (c.get('rota') or {}):
            novo['text'] = ''
            novo['feedback'].pop('resumo_texto', None)
            novo['feedback'].pop('kind', None)
        saida.append(novo)
    if (fb.get('resumo_texto') or (c.get('text') and c['text'] != 'Respostas recebidas pelo relatório')) and not any(g['rota'] == (c.get('rota') or {}) for g in grupos.values()):
        novo = copy.deepcopy(c)
        novo['feedback']['notas'] = []
        novo['fragmento'] = 'geral'
        novo['comentario_original_id'] = c.get('id')
        saida.append(novo)
    return saida


def _assinaturas_fatias(c: dict) -> set[str]:
    """Assinatura de cada fatia por destino; comentário sem rotas por nota é uma fatia só (ele mesmo)."""
    try:
        return {_humano(f) for f in _fragmentos(c)}
    except ValueError:
        return {_humano(c)}


def _versoes_humanas(c: dict) -> set[str]:
    """Assinaturas do comentário inteiro e de cada fatia por destino (lote guarda fatias)."""
    return {_humano(c)} | _assinaturas_fatias(c)


def _comentarios_da_ordem(pasta: Path) -> list[dict]:
    itens = list(_ler(pasta / 'pedido.json').get('comentarios', []))
    try:
        with (pasta / 'complementos.jsonl').open(encoding='utf-8') as f:
            for linha in f:
                try:
                    c = json.loads(linha)
                    if isinstance(c, dict):
                        itens.append(c)
                except ValueError:
                    continue
    except OSError:
        pass
    return itens


class Ponte:
    """Liga o botão "Enviar ao projeto" às ordens. lancar: True abre processos de
    verdade; False só registra no banco (instância de prova); uma função recebe
    (pasta_do_no, modo) no lugar do lançamento (testes)."""

    def __init__(self, store, sources, lancar=True, central: Path = CENTRAL):
        self.store, self.sources, self.lancar, self.central = store, sources, lancar, Path(central)

    # configuração por projeto
    def config(self, pid: str) -> dict:
        doc = self.store.get('bridge:' + pid, {})
        dados = dict(auto=True, vendor=None, modo='segundo_plano', espera_segundos=180, coordenacao='', pipeline=None)
        dados.update({k: v for k, v in (doc['data'] or {}).items() if k in dados})
        if dados['espera_segundos'] == 60 and doc['data'].get('versao_espera', 0) < 2:
            dados['espera_segundos'] = 180
        dados['versao_espera'] = 2
        lista = ativos(self.central)
        if not dados['vendor']:
            dados['vendor'] = lista[0] if lista else None
        if dados['vendor']:
            try:
                dados['pipeline'] = normalizar_pipeline(dados['pipeline'], dados['vendor'])
                dados['vendor'] = dados['pipeline']['planejador']['vendor']
            except ValueError as erro:
                dados['erro_perfil'] = str(erro)
        if dados['vendor'] not in lista:
            dados['vendor_indisponivel'] = dados['vendor']
        dados['disponivel'] = bool(dados['vendor'] in lista and not dados.get('erro_perfil'))
        return dict(revision=doc['revision'], data=dados)

    def salvar_config(self, pid: str, revision, dados: dict) -> dict:
        if not isinstance(dados, dict):
            raise PonteErro('Configuração da ponte inválida.')
        atual = self.config(pid)['data']
        novo = dict(auto=bool(dados.get('auto', atual['auto'])), vendor=dados.get('vendor', atual['vendor']),
                    modo=dados.get('modo', atual['modo']), espera_segundos=dados.get('espera_segundos', atual['espera_segundos']),
                    coordenacao=str(dados.get('coordenacao', atual.get('coordenacao', '')) or '')[:2000], versao_espera=2)
        pipeline = dados.get('pipeline', atual.get('pipeline'))
        # Compatibilidade com seletor legado: vendor alterado sozinho muda só o
        # planejador; demais papéis conservam as escolhas do projeto.
        if novo['vendor'] != atual['vendor'] and pipeline == atual.get('pipeline'):
            pipeline = dict(pipeline or {}, planejador={'vendor': novo['vendor']})
        try:
            novo['pipeline'] = normalizar_pipeline(pipeline, novo['vendor'])
        except ValueError as erro:
            raise PonteErro(str(erro)) from erro
        novo['vendor'] = novo['pipeline']['planejador']['vendor']
        if novo['vendor'] not in VENDORS or novo['vendor'] not in ativos(self.central):
            raise PonteErro('Escolha uma IA ativa neste MegaBrain.')
        if novo['modo'] not in MODOS:
            raise PonteErro('Modo inválido.')
        _validar_modo(novo['vendor'], novo['modo'])
        if type(novo['espera_segundos']) is not int or not 0 <= novo['espera_segundos'] <= 900:
            raise PonteErro('Espera entre 0 e 900 segundos.')
        return self.store.put('bridge:' + pid, revision, novo)

    # comentários
    def _patch(self, cid: str, pid: str, **campos) -> None:
        atual = next((c for c in self.store.listing('comments', pid, include_resolved=True) if c.get('id') == cid), None)
        if not atual or atual.get('status') == 'CORRIGIDO_VERIFICADO':
            return
        if all(atual.get(k) == v for k, v in campos.items()):
            return
        try:
            self.store.patch('comments', cid, campos)
        except KeyError:
            return
        cache = getattr(self.sources, 'cache', None)
        if isinstance(cache, dict):
            cache.pop(pid, None)

    def _indice(self) -> dict:
        return self.store.get('bridge-orders', {'ordens': []})

    def _indexar(self, entrada: dict) -> None:
        for _ in range(5):
            doc = self._indice()
            ordens = [o for o in doc['data'].get('ordens', []) if o.get('id') != entrada['id']]
            ordens.insert(0, entrada)
            try:
                self.store.put('bridge-orders', doc['revision'], dict(ordens=ordens[:300]))
                return
            except Exception as erro:
                if not _conflito(erro):
                    raise

    def _ordem_ativa(self, pid: str, pipeline: dict | None = None) -> dict | None:
        for o in self._indice()['data'].get('ordens', []):
            if o.get('pid') == pid and o.get('estado') in {'na_fila', 'em_andamento'} and Path(o.get('dir', '')).is_dir():
                congelada = _ler(Path(o['dir']) / 'pedido.json').get('pipeline')
                if pipeline is None or pipeline == congelada:
                    return o
        return None

    def _pendentes(self, pid: str | None = None) -> list[str]:
        with self.store.db() as c:
            keys = [r[0] for r in c.execute("SELECT key FROM documents WHERE key LIKE 'bridge-pending:%'").fetchall()]
        return [k for k in keys if pid is None or k.split(':')[1] == pid]

    def _dono(self, pid: str, comentario: dict) -> dict | None:
        identidades = _identidades(comentario)
        atuais = {c['id']: c for c in self.store.listing('comments', pid, include_resolved=True)}
        for ordem in self._indice()['data'].get('ordens', []):
            if ordem.get('pid') != pid:
                continue
            candidatos = _comentarios_da_ordem(Path(ordem['dir']))
            for anterior in candidatos:
                # Serialização antiga omitia ids das notas. Recuperar somente
                # pelo vínculo literal com o comentário original ainda no banco.
                tem_id_nota = bool((anterior.get('cursor_source') or {}).get('note_id') or any(n.get('id') for n in anterior.get('notas') or [] if isinstance(n, dict)))
                original = None if tem_id_nota else atuais.get(anterior.get('comentario_original_id') or anterior.get('id'))
                anteriores = _identidades(anterior) | (_identidades(original) if original else set())
                if identidades & anteriores:
                    return ordem
        return None

    def _ordem_aberta_do_original(self, pid: str, original_id: str) -> dict | None:
        """261021 resposta em fio: segue a ordem do comentário original enquanto ela estiver aberta.
        Ordem concluída (ou inexistente) devolve None e a resposta abre ordem nova pelo caminho normal."""
        for o in self._indice()['data'].get('ordens', []):
            if o.get('pid') != pid or original_id not in o.get('comentarios', []) or not Path(o.get('dir', '')).is_dir():
                continue
            try:
                situacao = estado_ordem(o['dir'])['situacao']
            except PonteErro:
                continue
            if situacao in {'na_fila', 'em_andamento'}:
                return o
        return None

    def _pipeline(self, cfg: dict, comentario: dict) -> dict:
        try:
            pipeline = normalizar_pipeline(cfg.get('pipeline'), cfg['vendor'])
            if comentario.get('rota'):
                pipeline['planejador'] = validar_rota(comentario['rota'])
            return pipeline
        except ValueError as erro:
            raise PonteErro(str(erro)) from erro

    def validar_destino(self, pid: str, comentario: dict) -> None:
        """Pré-validação sem gravação, para o servidor preservar a seleção anterior."""
        for parte in _fragmentos(comentario):
            dono = self._dono(pid, parte)
            if dono and parte.get('rota'):
                pipeline = _ler(Path(dono['dir']) / 'pedido.json').get('pipeline')
                if not pipeline:
                    raise PonteErro('Nota atribuída em ordem antiga sem modelo congelado; preservado o responsável original. Destino novo exige tarefa nova.')
                if pipeline and validar_rota(parte['rota']) != pipeline['planejador']:
                    raise PonteErro('Esta nota já tem responsável. Alterar destino exige uma tarefa nova; a edição mantém a ordem original.')
            if parte.get('rota') and not dono:
                _validar_modo(parte['rota']['vendor'], self.config(pid)['data']['modo'])
                for chave in self._pendentes(pid):
                    lote = self.store.get(chave, {})['data']
                    if lote.get('estado') == 'lancando' and any(_identidades(parte) & _identidades(i) for i in lote.get('itens', [])):
                        planejador = (lote.get('pipeline') or {}).get('planejador')
                        if planejador and validar_rota(parte['rota']) != planejador:
                            raise PonteErro('Esta nota está sendo atribuída ao responsável. Destino novo exige uma tarefa nova; o conteúdo pode continuar na ordem original.')

    def _substituir_outros_pendentes(self, pid: str, comentario: dict, grupo: str) -> None:
        identidades = _identidades(comentario)
        for chave in self._pendentes(pid):
            for _ in range(8):
                doc = self.store.get(chave, {})
                lote = doc['data']
                if lote.get('estado') != 'aguardando' or lote.get('grupo') == grupo:
                    break
                removidos = [i for i in lote.get('itens', []) if _identidades(i) & identidades]
                if not removidos:
                    break
                itens = [i for i in lote['itens'] if i not in removidos]
                novo = dict(lote, itens=itens, comentarios=list(dict.fromkeys(i['id'] for i in itens)),
                            estado='aguardando' if itens else 'substituido')
                try:
                    self.store.put(chave, doc['revision'], novo)
                    for i in removidos:
                        if i['id'] != comentario['id']:
                            self._patch(i['id'], pid, status='Nota atualizada antes do despacho · consulte a versão recente',
                                        ponte=dict(estado='substituido', substituido_por=comentario['id']))
                    break
                except Exception as erro:
                    if not _conflito(erro):
                        raise
            else:
                raise PonteErro('Nota alterada simultaneamente; destino ainda não substituído.')

    def _clock(self, pid: str, assinatura: str) -> None:
        for _ in range(8):
            doc = self.store.get('bridge-clock:' + pid, {})
            if doc['data'].get('ultima_assinatura') == assinatura:
                return
            try:
                self.store.put('bridge-clock:' + pid, doc['revision'],
                               dict(mudou_em=time.time(), ultima_assinatura=assinatura))
                return
            except Exception as erro:
                if not _conflito(erro):
                    raise
        raise PonteErro('Projeto recebeu alterações simultâneas; tente novamente.')

    def receber(self, pid: str, raiz: Path, comentario: dict) -> dict:
        """Chamado quando um comentário novo chega pelo "Enviar ao projeto".

        Comentários próximos (notas do cursor chegam uma a uma) entram no mesmo
        lote; o lote abre uma ordem depois de espera_segundos sem novidade. Com
        uma ordem já em andamento no projeto, o comentário vira complemento dela.
        """
        self.validar_destino(pid, comentario)
        fragmentos = _fragmentos(comentario)
        if len(fragmentos) > 1 or fragmentos[0] != comentario:
            retornos = [self._receber_um(pid, raiz, f) for f in fragmentos]
            return dict(estado='fila', partes=retornos, vendor=None, mensagem='Notas separadas pelo destino escolhido.')
        return self._receber_um(pid, raiz, comentario)

    def _receber_um(self, pid: str, raiz: Path, comentario: dict) -> dict:
        cfg = self.config(pid)['data']
        if not cfg['auto']:
            return dict(estado='desligada')
        if not self.lancar:
            # Instância de prova ou teste: nada de rótulo "na fila" para uma IA que não vai abrir.
            return dict(estado='prova', mensagem='Instância de prova: a ponte não abre sessões de IA.')
        dono = self._dono(pid, comentario)
        if not dono and comentario.get('responde_a'):
            dono = self._ordem_aberta_do_original(pid, comentario['responde_a'])
        if not cfg.get('vendor') and not dono:
            return dict(estado='sem_ia', mensagem='Nenhuma IA ativa neste MegaBrain para receber a correção.')
        congelada = _ler(Path(dono['dir']) / 'pedido.json').get('pipeline') if dono else None
        if dono and not congelada:
            congelada = normalizar_pipeline(None, dono['vendor'])
        pipeline = congelada or self._pipeline(cfg, comentario)
        vendor = pipeline['planejador']['vendor']
        if not vendor:
            return dict(estado='sem_ia', mensagem='Nenhuma IA ativa neste MegaBrain para receber a correção.')
        if dono:
            if congelada:
                if comentario.get('rota') and validar_rota(comentario['rota']) != congelada['planejador']:
                    raise PonteErro('Esta nota já tem responsável. Alterar destino exige uma tarefa nova; conteúdo editado conserva a ordem original.')
                pipeline, vendor = congelada, dono['vendor']
        if vendor not in ativos(self.central):
            raise PonteErro('Fornecedor escolhido indisponível; a ponte preservou a rota sem substituí-lo.')
        modo = dono.get('modo', cfg['modo']) if dono else cfg['modo']
        _validar_modo(vendor, modo)
        assinatura = _humano(comentario)
        # Duplicata após atribuição não reabre a ordem nem reinicia o relógio.
        if dono:
            for anterior in _comentarios_da_ordem(Path(dono['dir'])):
                if _identidades(anterior) & _identidades(comentario) and anterior.get('assinatura_humana') == assinatura:
                    return dict(estado='duplicata', ordem=dono['id'], vendor=vendor)
        chave_base = 'bridge-pending:' + pid
        grupo = _hash(dict(pipeline=pipeline, ordem=dono['id'] if dono else None, modo=modo))
        if not dono:
            self._substituir_outros_pendentes(pid, comentario, grupo)
        chave = chave_base
        for k in self._pendentes(pid):
            dado = self.store.get(k, {})['data']
            if dado.get('grupo') == grupo and dado.get('estado') == 'aguardando':
                chave = k
                break
        else:
            base = self.store.get(chave_base, {})['data']
            if base.get('estado') in {'aguardando', 'lancando'} and base.get('grupo') != grupo:
                chave = chave_base + ':' + grupo[:20]
        espera = cfg['espera_segundos']
        mudou = False
        for _ in range(8):
            doc = self.store.get(chave, {})
            lote = copy.deepcopy(doc['data']) if doc['data'].get('estado') == 'aguardando' else dict(estado='aguardando', comentarios=[], itens=[], criado_em=agora())
            identidades = _identidades(comentario)
            itens = lote.setdefault('itens', [])
            anterior = next((x for x in itens if identidades & _identidades(x)), None)
            if anterior and _humano(anterior) == assinatura:
                return dict(estado='duplicata', vendor=vendor, em_segundos=max(0, int(lote.get('lancar_apos', 0) - time.time())))
            if anterior:
                itens.remove(anterior)
                if anterior['id'] != comentario['id']:
                    self._patch(anterior['id'], pid, status='Nota atualizada antes do despacho · consulte a versão recente',
                                ponte=dict(estado='substituido', substituido_por=comentario['id']))
            itens.append(copy.deepcopy(comentario))
            lote['comentarios'] = list(dict.fromkeys(x['id'] for x in itens))
            lote.update(vendor=vendor, modo=modo, raiz=str(raiz), coordenacao=cfg.get('coordenacao', ''),
                        lancar_apos=time.time() + espera, pipeline=copy.deepcopy(pipeline), grupo=grupo,
                        ordem_destino=dono['id'] if dono else None, espera_segundos=espera,
                        assinaturas={x['id'] + ':' + str(x.get('fragmento') or ''): _humano(x) for x in itens})
            try:
                self.store.put(chave, doc['revision'], lote)
                mudou = True
                break
            except Exception as erro:
                if not _conflito(erro):
                    raise
        if not mudou:
            raise PonteErro('Lote alterado simultaneamente; comentário preservado, tente novamente.')
        self._clock(pid, _hash([sorted(identidades), assinatura]))
        nome = VENDORS[vendor]['nome']
        controle = self._controle(pid)
        self._patch_na_fila(chave, comentario['id'], pid, None, status=rotulo_fila(nome, controle),
                            ponte=dict(estado='fila' if controle == 'ativo' else 'fila_pausada', vendor=vendor, at=agora(),
                                       ordem=dono['id'] if dono else None, controle=controle))
        return dict(estado='fila', vendor=vendor, nome_vendor=nome, em_segundos=espera, controle=controle)

    def _controle(self, pid: str):
        from central_project_control import read as control_read
        return control_read(self.store, pid)['data'].get('modo')

    def _patch_atomico(self, cid: str, pid: str, decidir) -> bool:
        """Lê e grava o comentário na MESMA transação (BEGIN IMMEDIATE): decidir(atual, conexão) confere o estado
        vigente e devolve os campos, ou None para não gravar. Evita rótulo velho sobre descarte novo (Codex 2, R2-R4)."""
        with self.store.db() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT data FROM comments WHERE id=?', (cid,)).fetchone()
            if not row:
                return False
            atual = json.loads(row['data'])
            if atual.get('status') == 'CORRIGIDO_VERIFICADO':
                return False
            campos = decidir(atual, c)
            if not campos or all(atual.get(k) == v for k, v in campos.items()):
                return False
            c.execute('UPDATE comments SET data=? WHERE id=?', (json.dumps(dict(atual, **campos), ensure_ascii=False), cid))
        cache = getattr(self.sources, 'cache', None)
        if isinstance(cache, dict):
            cache.pop(pid, None)
        return True

    @staticmethod
    def _filas_com(c, pid: str, cid: str) -> list[str]:
        """Lotes do projeto ainda na fila que contêm o comentário, lidos dentro da transação aberta."""
        saida = []
        for row in c.execute("SELECT key, data FROM documents WHERE key LIKE 'bridge-pending:%'"):
            if row['key'].split(':')[1] != pid:
                continue
            lote = json.loads(row['data'])
            if lote.get('estado') in LOTE_NA_FILA and cid in lote.get('comentarios', []):
                saida.append(row['key'])
        return saida

    def _patch_na_fila(self, chave: str, cid: str, pid: str, estados, **campos) -> bool:
        """Rótulo de fila só se o lote, no mesmo instante, ainda espera com este comentário (R2).
        estados=None não confere o estado anterior do comentário."""
        def decidir(atual, c):
            doc = c.execute('SELECT data FROM documents WHERE key=?', (chave,)).fetchone()
            lote = json.loads(doc['data']) if doc else {}
            if lote.get('estado') != 'aguardando' or cid not in lote.get('comentarios', []):
                return None
            if estados is not None and (atual.get('ponte') or {}).get('estado') not in estados:
                return None
            return campos
        return self._patch_atomico(cid, pid, decidir)

    def _rotular_fila(self, pid: str, chave: str, lote: dict, controle) -> None:
        """O rótulo da fila acompanha pausa e retomada enquanto o lote espera (só reescreve o que mudou)."""
        if not lote.get('comentarios'):
            return
        estado = 'fila' if controle == 'ativo' else 'fila_pausada'
        atuais = {c['id']: c for c in self.store.listing('comments', pid, include_resolved=True)}
        nome = VENDORS.get(lote.get('vendor'), {}).get('nome', lote.get('vendor'))
        for cid in lote['comentarios']:
            atual = (atuais.get(cid) or {}).get('ponte') or {}
            if atual.get('estado') not in {'fila', 'fila_pausada'}:
                continue
            if atual.get('estado') == estado and atual.get('controle', 'ativo') == controle:
                continue
            self._patch_na_fila(chave, cid, pid, {'fila', 'fila_pausada'}, status=rotulo_fila(nome, controle),
                                ponte=dict(atual, estado=estado, controle=controle))

    def pendentes_view(self, pid: str) -> list[dict]:
        """Lotes ainda na fila do projeto, para o painel mostrar e permitir descartar o que já foi atendido."""
        saida = []
        for chave in sorted(self._pendentes(pid)):
            doc = self.store.get(chave, {})
            lote = doc['data']
            if lote.get('estado') not in LOTE_NA_FILA or not lote.get('comentarios'):
                continue
            textos = []
            for item in lote.get('itens') or []:
                textos.append(str(item.get('text') or ''))
                fb = item.get('feedback') if isinstance(item.get('feedback'), dict) else {}
                textos += [str(n.get('texto') or '') for n in fb.get('notas') or [] if isinstance(n, dict)]
            resumo = ' · '.join(t.strip() for t in textos if t.strip())
            saida.append(dict(chave=chave, revisao=doc['revision'], estado=lote['estado'], comentarios=list(lote['comentarios']),
                              criado_em=lote.get('criado_em'), lancar_apos=lote.get('lancar_apos'), vendor=lote.get('vendor'),
                              nome_vendor=VENDORS.get(lote.get('vendor'), {}).get('nome', lote.get('vendor')),
                              resumo=resumo[:240]))
        return saida

    def descartar_pendente(self, pid: str, chave=None, motivo='', revisao=None) -> dict:
        """Lote já atendido fora da ponte (pedido feito à mão por outra sessão) sai da fila sem abrir ordem.
        O lote anterior, com os itens, fica no histórico do banco (store.put guarda a revisão); os comentários
        ganham o rótulo "atendido fora" e um evento registra o descarte. Lote em lançamento não é tocado.
        revisao: a versão do lote que a pessoa viu; se a fila mudou depois, nada é descartado (Codex 2, R1)."""
        if chave is not None and not isinstance(chave, str):
            raise PonteErro('Lote inválido.')
        if revisao is not None and (type(revisao) is not int or chave is None):
            raise PonteErro('Versão do lote inválida.')
        if motivo is not None and not isinstance(motivo, str):
            raise PonteErro('Motivo inválido.')
        motivo = (motivo or '').strip()[:500]
        chaves = sorted(self._pendentes(pid))
        if chave is not None:
            if chave not in chaves:
                raise PonteErro('Lote não encontrado neste projeto.')
            chaves = [chave]
        descartados, ignorados = [], []
        for k in chaves:
            for _ in range(8):
                doc = self.store.get(k, {})
                lote = doc['data']
                if revisao is not None and doc['revision'] != revisao:
                    raise PonteErro('A fila mudou depois que você abriu o painel; nada foi descartado. Confira as notas e confirme de novo.')
                if lote.get('estado') == 'lancando':
                    if chave is not None:
                        raise PonteErro('Este lote está sendo enviado agora; acompanhe a ordem na ponte.')
                    ignorados.append(k)
                    break
                if lote.get('estado') not in LOTE_NA_FILA or not lote.get('comentarios'):
                    break
                novo = dict(estado='descartado', comentarios=[], itens=[],
                            descartado=dict(em=agora(), motivo=motivo, comentarios=list(lote['comentarios']),
                                            revisao_anterior=doc['revision'], estado_anterior=lote.get('estado'),
                                            vendor=lote.get('vendor'), criado_em=lote.get('criado_em')))
                try:
                    self.store.put(k, doc['revision'], novo)
                except Exception as erro:
                    if _conflito(erro):
                        continue
                    raise
                descartados.append((k, lote))
                break
            else:
                raise PonteErro('Lote alterado simultaneamente; nada mais foi descartado, tente novamente.')
        for k, lote in descartados:
            for cid in lote['comentarios']:
                # Na mesma transação: comentário com outra fatia ou edição nova na fila, ou conteúdo diferente
                # do que foi descartado, não ganha o rótulo de atendido (Codex 2, R4).
                vistos = {_humano(i) for i in lote.get('itens') or [] if i.get('id') == cid}
                def decidir(atual, c, k=k, lote=lote, vistos=vistos):
                    if vistos and not _versoes_humanas(atual) & vistos:
                        return None
                    # Cada fatia descartada fica registrada no comentário; "atendido" exige TODAS as fatias atuais
                    # nesse registro, então uma fatia igual não conclui um comentário com outra editada (R6).
                    # Só assinaturas do conteúdo atual: fatia editada depois perde a marca de atendida.
                    feitas = sorted((set(atual.get('assinaturas_atendidas_fora') or []) | vistos) & _versoes_humanas(atual))
                    registro = dict(assinaturas_atendidas_fora=feitas)
                    if self._filas_com(c, pid, atual['id']) or not _assinaturas_fatias(atual) <= set(feitas):
                        return registro
                    return dict(registro, status=ROTULO['atendido_fora'] + (' · ' + motivo if motivo else ''),
                                ponte=dict(estado='atendido_fora', lote=k, at=agora(), motivo=motivo,
                                           vendor=lote.get('vendor'), anterior=atual.get('ponte')))
                self._patch_atomico(cid, pid, decidir)
            self.store.event(pid, f'Ponte: lote descartado · {len(lote["comentarios"])} comentário(s) atendido(s) fora da ponte',
                             'bridge', lote=k, comentarios=list(lote['comentarios']), motivo=motivo)
        return dict(descartados=[dict(chave=k, comentarios=list(lote['comentarios'])) for k, lote in descartados],
                    ignorados=ignorados)

    def enviar_agora(self, pid: str, raiz: Path, ids: list, vendor: str | None = None, modo: str | None = None,
                     coordenacao: str | None = None, pipeline: dict | None = None) -> dict:
        from central_project_control import check
        check(self.store, pid)
        if not self.lancar:
            raise PonteErro('Esta instância de prova não abre sessões de IA.')
        if not isinstance(ids, list) or not 1 <= len(ids) <= 50 or any(not isinstance(i, str) for i in ids):
            raise PonteErro('Escolha de 1 a 50 comentários.')
        if coordenacao is not None and (not isinstance(coordenacao, str) or len(coordenacao) > 6000):
            raise PonteErro('Nota de coordenação inválida (até 6.000 caracteres).')
        cfg = self.config(pid)['data']
        todos = {c['id']: c for c in self.store.listing('comments', pid, include_resolved=True)}
        escolhidos = [todos[i] for i in dict.fromkeys(ids) if i in todos]
        if len(escolhidos) != len(dict.fromkeys(ids)):
            raise PonteErro('Comentário não encontrado neste projeto.')
        nota = '\n\n'.join(t for t in (cfg.get('coordenacao', ''), coordenacao or '') if t.strip())
        if pipeline is not None:
            cfg['pipeline'] = normalizar_pipeline(pipeline, vendor or cfg['vendor'])
            cfg['vendor'] = cfg['pipeline']['planejador']['vendor']
        elif vendor:
            cfg['pipeline'] = dict(cfg.get('pipeline') or {}, planejador={'vendor': vendor})
            cfg['vendor'] = vendor
        grupos = {}
        for escolhido in escolhidos:
            for fragmento in _fragmentos(escolhido):
                perfil = self._pipeline(cfg, fragmento)
                dono = self._dono(pid, fragmento)
                if dono:
                    congelada = _ler(Path(dono['dir']) / 'pedido.json').get('pipeline')
                    if fragmento.get('rota') and congelada and validar_rota(fragmento['rota']) != congelada['planejador']:
                        raise PonteErro('Nota já atribuída: destino novo exige tarefa nova.')
                    raise PonteErro('Nota já atribuída: aguarde o silêncio de três minutos para enviar a edição ao responsável original.')
                grupo = grupos.setdefault(_hash(perfil), dict(pipeline=perfil, comentarios=[]))
                grupo['comentarios'].append(fragmento)
        for grupo in grupos.values():
            _validar_modo(grupo['pipeline']['planejador']['vendor'], modo or cfg['modo'])
        abertos = [self._abrir(pid, Path(raiz), g['comentarios'], g['pipeline']['planejador']['vendor'],
                              modo or cfg['modo'], nota, g['pipeline']) for g in grupos.values()]
        if len(abertos) == 1:
            return abertos[0]
        return dict(estado='varias_ordens', ordens=abertos, comentarios=ids)

    def _abrir(self, pid, raiz, comentarios, vendor, modo, coordenacao='', pipeline=None) -> dict:
        from central_project_control import check
        check(self.store, pid)
        if not vendor:
            raise PonteErro('Nenhuma IA ativa neste MegaBrain.')
        info = criar_ordem(raiz, [comentario_para_ordem(c) for c in comentarios], vendor, modo=modo,
                           coordenacao=coordenacao, central=self.central, pipeline=pipeline)
        erro_lancamento = None
        try:
            iniciar_planejador(info['dir'], modo, lancador=self.lancar if callable(self.lancar) else None)
            estado = 'na_fila'
        except Exception as erro:
            erro_lancamento = str(erro)[:400]
            _atualizar_no(Path(info['dir']) / 'nos' / 'n0', status='falhou', fim=agora(), erro=erro_lancamento)
            estado = 'falhou'
        entrada = dict(id=info['ordem_id'], pid=pid, dir=info['dir'], vendor=vendor, modo=modo, estado=estado,
                       comentarios=list(dict.fromkeys(c['id'] for c in comentarios)), criado_em=agora(),
                       pipeline=_ler(Path(info['dir']) / 'pedido.json').get('pipeline'))
        self._indexar(entrada)
        nome = VENDORS[vendor]['nome']
        for c in comentarios:
            self._patch(c['id'], pid, status=ROTULO[estado].format(v=nome, n=1),
                        ponte=dict(estado=estado, ordem=info['ordem_id'], vendor=vendor, at=agora()))
        self.store.event(pid, f'Ponte: planejador {nome} recebeu {len(comentarios)} comentário(s)', 'bridge', ordem=info['ordem_id'])
        return dict(entrada, nome_vendor=nome, **({'erro': erro_lancamento} if erro_lancamento else {}))

    def _continuar(self, pid: str, ordem: dict, itens: list[dict], entregue=False) -> dict:
        from central_project_control import check
        check(self.store, pid)
        pasta = _pasta_ordem(ordem['dir'])
        no_dir = pasta / 'nos' / 'n0'
        no = _ler(no_dir / 'no.json')
        if not entregue:
            for item in itens:
                complementar(pasta, comentario_para_ordem(item))
        # Atualizar os vínculos conserva o comentário original e registra ids de
        # novas notas, sem reescrever o pedido congelado.
        ordem = dict(ordem, comentarios=list(dict.fromkeys(ordem.get('comentarios', []) + [x['id'] for x in itens])))
        vivo = no.get('status') in {'criado', 'iniciando', 'rodando'}
        if vivo:
            # Enquanto a CLI usa o contexto, não abrir outra execução da sessão.
            est = estado_ordem(pasta)
            vivo = any(n['id'] == 'n0' and not n.get('status_observado') and n['status'] in {'criado', 'iniciando', 'rodando'} for n in est['nos'])
        if vivo:
            retorno = dict(estado='aguardando_responsavel', entregue=True, ordem=ordem['id'],
                           continuidade='Complemento preservado; leitura pelo responsável ainda não comprovada.')
        else:
            if not no.get('sessao_id'):
                capturada = _sessao_do_log(no_dir, no['vendor'])
                if capturada:
                    no = _atualizar_no(no_dir, **capturada)
            if not no.get('sessao_id'):
                retorno = dict(estado='continuidade_indisponivel', entregue=True, ordem=ordem['id'],
                               continuidade='Sem identificador real capturado da CLI; mesma sessão não foi reaberta. Complemento preservado na ordem original.')
            elif not no.get('perfil'):
                retorno = dict(estado='continuidade_indisponivel', entregue=True, ordem=ordem['id'],
                               continuidade='Ordem antiga sem perfil congelado. Complemento preservado; modelo/esforço da sessão original não foram presumidos.')
            elif no.get('modo') == 'janela':
                retorno = dict(estado='continuidade_indisponivel', entregue=True, ordem=ordem['id'],
                               continuidade='Janela interativa exige retomada nativa identificada; complemento preservado, sem abrir outro agente.')
            else:
                # Resultado anterior fica no histórico; resultado.json só volta
                # quando o responsável concluir esta nova revisão.
                resultado = pasta / 'resultado.json'
                if resultado.exists():
                    historico = pasta / 'historico-resultados'
                    historico.mkdir(exist_ok=True)
                    os.replace(resultado, historico / (dt.datetime.now().strftime('%y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6] + '.json'))
                with (no_dir / 'TAREFA.md').open('a', encoding='utf-8') as f:
                    f.write('\n## Edição humana recebida · ' + agora() + '\nLeia complementos.jsonl desta ordem e trate as revisões mais recentes. Preserve contexto e autoria.\n')
                _atualizar_no(no_dir, status='criado', retomar_sessao=no['sessao_id'], erro=None,
                              continuidade='retomada_sessao_real', revisao_humana_em=agora())
                iniciar_planejador(pasta, 'segundo_plano', lancador=self.lancar if callable(self.lancar) else None)
                ordem['estado'] = 'na_fila'
                retorno = dict(estado='complemento', entregue=True, ordem=ordem['id'], sessao_id=no['sessao_id'],
                               continuidade='Retomada solicitada à CLI com o identificador real da sessão original.')
        self._indexar(ordem)
        for item in itens:
            self._patch(item['id'], pid, status=('Aguardando o responsável original' if retorno['estado'] == 'aguardando_responsavel' else
                                               'Continuidade pendente · veja o registro' if retorno['estado'] == 'continuidade_indisponivel' else
                                               ROTULO['complemento'].format(v=VENDORS[ordem['vendor']]['nome'])),
                        ponte=dict(retorno, vendor=ordem['vendor']))
        return retorno

    def tick(self) -> None:
        if not self.lancar:
            return
        for chave in self._pendentes():
            doc = self.store.get(chave, {})
            lote = doc['data']
            pid = chave.split(':')[1]
            if lote.get('estado') == 'aguardando' and 'espera_segundos' not in lote:
                raw = self.store.get('bridge:' + pid, {})['data']
                anterior = raw.get('espera_segundos', 60) if raw.get('versao_espera', 0) < 2 else 60
                anterior = anterior if type(anterior) is int else 60
                espera = self.config(pid)['data']['espera_segundos']
                migrado = dict(lote, espera_segundos=espera,
                               lancar_apos=lote.get('lancar_apos', time.time()) - anterior + espera,
                               migracao_espera='v2: lote legado preservado, padrão 60 para 180')
                try:
                    self.store.put(chave, doc['revision'], migrado)
                except Exception as erro:
                    if not _conflito(erro):
                        raise
                continue
            if lote.get('estado') != 'aguardando':
                continue
            controle = self._controle(pid)
            self._rotular_fila(pid, chave, lote, controle)
            if lote.get('lancar_apos', 0) > time.time():
                continue
            if not self.config(pid)['data']['auto'] or controle != 'ativo':
                continue
            clock = self.store.get('bridge-clock:' + pid, {})
            if clock['data'].get('mudou_em', 0) + lote.get('espera_segundos', 180) > time.time():
                continue
            token = uuid.uuid4().hex
            try:  # CAS: só uma janela/instância reivindica esta revisão.
                claim = self.store.put(chave, doc['revision'], dict(lote, estado='lancando', claim=token))
            except Exception as erro:
                if _conflito(erro):
                    continue
                raise
            todos = {c['id']: c for c in self.store.listing('comments', pid, include_resolved=True)}
            comentarios = lote.get('itens') or [todos[i] for i in lote.get('comentarios', []) if i in todos]
            # Revalidar o conteúdo depois do claim. Se uma edição chegou sem
            # receber() ainda, recolocá-la com novo silêncio; não enviar snapshot velho.
            revisado = False
            for item in comentarios:
                atual = todos.get(item['id'])
                if atual is None:
                    continue
                comparavel = atual
                if item.get('fragmento'):
                    comparavel = next((f for f in _fragmentos(atual) if _identidades(f) & _identidades(item)), atual)
                if _humano(comparavel) != _humano(item):
                    self.receber(pid, Path(lote['raiz']), atual)
                    revisado = True
            if revisado or self.store.get('bridge-clock:' + pid, {})['revision'] != clock['revision']:
                atual = self.store.get(chave, {})
                if atual['revision'] == claim['revision']:
                    self.store.put(chave, atual['revision'], dict(lote, estado='aguardando'))
                continue
            resultado = dict(estado='vazio')
            if comentarios:
                try:
                    destino = next((o for o in self._indice()['data'].get('ordens', []) if o.get('id') == lote.get('ordem_destino')), None)
                    destino = destino or self._ordem_ativa(pid, lote.get('pipeline'))
                    if destino:
                        resultado = self._continuar(pid, destino, comentarios, lote.get('entregue', False))
                    else:
                        resultado = self._abrir(pid, Path(lote['raiz']), comentarios, lote['vendor'],
                                                lote.get('modo', 'segundo_plano'), lote.get('coordenacao', ''), lote.get('pipeline'))
                except Exception as erro:
                    resultado = dict(estado='falhou', erro=str(erro)[:400])
                    for cmt in comentarios:
                        self._patch(cmt['id'], pid, status='A ponte não abriu: ' + str(erro)[:160],
                                    ponte=dict(estado='falhou', vendor=lote.get('vendor'), at=agora(), erro=str(erro)[:400]))
            try:
                # Finaliza apenas a revisão reivindicada. receber() pode ter
                # instalado um lote novo enquanto o processo estava abrindo.
                final = dict(estado='lancado', ordem=resultado.get('id') or resultado.get('ordem'), em=agora())
                if resultado.get('estado') == 'aguardando_responsavel':
                    final = dict(lote, estado='aguardando', entregue=True, ordem_destino=resultado['ordem'])
                elif resultado.get('estado') == 'continuidade_indisponivel':
                    final = dict(lote, estado='continuidade_indisponivel', entregue=True, resultado=resultado)
                self.store.put(chave, claim['revision'], final)
            except Exception as erro:
                if not _conflito(erro):
                    raise
        self.reconciliar()

    def reconciliar(self) -> None:
        doc = self._indice()
        mudou = False
        ordens = doc['data'].get('ordens', [])
        vinculos = {}
        pendentes = set()
        for o in ordens:
            for cid in o.get('comentarios', []):
                vinculos.setdefault((o.get('pid'), cid), []).append(o)
        for chave in self._pendentes():
            lote = self.store.get(chave, {})['data']
            if lote.get('estado') in {'aguardando', 'lancando', 'continuidade_indisponivel'}:
                pendentes.update((chave.split(':')[1], cid) for cid in lote.get('comentarios', []))
        def da_ordem(pid, campos):
            # Conferido na hora de gravar (Codex 2, R3): versão atendida fora da ponte só recebe a correção da
            # ordem anterior; comentário que voltou à fila desde a leitura acima não é reescrito.
            def decidir(atual, c):
                if self._filas_com(c, pid, atual['id']):
                    return None
                if (atual.get('ponte') or {}).get('estado') == 'atendido_fora':
                    return {'correction': campos['correction']} if campos.get('correction') else None
                return campos
            return decidir
        for o in ordens:
            pasta = Path(o.get('dir', ''))
            if not pasta.is_dir():
                continue
            if o.get('estado') in FINAIS_ORDEM:
                final = _ler(pasta / 'resultado.json')
                # Conclusão explícita posterior prevalece sobre falha inferida.
                # Sem resultado novo, a ordem final permanece fechada.
                if not final or final.get('status') == o.get('estado'):
                    continue
            try:
                est = estado_ordem(o['dir'])
            except PonteErro:
                continue
            situacao = est['situacao']
            nome = VENDORS.get(o.get('vendor'), {}).get('nome', o.get('vendor'))
            campos = dict(status=ROTULO.get(situacao, situacao).format(v=nome, n=est['ativos']),
                          ponte=dict(estado=situacao, ordem=o['id'], vendor=o.get('vendor'), ativos=est['ativos']))
            if est.get('resultado'):
                correcao = est['resultado'].get('resumo', '')
                if est['resultado'].get('pendencias'):
                    correcao += ' · Pendências: ' + '; '.join(est['resultado']['pendencias'])
                campos['correction'] = correcao
            for cid in o.get('comentarios', []):
                if len(vinculos.get((o['pid'], cid), [])) == 1 and (o['pid'], cid) not in pendentes:
                    self._patch_atomico(cid, o['pid'], da_ordem(o['pid'], campos))
            if situacao != o.get('estado'):
                if situacao in FINAIS_ORDEM:
                    self.store.event(o['pid'], f'Ponte: ordem {o["id"]} terminou · {situacao}', 'bridge', ordem=o['id'])
                o['estado'] = situacao
                mudou = True
        lidas = {}  # pasta da ordem → comentários recebidos; uma leitura por ciclo (Codex 2, R8)
        for (pid, cid), partes in vinculos.items():
            if len(partes) < 2:
                continue
            # Versões de cada fatia que as ordens receberam (pedido + complementos). Ordem antiga sem assinatura
            # congelada não permite conferir e mantém o comportamento anterior (Codex 2, R7).
            for p in partes:
                if p.get('dir') not in lidas and Path(p.get('dir', '')).is_dir():
                    lidas[p['dir']] = _comentarios_da_ordem(Path(p['dir']))
            recebidas = [x for p in partes for x in lidas.get(p.get('dir'), [])
                         if (x.get('comentario_original_id') or x.get('id')) == cid]
            cobertas = None if any(not x.get('assinatura_humana') for x in recebidas) else {x['assinatura_humana'] for x in recebidas}
            def partes_decidir(atual, c, pid=pid, partes=partes, cobertas=cobertas):
                # Pendência recalculada na transação (Codex 2, R5): parte que voltou à fila mantém o rótulo da fila,
                # que diz se o projeto está pausado; atendido fora da ponte não é reescrito.
                estado_atual = (atual.get('ponte') or {}).get('estado')
                if estado_atual == 'atendido_fora':
                    return None
                pendente = bool(self._filas_com(c, pid, atual['id']))
                if pendente and estado_atual in {'fila', 'fila_pausada'}:
                    return None
                completa = all(p.get('estado') == 'corrigido' for p in partes) and not pendente
                if completa and cobertas is not None:
                    # Fatia editada que nenhuma ordem recebeu nem foi atendida fora da ponte não conclui o comentário.
                    completa = _assinaturas_fatias(atual) <= cobertas | set(atual.get('assinaturas_atendidas_fora') or [])
                return dict(status=('Corrigido pela IA · todas as partes concluídas, confira' if completa else
                                    'Correção em partes · há destinos ou notas pendentes'),
                            ponte=dict(estado='corrigido' if completa else 'em_partes',
                                       ordens=[p['id'] for p in partes], partes=len(partes), pendente=pendente))
            self._patch_atomico(cid, pid, partes_decidir)
        if mudou:
            try:
                self.store.put('bridge-orders', doc['revision'], dict(ordens=ordens))
            except Exception as erro:
                if not _conflito(erro):
                    raise
