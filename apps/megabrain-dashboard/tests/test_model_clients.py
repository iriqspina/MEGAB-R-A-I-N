"""Native image contracts. Every subprocess is simulated; no inference/network."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import model_clients as clients


class ImageClientsTests(unittest.TestCase):
    def setUp(self):
        evidence=clients.ROOT/'evidence/261018_ponte-orquestradores/transporte-imagens'
        evidence.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='adapter-test-',dir=evidence)
        self.addCleanup(self.temp.cleanup)
        self.job=Path(self.temp.name).resolve(); self.workspace=self.job/'workspace'
        self.folder=self.workspace/'.mb-anexos';self.folder.mkdir(parents=True)
        self.stage=self.job/'01-stage';self.source=self.job/'source';self.source.mkdir()
        self.paths=[self.image('print.png')];self.calls=[];self.help_calls=[];self.stdin=[];self.native_bytes=[]
        self.exit_code=0;self.echo=False;self.fail_communicate=False;self.missing_result=False
        self.config=self.job/'global-zcode.json'
        self.config.write_text(json.dumps({'provider':{'zai':{'kind':'anthropic','options':{
            'baseURL':'https://api.z.ai/api/anthropic','apiKey':'FAKE-TEST-SUBSCRIPTION-SECRET'},
            'models':{'GLM-5.3':{'reasoning':{'defaultLevel':'max','levels':['low','max']}}}}}}),encoding='utf-8')
        self.bundle=self.job/'zcode.cjs';self.bundle.write_text('// fake pinned runtime',encoding='utf-8')
        for target,value in [('ZCODE',self.bundle),('ZCODE_CONFIG',self.config),
                             ('ZCODE_SHA256',hashlib.sha256(self.bundle.read_bytes()).hexdigest())]:
            p=patch.object(clients,target,value);p.start();self.addCleanup(p.stop)
        self.popen_patch=patch.object(clients.subprocess,'Popen',side_effect=self.popen)
        self.popen_mock=self.popen_patch.start();self.addCleanup(self.popen_patch.stop)
        p=patch.object(clients.subprocess,'run',side_effect=self.help);self.help_mock=p.start();self.addCleanup(p.stop)
        p=patch.object(clients,'_verify_auth',return_value={'local_check':True});self.auth_mock=p.start();self.addCleanup(p.stop)
        p=patch.dict(os.environ,{'OPENAI_API_KEY':'FAKE-OPENAI-TEST-SECRET','ANTHROPIC_API_KEY':'FAKE-ANTHROPIC-TEST-SECRET'})
        p.start();self.addCleanup(p.stop)

    def image(self,name,fmt='PNG'):
        buffer=io.BytesIO();Image.new('RGB',(3,2),(13,61,102)).save(buffer,format=fmt)
        path=self.folder/name;path.write_bytes(buffer.getvalue());return path

    def help(self,args,**kwargs):
        self.help_calls.append(args)
        self.assertEqual(args[-1],'--help','An unexpected real subprocess would be forbidden')
        return subprocess.CompletedProcess(args,0,'--image --attach --input-format stream-json --output-format','')

    def popen(self,args,**kwargs):
        self.calls.append((args,kwargs))
        test=self
        class Process:
            pid=123456;returncode=test.exit_code
            def communicate(self,stdin=None,timeout=None):
                test.stdin.append(stdin)
                if test.fail_communicate:raise subprocess.TimeoutExpired(args,timeout)
                if '--image' in args:
                    for i,value in enumerate(args):
                        if value=='--image':test.native_bytes.append(Path(args[i+1]).read_bytes())
                if '--output-last-message' in args:
                    Path(args[args.index('--output-last-message')+1]).write_text('resultado',encoding='utf-8')
                    return json.dumps({'type':'turn.completed','usage':{'input_tokens':1}}),'simulado'
                record={'type':'result','result':'resultado','response':'resultado','modelUsage':{'claude-opus-5-5':{}},'sessionId':'fake'}
                if test.missing_result:return json.dumps({'type':'system','subtype':'init'}),''
                output=json.dumps(record)
                if test.echo:
                    # A native replay/error accidentally echoes the entire input.
                    output=stdin+output
                return output,''
            def kill(self):self.returncode=-9
            def poll(self):return self.returncode
        return Process()

    def run_client(self,model='codex',**kwargs):
        return clients.run_model(model,'max','Analise o print',self.source,self.stage,**kwargs)

    def assert_off(self,result):
        self.assertFalse(result['tools_allowed']);self.assertEqual(result['tools_requested'],[])
        self.assertFalse(result['visual_inspection_observed'])
        env=self.calls[0][1]['env']
        self.assertNotIn('OPENAI_API_KEY',env);self.assertNotIn('ANTHROPIC_API_KEY',env)
        self.assertEqual(os.environ['OPENAI_API_KEY'],'FAKE-OPENAI-TEST-SECRET')

    def test_codex_native_flags_bytes_and_unchanged_account_policy(self):
        result=self.run_client(image_paths=[str(self.paths[0])])
        self.assertEqual(result['status'],'completed');self.assert_off(result)
        args,kw=self.calls[0]
        self.assertEqual(args[-2:],['--','-']);self.assertEqual(args[args.index('--image')+1],str(self.paths[0]))
        self.assertEqual(self.native_bytes,[self.paths[0].read_bytes()]);self.assertEqual(self.stdin,['Analise o print'])
        for setting in ('features.shell_tool=false','features.multi_agent=false','features.apps=false',
                        'features.plugins=false','features.hooks=false','web_search="disabled"','approval_policy="never"'):
            self.assertIn(setting,args)
        self.assertEqual(args[args.index('--sandbox')+1],'read-only')
        self.assertEqual(kw['env']['CODEX_HOME'],str(clients.HOME/'.codex-gpt2'))
        self.assertEqual(result['image_transport']['state'],'submitted_to_cli')
        self.assertTrue(result['image_inputs'][0]['transported']);self.assertFalse(result['image_inputs'][0]['visual_inspection_observed'])
        self.assertEqual(result['image_inputs'][0]['sha256'],hashlib.sha256(self.native_bytes[0]).hexdigest())

    def test_codex_explicit_primary_is_child_only(self):
        before=os.environ.get('CODEX_HOME')
        self.run_client(image_paths=self.paths,codex_account='primary')
        self.assertEqual(self.calls[0][1]['env']['CODEX_HOME'],str(clients.HOME/'.codex'))
        self.assertEqual(os.environ.get('CODEX_HOME'),before)

    def test_claude_multimodal_stdin_all_supported_mimes(self):
        paths=[self.paths[0],self.image('foto.jpg','JPEG'),self.image('quadro.gif','GIF'),self.image('quadro.webp','WEBP')]
        result=self.run_client('claude',image_paths=paths)
        self.assertEqual(result['status'],'completed');self.assert_off(result)
        args=self.calls[0][0]
        self.assertEqual(args[args.index('--input-format')+1],'stream-json')
        self.assertEqual(args[args.index('--output-format')+1],'stream-json');self.assertIn('--verbose',args)
        self.assertEqual(args[args.index('--tools')+1],'');self.assertIn('--safe-mode',args)
        self.assertIn('--strict-mcp-config',args);self.assertIn('--no-session-persistence',args)
        self.assertEqual(args[args.index('--permission-mode')+1],'dontAsk')
        message=json.loads(self.stdin[0]);self.assertEqual(message['type'],'user')
        self.assertEqual(message['message']['role'],'user');self.assertIsNone(message['parent_tool_use_id'])
        content=message['message']['content'];self.assertEqual(content[0],{'type':'text','text':'Analise o print'})
        for block,path,mime in zip(content[1:],paths,['image/png','image/jpeg','image/gif','image/webp']):
            self.assertEqual(block['source']['media_type'],mime)
            self.assertEqual(base64.b64decode(block['source']['data'],validate=True),path.read_bytes())

    def test_claude_research_keeps_only_web_tools_and_parses_stream(self):
        result=self.run_client('claude',capability='research',image_paths=self.paths,cancel_event=threading.Event())
        self.assertEqual(result['status'],'completed')
        args=self.calls[0][0];self.assertEqual(args[args.index('--tools')+1],'WebSearch,WebFetch')
        self.assertIn('--restricted',args);self.assertEqual(args.count('--verbose'),1)
        self.assertEqual(args[args.index('--max-turns')+1],'12')

    def test_glm_fails_before_config_auth_or_inference_even_with_attach(self):
        before=self.config.read_bytes()
        with patch.object(clients,'_glm_config') as configure:
            result=self.run_client('glm',image_paths=self.paths)
        self.assertEqual(result['status'],'image_transport_unavailable')
        self.assertIn('somente texto',result['error']);self.assertEqual(result['image_transport']['state'],'unsupported')
        self.assertFalse(result['model_called']);self.assertFalse(result['image_inputs'][0]['transported'])
        self.popen_mock.assert_not_called();configure.assert_not_called();self.auth_mock.assert_not_called()
        self.assertEqual(self.help_calls,[[self.calls_node(),str(self.bundle),'--help']])
        self.assertEqual(self.config.read_bytes(),before)

    @staticmethod
    def calls_node():return clients.shutil.which('node')

    def test_glm_changed_bundle_refuses_before_help(self):
        self.bundle.write_text('// changed',encoding='utf-8')
        result=self.run_client('glm',image_paths=self.paths)
        self.assertEqual(result['status'],'image_transport_unavailable');self.help_mock.assert_not_called()

    def test_missing_native_option_fails_before_inference(self):
        for model in ('codex','claude'):
            with self.subTest(model=model),patch.object(clients.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'--help','')):
                self.stage=self.job/(model+'-no-support')
                result=self.run_client(model,image_paths=self.paths)
                self.assertEqual(result['status'],'image_transport_unavailable');self.assertFalse(result['model_called'])
        self.popen_mock.assert_not_called()

    def test_no_image_behavior_all_clients(self):
        for model in ('codex','claude','glm'):
            with self.subTest(model=model):
                self.stage=self.job/(model+'-text');result=self.run_client(model)
                self.assertEqual(result['image_transport']['state'],'not_requested');self.assertEqual(result['image_inputs'],[])
                args,kw=self.calls[-1];self.assertNotIn('--image',args);self.assertNotIn('--input-format',args)
                if model=='glm':
                    bridge_args=json.loads((self.stage/'zcode-argv.json').read_text(encoding='utf-8'))
                    self.assertNotIn('--attach',bridge_args);self.assertEqual(bridge_args[bridge_args.index('--mode')+1],'plan')
                    self.assertIn(','.join(clients.DENY_TOOLS),bridge_args)
                    config=json.loads((self.stage/'zcode.json').read_text(encoding='utf-8'))
                    self.assertFalse(config['features']['mcp']);self.assertFalse(config['plugins']['enabled'])
                else:self.assertEqual(result['status'],'completed')
        self.help_mock.assert_not_called()

    def test_empty_list_keeps_text_transport(self):
        result=self.run_client(image_paths=[])
        self.assertEqual(result['status'],'completed');self.help_mock.assert_not_called()

    def test_logs_redact_echoed_base64_without_persisting_stdin(self):
        self.echo=True
        result=self.run_client('claude',image_paths=self.paths)
        self.assertEqual(result['status'],'completed')
        encoded=base64.b64encode(self.paths[0].read_bytes()).decode()
        for path in self.stage.rglob('*'):
            if path.is_file():
                content=path.read_text(encoding='utf-8')
                self.assertNotIn(encoded,content);self.assertNotIn('FAKE-OPENAI-TEST-SECRET',content)
        self.assertIn('[REDACTED]',(self.stage/'stdout.log').read_text(encoding='utf-8'))

    def test_cli_failure_does_not_claim_transport(self):
        self.exit_code=2
        result=self.run_client('claude',image_paths=self.paths)
        self.assertEqual(result['status'],'error');self.assertFalse(result['image_inputs'][0]['transported'])

    def test_missing_result_does_not_claim_transport(self):
        self.missing_result=True
        result=self.run_client('claude',image_paths=self.paths)
        self.assertEqual(result['status'],'missing_result_event');self.assertFalse(result['image_inputs'][0]['transported'])

    def test_invalid_lists_and_count_block_before_any_process(self):
        for i,paths in enumerate(('bad',{},tuple(self.paths),[None],self.paths*7,self.paths*2)):
            with self.subTest(paths=type(paths).__name__):
                self.stage=self.job/f'bad-{i}';result=self.run_client(image_paths=paths)
                self.assertEqual(result['status'],'error');self.assertFalse(result['model_called'])
        self.help_mock.assert_not_called();self.popen_mock.assert_not_called()

    def test_noncanonical_outside_other_job_directory_missing_paths(self):
        other=self.job/'other/workspace/.mb-anexos';other.mkdir(parents=True)
        outside=other/'print.png';outside.write_bytes(self.paths[0].read_bytes())
        invalid=[Path('relative.png'),self.source/'outside.png',outside,self.folder,
                 self.folder/'missing.png',str(self.folder/'..'/'.mb-anexos'/'print.png')]
        for i,path in enumerate(invalid):
            self.stage=self.job/f'path-{i}'
            result=self.run_client(image_paths=[path]);self.assertEqual(result['status'],'error')
        self.help_mock.assert_not_called();self.popen_mock.assert_not_called()

    def test_hardlink_blocked(self):
        linked=self.folder/'hard.png';os.link(self.paths[0],linked)
        result=self.run_client(image_paths=[linked]);self.assertEqual(result['status'],'error')
        self.help_mock.assert_not_called();self.popen_mock.assert_not_called()

    def test_symlink_or_junction_blocked(self):
        # Simulate Windows' reparse attribute on a lexical ancestor, before
        # resolve could hide a junction. No admin privilege or real shell.
        real_lstat=Path.lstat
        def reparse(path,*args,**kwargs):
            info=real_lstat(path,*args,**kwargs)
            if path==self.folder:return SimpleNamespace(st_mode=info.st_mode,st_file_attributes=0x400)
            return info
        with patch.object(Path,'lstat',reparse):
            result=self.run_client(image_paths=self.paths);self.assertEqual(result['status'],'error')
        self.help_mock.assert_not_called();self.popen_mock.assert_not_called()

    def test_forged_header_svg_and_empty_fail_real_decode(self):
        for i,data in enumerate((b'<svg xmlns="http://www.w3.org/2000/svg"/>',b'\x89PNG\r\n\x1a\nFAKE',b'')):
            self.paths[0].write_bytes(data);self.stage=self.job/f'forged-{i}'
            result=self.run_client(image_paths=self.paths);self.assertEqual(result['status'],'error')
        self.help_mock.assert_not_called();self.popen_mock.assert_not_called()

    def test_byte_limits_per_file_and_total_before_inference(self):
        with self.paths[0].open('wb') as stream:stream.truncate(clients.IMAGE_LIMITS['max_file_bytes']+1)
        result=self.run_client(image_paths=self.paths);self.assertEqual(result['status'],'error')
        self.paths=[self.image('a.png'),self.image('b.png')];self.stage=self.job/'total'
        limits=dict(clients.IMAGE_LIMITS,max_total_bytes=self.paths[0].stat().st_size)
        with patch.object(clients,'IMAGE_LIMITS',limits):
            result=self.run_client(image_paths=self.paths)
        self.assertIn('48 MiB',result['error']);self.help_mock.assert_not_called();self.popen_mock.assert_not_called()

    def test_exact_six_and_48_mib_acceptance_boundary(self):
        self.assertEqual(clients.IMAGE_LIMITS,{'max_files':6,'max_file_bytes':8*1024*1024,'max_total_bytes':48*1024*1024})
        data=self.paths[0].read_bytes()
        padded=data+b'\0'*(8*1024*1024-len(data))
        paths=[]
        for index in range(6):
            path=self.folder/f'full-{index}.png';path.write_bytes(padded);paths.append(path)
        rows,contents=clients._image_inputs(self.stage,paths)
        self.assertEqual(len(rows),6);self.assertEqual(sum(map(len,contents)),48*1024*1024)
        self.help_mock.assert_not_called();self.popen_mock.assert_not_called()

    def test_cancelled_before_start_preserves_no_transport_proof(self):
        event=threading.Event();event.set()
        result=self.run_client(image_paths=self.paths,cancel_event=event)
        self.assertEqual(result['status'],'cancelled');self.assertFalse(result['visual_inspection_observed'])
        self.assertEqual(result['image_transport']['state'],'not_started')
        self.help_mock.assert_not_called();self.popen_mock.assert_not_called()

    def test_codex_checks_bytes_again_after_help_auth(self):
        def mutate(*args):
            Image.new('RGB',(3,2),'red').save(self.paths[0]);return {'local_check':True}
        with patch.object(clients,'_verify_auth',side_effect=mutate):
            result=self.run_client(image_paths=self.paths)
        self.assertEqual(result['status'],'error');self.assertIn('mudou antes',result['error'])
        self.popen_mock.assert_not_called()

    def test_code_images_do_not_broaden_sandbox_or_permissions(self):
        with patch.object(clients,'_code_runtime',return_value={}),patch.object(clients,'_sandbox_preflight',return_value={'passed':True}):
            result=self.run_client(capability='code',execution_dir=self.workspace,image_paths=self.paths)
        self.assertEqual(result['status'],'completed');args=self.calls[0][0]
        for item in clients._code_permissions():self.assertIn(item,args)
        self.assertIn('features.shell_tool=true',args);self.assertIn('--strict-config',args)
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox',args)
        self.assertEqual(result['codex_account'],'primary')


if __name__=='__main__':unittest.main()
