"""Independent staging/evidence tests; no generated-code execution or inference."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
import central_execution as execution


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        base=APP.parents[1]/'evidence/261011_app-megabrain/security-fixtures'
        base.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(prefix='execution-',dir=base)
        self.base=Path(self.tmp.name);self.project=self.base/'project';self.project.mkdir()
        self.job=self.base/'job'
    def tearDown(self):self.tmp.cleanup()
    def source(self,name='main.py',text='def add(a,b): return a+b\n'):
        p=self.project/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8');return p
    def prepare(self,selected=None):return execution.prepare_execution(self.project,self.job,selected)
    def artifact(self,name='main.py',text='def add(a,b): return a+b\n'):
        p=self.job/'workspace'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8');return p
    def command(self,**updates):
        return {'kind':'command','name':'shell','command':'python -B -m unittest discover -v','cwd':str(self.job/'workspace'),
                'exit_code':0,'status':'completed','aggregated_output':'Ran 2 tests in 0.01s\n\nOK',
                'evidence_source':'fixture:codex_jsonl:item.completed',**updates}
    def result(self,commands=None,sources=None):
        commands=commands or [];result={'tool_results':commands,'web_sources':sources or []}
        if any(e.get('kind')=='command' for e in commands):
            result.update(capability='code',status='completed',workspace_after={'files':[
                {'path':r['relative_path'],'sha256':r['sha256']} for r in execution.inventory_changes(self.job)['files']]})
        return [result]
    def test_default_workspace_is_empty_and_does_not_copy_project(self):
        self.source(); result=self.prepare()
        self.assertEqual(list(Path(result['workspace']).iterdir()),[])
        self.assertEqual(result['selected_files'],[])
        self.assertFalse(json.loads(Path(result['baseline_path']).read_text())['is_os_sandbox'])
    def test_selected_copy_tracks_changes_without_touching_original(self):
        original=self.source();self.prepare(['main.py']);self.artifact(text='def add(a,b): return a+b+1\n')
        self.artifact('README.md','Run tests before release.\n')
        result=execution.inventory_changes(self.job)
        self.assertEqual(original.read_text(),'def add(a,b): return a+b\n')
        self.assertTrue(result['originals_unchanged'])
        self.assertEqual({r['relative_path']:r['change'] for r in result['files']},{'README.md':'added','main.py':'modified'})
    def test_existing_attempt_is_never_overwritten(self):
        self.prepare();self.artifact()
        with self.assertRaises(FileExistsError):self.prepare()
        self.assertTrue((self.job/'workspace/main.py').exists())
    def test_traversal_absolute_paths_and_private_controls_rejected(self):
        for selected in ['../outside.py','/outside.py','C:/outside.py','src\\main.py','src//main.py','.env','data/config.json','AGENTS.md','file.py:stream']:
            with self.subTest(selected=selected),self.assertRaises((ValueError,OSError)):
                execution.prepare_execution(self.project,self.base/('trial'+str(abs(hash(selected)))),[selected])
    def test_selection_validated_fully_before_any_copy(self):
        self.source()
        with self.assertRaises((ValueError,OSError)):self.prepare(['main.py','missing.py'])
        self.assertFalse((self.job/'workspace').exists())
    def test_secret_binary_and_file_size_are_rejected(self):
        self.source('secret-config.json','{"api_key":"synthetic-long-secret-for-security-test"}')
        (self.project/'binary.py').write_bytes(b'abc\x00def')
        (self.project/'large.py').write_bytes(b'x'*(execution.LIMITS['max_file_bytes']+1))
        for name in ['secret-config.json','binary.py','large.py']:
            with self.subTest(name=name),self.assertRaises(ValueError):
                execution.prepare_execution(self.project,self.base/name.replace('.','-'),[name])
    def test_quantity_duplicates_and_total_size_are_bounded(self):
        self.source()
        with self.assertRaises(ValueError):self.prepare(['main.py']*101)
        with self.assertRaises(ValueError):self.prepare(['main.py','MAIN.py'])
        with patch.dict(execution.LIMITS,{'max_total_bytes':5}):
            with self.assertRaises(ValueError):self.prepare(['main.py'])
    def test_hardlink_is_not_copied_or_indexed(self):
        original=self.source();alias=self.project/'alias.py'
        try:os.link(original,alias)
        except OSError as exc:self.skipTest('Hardlinks unavailable: '+type(exc).__name__)
        with self.assertRaises(ValueError):self.prepare(['alias.py'])
        self.assertEqual(execution.list_source_files(self.project)['files'],[])
    def test_symlink_is_not_followed_when_available(self):
        external=self.base/'outside.py';external.write_text('private fixture')
        link=self.project/'linked.py'
        try:link.symlink_to(external)
        except OSError as exc:self.skipTest('Symlink permission unavailable: '+type(exc).__name__)
        with self.assertRaises(ValueError):self.prepare(['linked.py'])
    def test_original_changes_are_detected_even_if_workspace_tests_pass(self):
        source=self.source();self.prepare(['main.py']);self.artifact(text='print("candidate")\n');source.write_text('external edit\n')
        result=execution.finalize_execution(self.job,self.result([self.command()]))
        self.assertFalse(result['originals_unchanged']);self.assertIn('originals_changed_outside_workspace',result['verification']['reasons'])
    def test_removed_file_recorded_and_sensitive_output_not_published(self):
        self.source();self.prepare(['main.py']);(self.job/'workspace/main.py').unlink()
        self.artifact('.env','TOKEN=synthetic\n');self.artifact('secret.json','{"password":"synthetic-long-password-for-test"}')
        result=execution.finalize_execution(self.job,[])
        self.assertEqual(result['removed'],['main.py']);self.assertEqual(result['artifacts'],[])
        self.assertEqual(len(result['blocked']),2)
    def test_generated_caches_do_not_become_artifacts_or_fail_code_gate(self):
        self.prepare();self.artifact();self.artifact('__pycache__/example.pyc','synthetic cache')
        result=execution.finalize_execution(self.job,self.result([self.command()]))
        self.assertEqual(result['verification']['status'],'passed')
        self.assertEqual(len(result['artifacts']),1);self.assertTrue(result['skipped'])
    def test_real_harness_test_result_required_not_model_text_or_test_json(self):
        self.prepare();self.artifact();self.artifact('tests.json','{"status":"PASS","tests":12}')
        for result in [[{'text':'All tests passed.'}],self.result([self.command(evidence_source='')]),self.result([self.command(command="echo 'pytest PASS'")])]:
            with self.subTest(result=result):
                manifest=execution.finalize_execution(self.job,result)
                self.assertEqual(manifest['verification']['status'],'needs_review')
                self.assertEqual(manifest['tests'],[])
    def test_zero_tests_missing_summary_failed_and_running_never_pass(self):
        self.prepare();self.artifact()
        cases=[{'aggregated_output':'Ran 0 tests in 0s\nOK'},{'aggregated_output':'PASS'}, {'exit_code':1}, {'status':'running'}]
        for change in cases:
            with self.subTest(change=change):
                result=execution.finalize_execution(self.job,self.result([self.command(**change)]))
                self.assertEqual(result['verification']['status'],'needs_review')
                self.assertNotEqual(result['tests'][0]['status'],'passed')
    def test_shell_wrappers_chains_and_python_inline_commands_are_unverified(self):
        self.prepare()
        commands=['python -m unittest; echo PASS','powershell -Command "python -m unittest"',
                  'python -c "print(1)" -m unittest','echo python -m unittest','python -m unittest && echo OK']
        for command in commands:
            with self.subTest(command=command):self.assertEqual(execution.observed_evidence(self.result([self.command(command=command)]))['tests'],[])
    def test_changed_code_and_observed_positive_test_produce_hashed_manifest(self):
        self.prepare();artifact=self.artifact()
        result=execution.finalize_execution(self.job,self.result([self.command()]))
        self.assertEqual(result['verification']['status'],'passed');self.assertEqual(result['tests'][0]['reported_count'],2)
        self.assertEqual(result['artifacts'][0]['sha256'],execution._sha(artifact.read_bytes()))
        self.assertTrue(Path(result['manifest_path']).exists())
    def test_research_requires_current_url_from_observed_web_result(self):
        self.prepare();self.artifact('research.html','<h1>Research fixture</h1>')
        source={'url':'https://example.org/current','accessed_at':'2026-10-11T20:00:00Z','retrieved':True,'retrieval_kind':'page_fetch'}
        tool={'kind':'web_fetch','name':'WebFetch','status':'completed','urls':[source['url']],'evidence_source':'fixture:claude_tool_result'}
        good=execution.finalize_execution(self.job,self.result([tool],[source]),mode='research')
        self.assertEqual(good['verification']['status'],'passed')
        for changes in [{'retrieved':False},{'accessed_at':None},{'retrieval_kind':'search_result'},{'url':'https://example.org/invented'},{'url':'http://127.0.0.1/private'}]:
            with self.subTest(changes=changes):
                bad=execution.finalize_execution(self.job,self.result([tool],[{**source,**changes}]),mode='research')
                self.assertEqual(bad['verification']['status'],'needs_review')
    def test_new_edit_or_action_after_green_test_invalidates_old_proof(self):
        self.prepare();self.artifact()
        results=self.result([self.command()])
        self.artifact(text='def add(a,b): return a-b\n')
        changed=execution.finalize_execution(self.job,results)
        self.assertIn('code_changed_after_observed_stage',changed['verification']['reasons'])
        for event in [self.command(command='echo unchecked'),{'kind':'file_change','status':'completed','evidence_source':'fixture'}]:
            with self.subTest(event=event):
                updated=self.result([self.command(),event])
                result=execution.finalize_execution(self.job,updated)
                self.assertIn('post_test_changes_or_unverified_commands',result['verification']['reasons'])
        inspected=self.result([self.command(),self.command(command='Get-ChildItem -File',aggregated_output='main.py')])
        self.assertEqual(execution.finalize_execution(self.job,inspected)['verification']['status'],'passed')
    def test_mixed_mode_needs_both_research_and_code_evidence(self):
        self.prepare();self.artifact()
        result=execution.finalize_execution(self.job,self.result([self.command()]),mode='mixed')
        self.assertEqual(result['verification']['status'],'needs_review')
        self.assertIn('no_observed_live_web_action',result['verification']['reasons'])
    def test_picker_uses_same_guards_and_reports_depth_truncation(self):
        self.source();self.source('src/ui.ts','export const name="fixture";')
        self.source('.env','secret');self.source('node_modules/dep.js','dependency');self.source('AGENTS.md','instructions')
        self.source('src/token.json','{"access_token":"synthetic-secret-token-value-long"}')
        self.source('a/b/c/d/e/f/g/h/i/j/deep.py','pass')
        result=execution.list_source_files(self.project)
        self.assertEqual({r['path'] for r in result['files']},{'main.py','src/ui.ts'})
        self.assertTrue(result['truncated'])
    def test_unmodified_selected_code_is_not_presented_as_new_artifact(self):
        self.source();self.prepare(['main.py'])
        result=execution.finalize_execution(self.job,self.result([self.command()]))
        self.assertEqual(result['artifacts'],[]);self.assertIn('no_code_artifact',result['verification']['reasons'])
    def test_observed_windows_cmd_wrapper_preserves_raw_command_and_provenance(self):
        self.prepare();self.artifact('test/example.test.cjs','// fixture; never executed\n')
        raw=r'''"C:\\Windows\\system32\\cmd.exe" /c 'node --test --preserve-symlinks --preserve-symlinks-main' '''.strip()
        event=self.command(command=raw,aggregated_output='ℹ tests 18\nℹ pass 18\nℹ fail 0',evidence_source={'path':'observed.log','json_event_index':40,'vendor':'codex'})
        result=execution.finalize_execution(self.job,self.result([event]))
        test=result['tests'][0]
        self.assertEqual(test['command'],raw);self.assertEqual(test['reported_count'],18)
        self.assertEqual(test['normalization']['method'],'unwrapped_fixed_shell')
        self.assertEqual(test['evidence_source'],event['evidence_source'])
        self.assertEqual(result['verification']['status'],'passed')
    def test_fixed_powershell_wrapper_accepts_only_inert_flags_and_direct_payload(self):
        self.prepare()
        allowed=r'''"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -Command "python -B -m unittest discover -v"'''
        tests=execution.observed_evidence([{'tool_results':[self.command(command=allowed)]}])['tests']
        self.assertEqual(len(tests),1);self.assertEqual(tests[0]['status'],'passed')
        for raw in [allowed.replace('-NoProfile','-ExecutionPolicy Bypass'),allowed.replace('-Command','-EncodedCommand'),allowed.replace('System32','Temp'),allowed.replace('python -B','echo python -B'),allowed.replace(' -v"',' -v; echo PASS"'),allowed.replace(' -v"',' -v & echo PASS"'),allowed.replace(' -v"',' -v %FAKE%"')]:
            with self.subTest(raw=raw):self.assertEqual(execution.observed_evidence([{'tool_results':[self.command(command=raw)]}])['tests'],[])
    def test_node_runtime_flags_supersede_same_suite_without_erasing_failure(self):
        self.prepare();self.artifact()
        failed=self.command(command='node --test',exit_code=1,status='failed',aggregated_output='tests 1\nfail 1')
        passed=self.command(command='node --test --preserve-symlinks --preserve-symlinks-main',aggregated_output='tests 18\npass 18\nfail 0')
        result=execution.finalize_execution(self.job,self.result([failed,passed]))
        self.assertEqual(result['verification']['status'],'passed');self.assertEqual(len(result['tests']),2)
        self.assertEqual(result['tests'][0]['status'],'failed');self.assertFalse(result['tests'][0]['current_attempt'])
        self.assertEqual(result['tests'][0]['superseded_by_test_index'],1)
        self.assertTrue(result['tests'][1]['current_attempt'])
    def test_different_suite_selection_or_cwd_cannot_erase_failed_test(self):
        self.prepare();self.artifact()
        failed=self.command(command='node --test test/a.test.cjs',exit_code=1,status='failed',aggregated_output='tests 1\nfail 1')
        for change in [{'command':'node --test test/b.test.cjs'},{'command':'node --test --test-name-pattern=one test/a.test.cjs'},{'command':'node --test test/a.test.cjs','cwd':'elsewhere'}]:
            passed=self.command(aggregated_output='tests 1\npass 1',**change)
            result=execution.finalize_execution(self.job,self.result([failed,passed]))
            self.assertIn('test_failure_or_unverified',result['verification']['reasons'])
            self.assertTrue(result['tests'][0]['current_attempt'])
    def test_runtime_flag_after_double_dash_is_a_suite_target_not_ignored(self):
        a=execution._test_command(self.command(command='node --test'))
        b=execution._test_command(self.command(command='node --test -- --preserve-symlinks'))
        self.assertNotEqual(a[-1],b[-1])
    def test_private_technical_snapshot_files_excluded_without_hiding_public_change(self):
        self.prepare();self.artifact();self.artifact('.automations/check.cjs','// synthetic');self.artifact('evidence/test-result.json','{"status":"PASS"}')
        results=self.result([self.command()]);snapshot=results[0]['workspace_after']['files']
        snapshot.extend([{'path':'.automations/check.cjs','sha256':'0'*64},{'path':'evidence/test-result.json','sha256':'1'*64}])
        result=execution.finalize_execution(self.job,results)
        self.assertEqual(result['verification']['status'],'passed')
        self.assertEqual(len(result['snapshot_comparison']['excluded_adapter_files']),2)
        self.assertEqual({a['relative_path'] for a in result['artifacts']},{'main.py'})
        self.assertEqual(len(result['skipped']),2)
        self.artifact(text='def add(a,b): return a-b\n')
        self.assertIn('code_changed_after_observed_stage',execution.finalize_execution(self.job,results)['verification']['reasons'])
    def test_arbitrary_script_after_wrapped_test_remains_pending(self):
        self.prepare();self.artifact()
        good=self.command(command=r'''"C:\Windows\System32\cmd.exe" /c 'node --test' ''',aggregated_output='tests 2\npass 2')
        arbitrary=self.command(command=r'''"C:\Windows\System32\cmd.exe" /c 'node .automations/verify-delivery.cjs' ''')
        result=execution.finalize_execution(self.job,self.result([good,arbitrary]))
        self.assertIn('post_test_changes_or_unverified_commands',result['verification']['reasons'])
        readonly=self.command(command=r'''"C:\Windows\System32\cmd.exe" /c dir''',aggregated_output='main.py')
        self.assertEqual(execution.finalize_execution(self.job,self.result([good,readonly]))['verification']['status'],'passed')
    def test_inline_node_cannot_claim_test_execution(self):
        event=self.command(command='node --test --eval "console.log(18)"',aggregated_output='tests 18\npass 18')
        self.assertEqual(execution.observed_evidence([{'tool_results':[event]}])['tests'],[])
    def test_technical_directory_link_is_blocked_before_exclusion(self):
        self.prepare();self.artifact()
        external=self.base/'external';external.mkdir();(external/'private.txt').write_text('do not follow',encoding='utf-8')
        link=self.job/'workspace/.automations'
        try:link.symlink_to(external,target_is_directory=True)
        except OSError as exc:self.skipTest('Directory symlink permission unavailable: '+type(exc).__name__)
        inventory=execution.inventory_changes(self.job)
        self.assertEqual(inventory['skipped'],[])
        self.assertEqual(inventory['blocked'],[{'relative_path':'.automations','reason':'excluded_directory_or_link'}])
        self.assertNotIn('private.txt',[r['relative_path'] for r in inventory['files']])


if __name__=='__main__':unittest.main()
