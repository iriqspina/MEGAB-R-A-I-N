"""Project sources with a complete, read-only catalogue of human HTML reports."""
from __future__ import annotations
import hashlib, importlib.util, json, logging, os, re, sys, threading, time
from datetime import datetime, timezone
from pathlib import Path
from central_store import APP, ROOT, ident, now, read_json

sys.path.insert(0,str(ROOT/'bin'))
from mb_catalogo import coletar

EXTS={'.png':'image','.jpg':'image','.jpeg':'image','.webp':'image','.gif':'image','.svg':'image','.pdf':'pdf','.html':'html','.htm':'html','.mp3':'audio','.wav':'audio','.mp4':'video','.webm':'video','.md':'text','.txt':'text'}
EXCLUDE={'node_modules','.git','.venv','runtime-packages','_arquivo','historico','backups','backup'}
REPORT_EXCLUDE=EXCLUDE-{'_arquivo','historico'}|{'private','privado','privados','privadas','secrets','credenciais','__pycache__'}
ARCHIVES={'_arquivo','historico','histórico','history'}
COLORS=['#c7a0ff','#62d9bf','#f8ae74','#8bb7ff','#f9a9cf','#d6dd86']

def dated(value):
    try: return datetime.fromisoformat(value.replace('Z','+00:00')).timestamp() if value else 0
    except (TypeError,ValueError,OverflowError): return 0

def excluded(part,history=False):
    name=part.casefold()
    names=REPORT_EXCLUDE if history else EXCLUDE|REPORT_EXCLUDE
    return name.startswith('.') or name in names or name.startswith(('backup-','backup_','backups-','backups_'))
def stamp(path):
    try: return datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(timespec='seconds')
    except OSError: return None
def redact(text):
    text=re.sub(r'(?i)((?:api[_ -]?key|token|senha|password|stream[_ -]?key|chave(?: de transmiss[aã]o)?)\s*[:=]\s*)([^\s,;]{10,})',r'\1[oculto]',text)
    return re.sub(r'\b(?:sk-[A-Za-z0-9_-]{16,}|live_[A-Za-z0-9_-]{16,})\b','[credencial oculta]',text)
def clean(text): return redact(re.sub(r'[`*_#]+','',re.sub(r'\[([^]]+)\]\([^)]+\)',r'\1',text)).strip())
def brief(text):
    lines=[clean(x) for x in text.splitlines() if x.strip() and not x.lstrip().startswith(('#','<!--','|','```'))]
    tldr=next((x.split('—',1)[-1].split(':',1)[-1].strip() for x in lines if 'TL;DR' in x.upper()),None)
    return (tldr or next((x for x in lines if len(x)>45),'Nenhum resumo registrado ainda.'))[:550]

class Sources:
    def __init__(self,store,parent=None):
        self.store=store; self.parent=Path(parent or ROOT.parent).resolve(); self.lock=threading.RLock()
        self.projects={}; self.files={}; self.cache={}; self.scan_time=0; self.fingerprints={}; self.session_cache=(0,[])
        self.summary_lock=threading.RLock(); self.summary_cache={}; self.summary_flights={}; self.summary_generation={}
        self.summary_snapshot=None;self.summary_snapshot_flight=None;self.summary_snapshot_generation=0
        self.summary_ttl=15
        from central_returns import Returns
        self.returns=Returns(store)
        from central_catalog import Catalog
        self.catalog=Catalog(store); self._catalog_seen={}
        self.discover()
    def discover(self):
        roots=[]
        if ROOT.parent==self.parent: roots.append(ROOT)
        for p in sorted(self.parent.iterdir(),key=lambda p:p.name.casefold()):
            if p.is_dir() and not p.name.startswith('.') and p.resolve().is_relative_to(self.parent) and any((p/n).exists() for n in ('MEGABRAIN','ESTADO.md','00_PARA-VOCE','memoria/estado/ESTADO.md')): roots.append(p.resolve())
        discovered={ident(p):p for p in dict.fromkeys(roots)}
        with self.lock:
            changed=list(discovered.items())!=list(self.projects.items())
            previous=list(self.projects); self.projects=discovered
        if changed:
            # A new order also changes the assigned catalogue colors.
            for pid in set(previous)|set(discovered): self.invalidate_summary(pid)
        self.scan_time=time.time()

    def invalidate_summary(self,pid):
        with self.summary_lock:
            self.summary_cache.pop(pid,None)
            self.summary_generation[pid]=self.summary_generation.get(pid,0)+1
            self.summary_snapshot=None;self.summary_snapshot_generation+=1
    def root(self,pid):
        with self.lock: root=self.projects.get(pid)
        if root is None: raise KeyError('Projeto não encontrado.')
        return root
    def source_paths(self,root):
        brain=root/'MEGABRAIN' if (root/'MEGABRAIN').is_dir() else root
        out={}
        for name in ('ESTADO','HANDOFF','DECISOES'):
            out[name]=next((p for p in [root/'memoria/estado'/f'{name}.md',root/f'{name}.md',brain/'memoria/estado'/f'{name}.md',brain/f'{name}.md'] if p.is_file()),None)
        return out
    def fingerprint(self,root):
        paths=[p for p in self.source_paths(root).values() if p]+[root/'dados/entregas.json']
        inbox=root/'00_PARA-VOCE'
        if inbox.is_dir(): paths.extend(self.report_paths(root)); paths.extend(self.asset_paths(inbox,limit=1000))
        facts=[]
        for p in sorted(set(paths),key=lambda p:str(p).casefold()):
            try:
                st=p.stat(); facts.append((str(p),st.st_mtime_ns,st.st_size))
            except OSError: facts.append((str(p),'unavailable',0))
        return ident(facts)
    def walk_files(self,base,root,history=False):
        root=Path(root).resolve(); base=Path(base)
        if not base.resolve().is_relative_to(root): return
        seen=set()
        for directory,dirs,files in os.walk(base,followlinks=False):
            dirs[:]=sorted(d for d in dirs if not excluded(d,history)
                          and not (Path(directory)/d).is_symlink()
                          and not getattr(Path(directory)/d,'is_junction',lambda:False)()
                          and (Path(directory)/d).resolve().is_relative_to(root))
            for name in sorted(files):
                p=Path(directory)/name
                if excluded(name,history): continue
                try: resolved=p.resolve(strict=True)
                except (OSError,ValueError): continue
                if not resolved.is_relative_to(root) or any(excluded(x,history) for x in resolved.relative_to(root).parts): continue
                if resolved not in seen and resolved.is_file():
                    seen.add(resolved); yield resolved
    def report_paths(self,root):
        # Reports are never subject to the thumbnail/other-asset limits.
        return [p for p in self.walk_files(root/'00_PARA-VOCE',root,history=True) if p.suffix.lower() in {'.html','.htm'}]
    def asset_paths(self,base,limit=1000):
        paths=[]
        for p in self.walk_files(base,base):
            if p.suffix.lower() in EXTS and p.suffix.lower() not in {'.md','.txt'}:
                paths.append(p)
                if len(paths)>=limit: break
        return paths
    def index_file(self,path,root,role='result'):
        if not path: return None
        try:
            p=Path(path).resolve(strict=True)
            if not p.is_file() or not p.is_relative_to(root.resolve()) or p.suffix.lower() not in EXTS: return None
            if any(excluded(x,history=True) for x in p.relative_to(root).parts): return None
            if p.stat().st_size>250_000_000: return None
            fid=ident(p)
            with self.lock: self.files[fid]=(p,root.resolve())
            return dict(id=fid,name=p.name,type=EXTS[p.suffix.lower()],role=role,url=f'/api/files/{fid}',updated_at=stamp(p),size=p.stat().st_size,author='Não informado',origin=str(p.relative_to(root)),historical=any(x.casefold() in ARCHIVES for x in p.relative_to(root).parts[:-1]))
        except OSError: return None
    def project_summary(self,pid,force=False):
        """One root per scan; concurrent readers share a scan without holding the file index lock."""
        started=time.monotonic()
        while True:
            with self.summary_lock:
                cached=self.summary_cache.get(pid)
                if cached and time.monotonic()-cached[0]<self.summary_ttl and (not force or cached[0]>=started):
                    return dict(cached[1])
                flight=self.summary_flights.get(pid)
                if flight is None:
                    flight=threading.Event();self.summary_flights[pid]=flight
                    generation=self.summary_generation.get(pid,0)
                    break
            flight.wait()
        try:
            with self.lock:
                root=self.projects.get(pid)
                if root is None: raise KeyError('Projeto não encontrado.')
                color=COLORS[list(self.projects).index(pid)%len(COLORS)]
            paths=self.source_paths(root); source=paths['ESTADO']
            try: text=source.read_text(encoding='utf-8-sig')[:24000] if source else ''
            except OSError: text=''
            reg=read_json(root/'dados/entregas.json').get('entregas',[])
            reports=self.report_paths(root)
            row=dict(id=pid,name='MegaBrain' if root==ROOT else root.name,color=color,updated_at=stamp(source) if source else None,summary=brief(text),source_age=stamp(source) if source else None,delivery_count=len(reg),report_count=len(reports),source='ESTADO.md' if source else 'Sem estado registrado')
            with self.summary_lock:
                # Poll/discovery may invalidate while the filesystem scan is in flight.
                if self.summary_generation.get(pid,0)==generation:
                    self.summary_cache[pid]=(time.monotonic(),row)
            return dict(row)
        finally:
            with self.summary_lock:
                self.summary_flights.pop(pid,None);flight.set()

    def summaries(self):
        if time.time()-self.scan_time>60: self.discover()
        while True:
            with self.summary_lock:
                cached=self.summary_snapshot
                if cached and time.monotonic()-cached[0]<self.summary_ttl:
                    return {**cached[1],'projects':[dict(row) for row in cached[1]['projects']]}
                flight=self.summary_snapshot_flight
                if flight is None:
                    flight=threading.Event();self.summary_snapshot_flight=flight
                    generation=self.summary_snapshot_generation
                    break
            flight.wait()
        try:
            with self.lock: ids=list(self.projects)
            rows=[]
            for pid in ids:
                try: rows.append(self.project_summary(pid))
                except KeyError: continue  # Removed by discovery during this snapshot.
            result={'projects':rows,'revision':ident(rows),'scanned_at':now()}
            with self.summary_lock:
                if self.summary_snapshot_generation==generation:
                    # Age begins after the complete catalogue, even if a cold scan exceeded the TTL.
                    self.summary_snapshot=(time.monotonic(),result)
            return {**result,'projects':[dict(row) for row in rows]}
        finally:
            with self.summary_lock:
                self.summary_snapshot_flight=None;flight.set()
    def sessions(self,root):
        if time.time()-self.session_cache[0]>30:
            try:
                path=ROOT/'motor/mods/megabrain-mod/coletor/mb_sessoes.py'
                spec=importlib.util.spec_from_file_location('mb_sessions_app',path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
                data=mod.coletar(horas=24).get('sessoes',[])
                self.session_cache=(time.time(),data)
            except Exception: self.session_cache=(time.time(),[])
        rows=[]
        for s in self.session_cache[1]:
            try: matched=Path(s.get('cwd','')).resolve().is_relative_to(root)
            except (OSError,ValueError): matched=False
            if matched:
                rows.append(dict(id=str(s.get('id',ident(s))),vendor=s.get('fonte','IA'),title=s.get('titulo','Sessão'),status='Atividade recente' if s.get('idade_s',999)>0 and s.get('idade_s',999)<300 else 'Sem atividade recente',updated_at=datetime.fromtimestamp(s.get('ultima_ms',0)/1000,timezone.utc).isoformat(),evidence='Última escrita observada; não confirma execução ou conclusão.'))
        return rows[:30]
    def detail(self,pid,force=False,summary=None):
        root=self.root(pid)
        if not force and pid in self.cache and time.time()-self.cache[pid][0]<8: return self.cache[pid][1]
        summary=dict(summary) if summary is not None else self.project_summary(pid,force=force)
        paths=self.source_paths(root)
        try: text=paths['ESTADO'].read_text(encoding='utf-8-sig')[:24000] if paths['ESTADO'] else ''
        except OSError: text=''
        next_step=next((clean(x.split(':',1)[-1]) for x in text.splitlines() if re.match(r'^(?:\*\*)?PR[ÓO]XIMO PASSO',x,re.I)),'Consulte o resultado mais recente ou comece uma sessão de análise.')
        summary['next_step']=next_step[:600]
        assets=[]; deliveries=[]; activity=[]; delivered_files=set(); delivery_ids=set()
        try: catalog=coletar(root).get('entregas',[])
        except (ValueError,OSError,KeyError): catalog=[]
        for row in catalog:
            try:
                location=Path(row.get('arquivo') or row.get('pasta') or root)
                location=location.resolve() if location.is_absolute() else (root/location).resolve()
                if not location.is_relative_to(root) or any(excluded(x,history=True) for x in location.relative_to(root).parts): continue
            except (OSError,ValueError): continue
            asset=self.index_file(row.get('arquivo',''),root)
            if asset: assets.append(asset)
            # Explicit records precede legacy rows and keep their human metadata.
            if asset and asset['id'] in delivered_files: continue
            did=row.get('id',ident(row))
            if did in delivery_ids: continue
            delivery_ids.add(did)
            if asset: delivered_files.add(asset['id'])
            deliveries.append(dict(id=did,title=row.get('titulo','Entrega'),status=row.get('estado','nao_verificado'),updated_at=asset['updated_at'] if asset else row.get('atualizado_em'),recorded_updated_at=row.get('atualizado_em'),summary=row.get('etapa') or row.get('proxima_acao',''),file_id=asset['id'] if asset else None,type=asset['type'] if asset else None,verified=row.get('estado')=='pronto',verification_label='Arquivo confere com o registro; consulte a prova vinculada.' if row.get('estado')=='pronto' else 'Verificação não registrada.',session=row.get('sessao','Origem não registrada'),historical=asset.get('historical',False) if asset else row.get('estado')=='arquivado',origin=row.get('origem','registro'),source=asset['origin'] if asset else row.get('fonte')))
        for p in self.report_paths(root):
            asset=self.index_file(p,root)
            if not asset: continue
            assets.append(asset)
            if asset['id'] in delivered_files: continue
            delivered_files.add(asset['id'])
            deliveries.append(dict(id='report:'+asset['id'],title=p.stem.replace('_',' '),status='nao_verificado',updated_at=asset['updated_at'],summary='Relatório do histórico; verificação não registrada.' if asset['historical'] else 'Relatório encontrado no projeto; verificação não registrada.',file_id=asset['id'],type='html',verified=False,verification_label='Verificação não registrada.',session='Origem não registrada',historical=asset['historical'],origin='arquivo local',source=asset['origin']))
        for base in [root/'00_PARA-VOCE',root/'referencias',root/'assets']:
            if not base.is_dir(): continue
            candidates=self.asset_paths(base,limit=3000)
            candidates.sort(key=lambda p:stamp(p) or '',reverse=True)
            for p in candidates[:240]:
                role='reference' if base.name=='referencias' or 'referenc' in p.name.casefold() else 'result' if base.name=='00_PARA-VOCE' else 'asset'
                asset=self.index_file(p,root,role)
                if asset: assets.append(asset)
        assets=list({a['id']:a for a in assets}.values())
        assets.sort(key=lambda x:dated(x['updated_at']),reverse=True)
        deliveries.sort(key=lambda x:dated(x['updated_at']),reverse=True)
        summary['delivery_count']=len(deliveries)
        for name,p in paths.items():
            if p: activity.append(dict(id=ident(p),title=f'{name.capitalize()} atualizado',detail='Data do arquivo de origem, sem inferir conclusão.',at=stamp(p),kind='source'))
        for d in deliveries[:15]: activity.append(dict(id=d['id'],title=d['title'],detail=d['summary'],at=d['updated_at'],kind='delivery'))
        with self.store.db() as c:
            events=c.execute('SELECT id,data FROM events WHERE project=? ORDER BY id DESC LIMIT 30',(pid,)).fetchall()
        activity.extend(dict(json.loads(r['data']),id='event:'+str(r['id'])) for r in events)
        activity.sort(key=lambda x:x.get('at') or '',reverse=True)
        refs=self.store.listing('refs',pid)
        data=dict(project=summary,deliveries=deliveries,assets=assets,activity=activity,sessions=self.sessions(root),comments=self.store.listing('comments',pid),references=refs)
        data['revision']=ident(data)
        self.cache[pid]=(time.time(),data)
        # 261021 F0b: alimenta o índice de busca; falha dele nunca derruba o detalhe.
        try: self.catalog.ingest(pid,data)
        except Exception: logging.getLogger('megabrain.catalog').exception('Falha ao indexar o detalhe; busca mantém a última observação')
        return data
    def poll(self):
        # Rediscovery belongs to polling, even when nobody requests summaries.
        previous=set(self.projects)
        self.discover()
        for pid in set(self.projects)-previous:
            self.store.event(pid,'Novo projeto disponível na central',kind='project_discovered')
        for pid in previous-set(self.projects):
            self.cache.pop(pid,None); self.fingerprints.pop(pid,None)
            self.store.event(pid,'Projeto deixou de estar disponível',kind='project_unavailable')
        # Observe project-local execution without dispatching or altering sessions.
        try:
            from central_operations import sync
            if self.parent==ROOT.parent.resolve():
                sync(self.store)
        except (ValueError,OSError,json.JSONDecodeError):
            logging.getLogger('megabrain.operations').warning('Fonte de execução indisponível; observação anterior preservada')
        # Import only allowlisted exports. No downloaded text can execute a task.
        try:
            from central_feedback import scan
            scan(self.store,self)
        except Exception:
            logging.getLogger('megabrain.feedback').exception('Falha ao receber respostas; nova tentativa no próximo ciclo')
        for pid,root in list(self.projects.items()):
            try: value=self.fingerprint(root)
            except OSError:
                logging.getLogger('megabrain.sources').warning('Fonte temporariamente indisponível: %s',pid)
                continue
            old=self.fingerprints.get(pid)
            if old and old!=value:
                self.cache.pop(pid,None); self.invalidate_summary(pid); self.store.event(pid,'Fontes do projeto atualizadas')
            self.fingerprints[pid]=value
        # 261021 F0b: preenchimento gradual do índice de busca — um projeto por ciclo,
        # apenas na raiz real (a mesma guarda de central_operations), sem varrer raízes de teste.
        if self.parent==ROOT.parent.resolve():
            for pid in list(self.projects):
                fingerprint=self.fingerprints.get(pid)
                if fingerprint is None or self._catalog_seen.get(pid)==fingerprint: continue
                try:
                    if pid not in self._catalog_seen and self.catalog.covered(pid):
                        self._catalog_seen[pid]=fingerprint; continue
                except Exception:
                    logging.getLogger('megabrain.catalog').exception('Falha ao ler cobertura do índice de busca'); continue
                try:
                    self.detail(pid,force=True); self._catalog_seen[pid]=fingerprint
                except Exception:
                    self._catalog_seen[pid]=fingerprint
                    logging.getLogger('megabrain.catalog').exception('Falha ao indexar o projeto no catálogo de busca: %s',pid)
                break
        self.returns.observe(self)
    def file(self,fid):
        with self.lock: item=self.files.get(fid)
        if not item:
            # A saved report can be restored before any project detail is read.
            # Resolve only human reports in already registered roots, using the
            # same exclusions and confinement as the normal catalogue.
            with self.lock: roots=tuple(self.projects.values())
            for root in roots:
                for path in self.report_paths(root):
                    if ident(path)!=fid: continue
                    if self.index_file(path,root):
                        with self.lock: item=self.files.get(fid)
                    break
                if item: break
        if not item: raise KeyError('Arquivo não indexado. Reabra o projeto.')
        p,root=item
        if not p.is_file() or not p.resolve().is_relative_to(root) or p.suffix.lower() not in EXTS: raise KeyError('Arquivo indisponível.')
        return p,root
