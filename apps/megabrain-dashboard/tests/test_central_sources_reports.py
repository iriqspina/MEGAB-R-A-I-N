"""Complete report discovery and change polling, using synthetic project files."""
from pathlib import Path
import hashlib
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
from central_sources import Sources
from central_store import Store, ident


class ReportsTests(unittest.TestCase):
    def setUp(self):
        base=APP.parents[1]/'evidence/261012_central-relatorios/test-fixtures'
        base.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(prefix='reports-',dir=base)
        self.parent=Path(self.tmp.name)
        self.project=self.parent/'Synthetic Project'
        (self.project/'00_PARA-VOCE').mkdir(parents=True)
        self.store=Store(self.parent/'test-store.sqlite3')
        self.sources=Sources(self.store,self.parent)
        self.sessions=patch.object(self.sources,'sessions',return_value=[])
        self.sessions.start()
        self.feedback=patch('central_feedback.scan',return_value=None)
        self.feedback.start()

    def tearDown(self):
        self.feedback.stop(); self.sessions.stop(); self.tmp.cleanup()

    def report(self,relative,text='<html>synthetic fixture</html>',at=None):
        p=self.project/'00_PARA-VOCE'/relative
        p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding='utf-8')
        if at is not None: os.utime(p,(at,at))
        return p

    def detail(self): return self.sources.detail(ident(self.project),force=True)

    def test_cold_restored_report_resolves_before_project_detail(self):
        path=self.report('task/current.html')
        self.assertNotIn(ident(path),self.sources.files)
        resolved,root=self.sources.file(ident(path))
        self.assertEqual(resolved,path.resolve())
        self.assertEqual(root,self.project.resolve())
        self.assertFalse(self.sources.cache)

    def test_cold_restore_does_not_recover_private_or_unknown_project(self):
        private=self.report('private/hidden.html')
        external=self.parent/'Unregistered'/'00_PARA-VOCE'/'secret.html'
        external.parent.mkdir(parents=True);external.write_text('<html>not registered</html>')
        for path in (private,external):
            with self.subTest(path=path),self.assertRaises(KeyError):
                self.sources.file(ident(path))

    def test_cold_restore_does_not_recover_removed_report(self):
        path=self.report('task/removed.html');fid=ident(path);path.unlink()
        with self.assertRaises(KeyError):self.sources.file(fid)

    def test_more_than_1000_reports_have_results_ids_and_latest_first(self):
        expected=[]
        for n in range(1250): expected.append(self.report(f'task/report-{n:04}.html',at=1_700_000_000+n))
        expected.append(self.report('last.HTM',at=1_700_010_000))
        before={p:p.read_bytes() for p in expected}
        data=self.detail()
        rows=[d for d in data['deliveries'] if d['type']=='html']
        self.assertEqual(len(rows),1251)
        self.assertEqual(len({d['file_id'] for d in rows}),1251)
        self.assertEqual(rows[0]['file_id'],ident(expected[-1]))
        self.assertEqual(data['project']['delivery_count'],1251)
        for row in rows:
            self.assertFalse(row['verified']); self.assertEqual(row['status'],'nao_verificado')
            self.assertEqual(self.sources.file(row['file_id'])[0].read_bytes(),before[self.sources.file(row['file_id'])[0]])
        self.assertEqual(len([a for a in data['assets'] if a['type']=='html']),1251)

    def test_manual_title_session_and_hash_proof_survive_path_deduplication(self):
        p=self.report('task/index.html',at=1_700_000_000)
        (self.project/'dados').mkdir()
        registro={'schema_version':1,'entregas':[dict(id='human-id',titulo='Título humano preservado',pasta='00_PARA-VOCE/task',arquivo='00_PARA-VOCE/task/index.html',estado='pronto',proxima_acao='Decisão humana pendente',sessao='sessão registrada',atualizado_em='2023-01-01T00:00:00Z',verificado_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),verificacao='prova sintética')]}
        target=self.project/'dados/entregas.json'; target.write_text(json.dumps(registro),encoding='utf-8')
        original=target.read_bytes()
        data=self.detail(); rows=[d for d in data['deliveries'] if d['file_id']==ident(p)]
        self.assertEqual(len(rows),1)
        row=rows[0]
        self.assertEqual(row['id'],'human-id'); self.assertEqual(row['title'],'Título humano preservado')
        self.assertEqual(row['session'],'sessão registrada'); self.assertTrue(row['verified'])
        self.assertEqual(row['recorded_updated_at'],'2023-01-01T00:00:00Z')
        self.assertEqual(target.read_bytes(),original)
        p.write_text('<html>changed after verification</html>')
        row=next(d for d in self.detail()['deliveries'] if d['file_id']==ident(p))
        self.assertFalse(row['verified']); self.assertEqual(row['status'],'em_revisao')

    def test_archive_is_accessible_and_private_backup_runtime_trees_are_excluded(self):
        history=self.report('task/historico/old.html')
        archive=self.report('_arquivo/2025/old.html')
        current=self.report('task/result.html')
        for folder in ['backup','backups','backup-previous','backup_2025','privado','privados','private','secrets','node_modules','.hidden']:
            self.report(folder+'/hidden.html')
        data=self.detail(); ids={d['file_id'] for d in data['deliveries'] if d['type']=='html'}
        self.assertEqual(ids,{ident(history),ident(archive),ident(current)})
        for row in data['deliveries']:
            if row['file_id'] in {ident(history),ident(archive)}: self.assertTrue(row['historical'])
        for asset in data['assets']: self.assertNotIn('hidden.html',asset['origin'])

    def test_html_references_remain_available_without_results_registration(self):
        refs=self.project/'referencias';refs.mkdir()
        p=refs/'guide.html';p.write_text('<html>reference</html>')
        data=self.detail()
        asset=next(a for a in data['assets'] if a['id']==ident(p))
        self.assertEqual(asset['role'],'reference')

    def test_poll_notices_added_and_modified_report_after_1000_other_reports(self):
        for n in range(1050): self.report(f'task/{n:04}.html')
        pid=ident(self.project); self.sources.poll()
        first=self.detail(); first_revision=first['revision']
        tail=self.report('task/zz-last.html')
        self.sources.cache[pid]=(float('inf'),first)
        self.sources.poll()
        self.assertNotIn(pid,self.sources.cache)
        added=self.detail(); self.assertNotEqual(added['revision'],first_revision)
        row=next(d for d in added['deliveries'] if d['file_id']==ident(tail))
        previous=self.sources.fingerprints[pid]
        # Keep size fixed: nanosecond mtimes must still invalidate the source cache.
        old=tail.stat();os.utime(tail,ns=(old.st_atime_ns,old.st_mtime_ns+5_000_000_000))
        self.sources.cache[pid]=(float('inf'),added)
        self.sources.poll()
        self.assertNotEqual(self.sources.fingerprints[pid],previous)
        self.assertNotIn(pid,self.sources.cache)
        self.assertEqual(next(d for d in self.detail()['deliveries'] if d['file_id']==ident(tail))['id'],row['id'])
        events=self.store.events()['events']
        self.assertEqual(len([e for e in events if e['kind']=='source_changed']),2)
        self.assertEqual(len([e for e in events if e['kind']=='report_arrived']),1)
        self.assertFalse(any(e['kind']=='report_updated' for e in events))

    def test_poll_discovers_new_project_without_summaries_call(self):
        project=self.parent/'New Project'; (project/'00_PARA-VOCE').mkdir(parents=True)
        (project/'00_PARA-VOCE/new.html').write_text('<html>new project</html>')
        pid=ident(project); self.assertNotIn(pid,self.sources.projects)
        self.sources.poll()
        self.assertIn(pid,self.sources.projects)
        self.assertTrue(any(e['project_id']==pid and e['kind']=='project_discovered' for e in self.store.events()['events']))
        self.assertTrue(any(d['type']=='html' for d in self.sources.detail(pid)['deliveries']))

    def test_symlinks_cannot_import_external_reports_or_projects(self):
        outside=self.parent/'Unrelated';outside.mkdir();(outside/'secret.html').write_text('secret')
        (outside/'00_PARA-VOCE').mkdir();(outside/'00_PARA-VOCE/other.html').write_text('outside')
        # This directory is deliberately outside the Sources parent.
        isolated=self.parent/'Isolated';isolated.mkdir()
        sources=Sources(self.store,isolated)
        try:
            (self.project/'00_PARA-VOCE/linked.html').symlink_to(outside/'secret.html')
            (self.project/'00_PARA-VOCE/linked-dir').symlink_to(outside,target_is_directory=True)
            (isolated/'Imported Project').symlink_to(outside,target_is_directory=True)
        except OSError as exc: self.skipTest('OS does not permit synthetic symlinks: '+str(exc))
        self.assertEqual(self.sources.report_paths(self.project),[])
        self.assertIsNone(self.sources.index_file(self.project/'00_PARA-VOCE/linked.html',self.project))
        sources.discover();self.assertEqual(sources.projects,{})


if __name__=='__main__': unittest.main()
