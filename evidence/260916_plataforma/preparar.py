from pathlib import Path
import collections, datetime, hashlib, json, subprocess, sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(*args): return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
tracked = run('git','ls-files').splitlines()
status = run('git','status','--porcelain=v1')
(HERE/'git-antes.txt').write_text(status, encoding='utf-8')
files = [p for p in (ROOT/'00_PARA-VOCE').rglob('*') if p.is_file()]
sources = ['memoria/estado/ESTADO.md','memoria/estado/HANDOFF.md','memoria/identidade/260810_memoria-pessoal.md','motor/skills/megabrain/SKILL.md','motor/referencias/260818_padrao-resposta.md','bin/mb-contexto.py','bin/mb-inicio-sessao.py','bin/mb-entrega.py','bin/mb-relatorio-vivo.py','00_painel/RELATORIO.html','memoria/nucleo/MEGABRAIN.md','memoria/nucleo/licoes-megabrain.md','licoes-megabrain.md','INDICE.md']
manifest = {}
for name in sources:
    p=ROOT/name
    if p.is_file():
        manifest[name]={'sha256':digest(p),'bytes':p.stat().st_size}
        out=HERE/'backup'/name; out.parent.mkdir(parents=True,exist_ok=True)
        if not out.exists(): out.write_bytes(p.read_bytes())
stats={'measured_at':datetime.datetime.now().astimezone().isoformat(), 'root':str(ROOT), 'head':run('git','rev-parse','HEAD').strip(), 'dirty_entries':len(status.splitlines()), 'root_directories':[p.name for p in ROOT.iterdir() if p.is_dir()], 'inbox_directories':[p.name for p in (ROOT/'00_PARA-VOCE').iterdir() if p.is_dir()], 'inbox_loose_files':[p.name for p in (ROOT/'00_PARA-VOCE').iterdir() if p.is_file()], 'inbox_file_count':len(files),'inbox_extensions':dict(collections.Counter(p.suffix.lower() for p in files)), 'applications':[p.name for p in (ROOT/'apps').iterdir() if p.is_dir()], 'sources':manifest}
(HERE/'baseline.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in stats.items() if k not in ('sources','root_directories','inbox_directories','inbox_loose_files')},ensure_ascii=False,indent=2))
