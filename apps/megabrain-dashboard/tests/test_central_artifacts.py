"""Artifact hash/namespace and nested-preview policy tests, without model calls."""
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
import central_artifacts as artifacts


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        base=APP.parents[1]/'evidence/261011_app-megabrain/security-fixtures';base.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(prefix='artifacts-',dir=base);self.app=Path(self.tmp.name)
        self.patch=patch.object(artifacts,'APP',self.app);self.patch.start()
        self.job={'id':'a'*32,'title':'Synthetic job','artifacts':[]}
        self.directory=artifacts.job_directory(self.job['id']);(self.directory/'workspace').mkdir(parents=True)
    def tearDown(self):self.patch.stop();self.tmp.cleanup()
    def file(self,name,text):
        path=self.directory/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')
        out=artifacts.register_artifact(self.job['id'],name);self.job['artifacts'].append(out);return out
    def test_download_allows_code_text_languages_but_not_logs_or_controls(self):
        for name in ['main.go','main.rs','main.sh','main.ps1','main.java']:
            out=self.file('workspace/'+name,'// synthetic code')
            self.assertTrue(artifacts.resolve_artifact(self.job,out['id'])[0].exists())
        for relative in ['stdout.txt','01-stage/prompt.txt','workspace/.env','workspace/AGENTS.md','../outside.py','workspace/../../data/native.key']:
            with self.subTest(relative=relative),self.assertRaises((ValueError,OSError)):
                artifacts.checked_path(self.directory,relative)
    def test_changed_artifact_fails_hash_check(self):
        artifact=self.file('workspace/main.py','print("before")')
        (self.directory/artifact['path']).write_text('print("after")')
        with self.assertRaises(ValueError):artifacts.resolve_artifact(self.job,artifact['id'])
    def test_hardlink_cannot_be_registered(self):
        source=self.directory/'workspace/original.py';source.write_text('pass')
        linked=self.directory/'workspace/linked.py'
        try:os.link(source,linked)
        except OSError as exc:self.skipTest(type(exc).__name__)
        with self.assertRaises(ValueError):artifacts.register_artifact(self.job['id'],'workspace/linked.py')
    def test_wrapper_uses_checked_ids_and_innermost_frame_is_opaque(self):
        aid='b'*24;content=artifacts.preview_wrapper(self.job['id'],aid)
        self.assertIn('/render/'+aid,content);self.assertIn('sandbox="allow-scripts allow-forms"',content)
        self.assertNotIn('allow-same-origin',content)
        policy=artifacts.PREVIEW_WRAPPER_HEADERS['Content-Security-Policy']
        self.assertIn("default-src 'none'",policy);self.assertIn("frame-src 'self'",policy)
        render=artifacts.RENDER_HEADERS['Content-Security-Policy']
        for directive in ["sandbox allow-scripts allow-forms","connect-src 'none'","frame-src 'none'","form-action 'none'","script-src 'unsafe-inline'"]:
            self.assertIn(directive,render)
        self.assertNotIn('allow-same-origin',render)
        for forbidden in ['allow-top-navigation','allow-popups','allow-downloads']:
            self.assertNotIn(forbidden,content);self.assertNotIn(forbidden,render)
        for jid,artifact in [('" onclick="attack','b'*24),('a'*32,'../secret'),('a'*32,'b'*23)]:
            with self.assertRaises(ValueError):artifacts.preview_wrapper(jid,artifact)
    def test_preview_inlines_registered_hash_checked_js_css_svg(self):
        self.file('workspace/main.js','document.querySelector("button").onclick=()=>{document.body.dataset.clicked="yes"};')
        self.file('workspace/main.css','body{color:rebeccapurple}')
        self.file('workspace/logo.svg','<svg xmlns="http://www.w3.org/2000/svg"/>')
        content='<html><link rel="stylesheet" href="main.css"><img src="logo.svg"><button>Test</button><script src="main.js"></script></html>'
        out=artifacts.isolated_preview(content,self.job)
        self.assertIn('<style>body{color:rebeccapurple}</style>',out)
        self.assertIn('document.querySelector',out);self.assertNotIn('src="main.js"',out)
        self.assertIn('data:image/svg+xml;base64,',out)
    def test_external_attrs_refresh_base_and_frames_are_removed(self):
        content='<base href="https://evil.test/"><meta http-equiv="refresh" content="0;url=https://evil.test"><a href="javascript:alert(1)" ping="https://evil.test">Link</a><img srcset="https://evil.test/a 1x" src="https://evil.test/a"><iframe srcdoc="attack"></iframe><script src="https://evil.test/a.js"></script>'
        out=artifacts.isolated_preview(content,self.job)
        for bad in ['https://evil.test','javascript:','srcdoc','srcset','<base','<meta','<iframe','<script src']:
            self.assertNotIn(bad,out)
    def test_nested_asset_paths_work_without_parent_traversal(self):
        page=self.file('workspace/demo/index.html','<script src="main.js"></script>')
        self.file('workspace/demo/main.js','document.body.dataset.nested="yes";')
        out=artifacts.isolated_preview('<script src="main.js"></script>',self.job,page)
        self.assertIn('dataset.nested',out)
        self.assertNotIn('dataset.nested',artifacts.isolated_preview('<script src="../demo/main.js"></script>',self.job,page))
    def test_research_report_escapes_title_text_and_drops_non_web_sources(self):
        self.job['title']='<script>attack()</script>'
        made=artifacts.research_report(self.job,'<img onerror=attack()>',[
            {'url':'javascript:alert(1)','title':'bad'},{'url':'https://example.org/source?a=1&b=2','title':'<safe>','retrieved':True}])
        text=(self.directory/made[0]['path']).read_text(encoding='utf-8')
        self.assertIn('&lt;script&gt;',text);self.assertIn('&lt;img',text)
        self.assertNotIn('javascript:',text);self.assertIn('&amp;b=2',text)


if __name__=='__main__':unittest.main()
