from pathlib import Path
import sys,json,hashlib,importlib.util,shutil
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'bin'))
spec=importlib.util.spec_from_file_location('sync_mem',ROOT/'bin/mb-sync-memoria.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
source=ROOT/'memoria/identidade/260810_memoria-pessoal.md';home=Path.home();rows=[]
targets=[('claude','.claude'),('gemini','.gemini'),('kimi','.kimi'),('kimi','.kimi-code'),('codex','.codex'),('codex','.codex-gpt2'),('claude-style','.claude'),('codex','.zcode')]
for idx,(target,dirname) in enumerate(targets):
    folder=home/dirname;dest=folder/mod.TARGET_FILE[target]
    if not folder.exists():rows.append({'destino':str(dest),'status':'cliente não encontrado'});continue
    if dest.exists():
        backup=HERE/'backup-identidades'/str(idx)/dest.name;backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():shutil.copy2(dest,backup)
    result=mod.sync_um(target,source,folder,'conteudo','<USUARIO> (<USUARIO>)')
    text=dest.read_text(encoding='utf-8-sig')
    rows.append({'destino':str(dest),'resultado':result,'regra_presente':'Encontrar e controlar o trabalho (260916' in text,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
# Apenas a skill alterada; fonte preservada, cópias derivadas recebem os mesmos bytes.
skill=ROOT/'motor/skills/megabrain/SKILL.md';skillhash=hashlib.sha256(skill.read_bytes()).hexdigest()
copies=[home/'.codex/skills/megabrain/SKILL.md',home/'.claude/skills/megabrain/SKILL.md',home/'.kimi-code/plugins/managed/megabrain/skills/megabrain/SKILL.md',home/'AppData/Roaming/kimi-desktop/daimon-share/daimon/skills/megabrain/SKILL.md']
for base in [home/'.codex/plugins/cache/personal/megabrain',home/'.codex-gpt2/plugins/cache/personal/megabrain']:
    if base.is_dir():copies.extend(base.glob('*/skills/megabrain/SKILL.md'))
for idx,dest in enumerate(copies):
    if not dest.is_file():continue
    backup=HERE/'backup-skills'/str(idx)/'SKILL.md';backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(dest,backup)
    dest.write_bytes(skill.read_bytes())
    ref=dest.parents[2]/'referencias/260916_plataforma-contrato.md'
    # installed skills resolve the central according to their own documented layout;
    # the canonical reference stays in the central, avoiding ad hoc layout creation.
    rows.append({'destino':str(dest),'tipo':'skill derivada','sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'igual_fonte':hashlib.sha256(dest.read_bytes()).hexdigest()==skillhash})
(HERE/'sincronizacao.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(rows,ensure_ascii=False,indent=2))
