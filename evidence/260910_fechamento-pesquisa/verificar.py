"""Verifica a entrega recuperada; nao despacha modelos nem altera Git."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
BRAIN = ROOT / 'memoria/cerebro'
RAW_NAMES = [
    '260910_pesquisa-niveis-de-esforco-mecanica',
    '260910_pesquisa-benchmarks-custo-vs-qualidade-por-esforco',
    '260910_pesquisa-ultracode-e-orquestracao-multiagente',
    '260910_pesquisa-taticas-prompt-planejamento-e-perguntas',
    '260910_youtube-5EhrMJ9HIfU-astra-wrong-e-claudex-loop',
    '260910_pesquisa-cotas-chatgpt-pro-e-claude-pro-x5',
    '260910_pesquisa-double-diamond-fragmentacao-e-modelo-por-etapa',
]
WIKI_NAMES = [
    '260910_niveis-de-esforco-o-que-muda-e-como-um-low-chega-perto',
    '260910_modelo-por-etapa-double-diamond-fragmentado',
    '260910_cotas-lado-a-lado-chatgpt-pro-e-claude-pro',
]
index = (BRAIN / 'INDICE.md').read_text(encoding='utf-8')
sources = index.split('## Fontes processadas (raw/)', 1)[1]
hashes = {}
for name in RAW_NAMES:
    path = BRAIN / 'raw' / (name + '.md')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    matching = [line for line in sources.splitlines() if f'`raw/{name}.md`' in line]
    assert len(matching) == 1, f'Indice ausente/duplicado: {name}'
    assert digest[:16] in matching[0], f'Hash antigo: {name}'
    hashes[name] = digest
links = 0
for name in WIKI_NAMES:
    path = BRAIN / 'wiki' / (name + '.md')
    content = path.read_text(encoding='utf-8')
    assert f'`wiki/{name}.md`' in index
    for target in re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', content):
        target = target.split('#')[0]
        assert (BRAIN / 'wiki' / (target + '.md')).is_file(), target
        links += 1
report = ROOT / '00_PARA-VOCE/260910_pesquisa-esforco-e-modelos/260910_RELATORIO-esforco-modelos-e-pipeline.md'
for target in re.findall(r'\]\(([^)]+)\)', report.read_text(encoding='utf-8')):
    if not target.startswith('https://'):
        assert (report.parent / target).resolve().is_file(), target

sys.path.insert(0, str(ROOT / 'apps/automations'))
spec = importlib.util.spec_from_file_location('research_check_automations', ROOT / 'apps/automations/automations.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
config = engine.load_config()
routes = {}
for profile in ('micro', 'normal', 'frontier'):
    job = {'objective': 'Conferir perfis sem executar modelos',
           'criteria': ['Quatro papeis e revisores de fornecedores diferentes'],
           'profile': profile}
    engine.validate_job(job)
    routes[profile] = engine.preview_route_v2(config, job)

source = ROOT / 'motor/skills/orquestracao1/SKILL.md'
expected = hashlib.sha256(source.read_bytes()).hexdigest()
home = Path.home()
copies = [
    ROOT / 'motor/plugin-megabrain-claude/skills/orquestracao1/SKILL.md',
    home / '.claude/skills/orquestracao1/SKILL.md',
    home / '.codex/skills/orquestracao1/SKILL.md',
    home / '.gemini/skills/orquestracao1/SKILL.md',
    home / '.kimi-code/plugins/managed/megabrain/skills/orquestracao1/SKILL.md',
    home / 'plugins/megabrain/skills/orquestracao1/SKILL.md',
    home / '.codex/plugins/cache/personal/megabrain/1.6.3+codex.20260825202815/skills/orquestracao1/SKILL.md',
]
for copy in copies:
    assert hashlib.sha256(copy.read_bytes()).hexdigest() == expected, str(copy)

result = {'status': 'PASS', 'raws': len(hashes), 'wikis': len(WIKI_NAMES),
          'wikilinks_checked': links, 'report_links': 'PASS', 'source_sha256': expected,
          'copies_checked': [str(path) for path in copies], 'raw_sha256': hashes,
          'profile_previews': routes, 'provider_calls': 0}
dest = Path(__file__).with_name('verificacao.json')
dest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({key: result[key] for key in ('status', 'raws', 'wikis', 'wikilinks_checked', 'report_links', 'provider_calls')}, ensure_ascii=False))
print(f'{len(copies)} copias com SHA256 igual; 3 perfis validados; evidencia: {dest}')
