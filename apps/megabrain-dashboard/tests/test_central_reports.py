"""Confinement, policy and project-resource regression tests for report viewer."""
from pathlib import Path
import hashlib
import os
import sys
import tempfile
import unittest
import importlib.util
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
import central_reports as reports


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path = self.root / '00_PARA-VOCE/task/entry.html'
        self.path.parent.mkdir(parents=True)
        self.fid = 'a' * 20
        self.token = 'ticket_report_123456789'

    def tearDown(self):
        self.tmp.cleanup()

    def render(self, text):
        self.path.write_text(text, encoding='utf-8')
        original = self.path.read_bytes()
        rendered = reports.render_report(self.path, self.root, self.fid, self.token)
        self.assertEqual(original, self.path.read_bytes())
        return rendered

    def put(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode())
        return path

    def test_wrapper_and_child_policies_keep_network_and_api_isolated(self):
        wrapper = reports.wrapper_report(self.fid, self.token)
        self.assertIn('/api/reports/' + self.fid + '/render?ticket=' + self.token, wrapper)
        self.assertIn('sandbox="allow-scripts allow-forms"', wrapper)
        self.assertIn('event.source!==inner.contentWindow', wrapper)
        self.assertIn("event.origin!=='null'", wrapper)
        self.assertIn('m.token!==META.token', wrapper)
        self.assertIn('m.fid!==META.fid', wrapper)
        for value in [wrapper, reports.render_headers['Content-Security-Policy']]:
            for forbidden in ['allow-same-origin', 'allow-top-navigation', 'allow-popups', 'allow-downloads']:
                self.assertNotIn(forbidden, value)
        for directive in ["connect-src 'none'", "frame-src 'none'", "form-action 'none'", "worker-src 'none'", "sandbox allow-scripts allow-forms"]:
            self.assertIn(directive, reports.render_headers['Content-Security-Policy'])
        self.assertIn("frame-src 'self'", reports.view_headers['Content-Security-Policy'])

    def test_inline_and_local_scripts_wait_for_bound_storage_restore(self):
        self.put('00_PARA-VOCE/main.js', 'window.fixtureLoaded=true;')
        result = self.render('<head></head><script src="../main.js"></script><script>window.inlineLoaded=true;</script>')
        self.assertIn('window.fixtureLoaded=true;', result)
        self.assertIn('window.inlineLoaded=true;', result)
        self.assertEqual(2, result.count('<script type="application/x-megabrain-script"'))
        self.assertIn('megabrain-report-restore', result)
        self.assertIn('m.hash!==META.hash', result)
        self.assertIn(hashlib.sha256(self.path.read_bytes()).hexdigest(), result)
        self.assertLess(result.index('Object.defineProperty(window'), result.index('window.fixtureLoaded'))
        self.assertIn("hook('CursorFerramentas'", result)
        self.assertIn("hook('DecisoesRespondiveis'", result)

    def test_images_css_fonts_and_parent_assets_are_inlined_within_project(self):
        self.put('assets/photo.png', b'fixture-image')
        self.put('assets/font.woff2', b'fixture-font')
        self.put('assets/style.css', 'body{background:url(photo.png)}@font-face{src:url(font.woff2)}')
        result = self.render('<link rel="stylesheet" href="../../assets/style.css"><img src="../../assets/photo.png">')
        self.assertIn('data:image/png;base64,', result)
        self.assertIn('data:font/woff2;base64,', result)
        self.assertNotIn('href="../../assets/style.css"', result)
        self.assertNotIn('src="../../assets/photo.png"', result)

    def test_embedded_css_artwork_fonts_and_svg_references_preserve_original_spelling(self):
        svg = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg"%3E%3Ctext%3EA)%3C/text%3E%3C/svg%3E'
        font = 'data:font/woff2;base64,Zml4dHVyZQ=='
        style = "body{background:url('" + svg + "')}@font-face{font-family:Fixture;src:url(" + font + ")}svg{filter:url(#shadow)}"
        result = self.render('<style>' + style + '</style><div style="mask:url(#mask)"></div>')
        self.assertIn('<style>' + style + '</style>', result)
        self.assertIn('mask:url(#mask)', result)
        self.assertNotIn('about:blank', result)

    def test_quoted_local_asset_parentheses_and_nonvisual_data_remain_confined(self):
        self.put('assets/photo (final).png', b'fixture-image')
        result = self.render('<style>body{background:url("../../assets/photo (final).png")}div{background:url("data:text/html,bad")}p{background:url("https://example.test/photo (final).png")}</style>')
        self.assertIn('data:image/png;base64,', result)
        self.assertEqual(2, result.count('about:blank'))
        self.assertNotIn('data:text/html', result)
        self.assertNotIn('https://example.test', result)

    def test_local_links_become_app_directives_external_links_require_click(self):
        self.put('00_PARA-VOCE/second.html', '<h1>Second</h1>')
        result = self.render('<a href="../second.html">Local</a><a href="https://example.test/reference" target="_blank" ping="https://evil.test">Ref</a><a href="javascript:alert(1)">Invalid</a>')
        self.assertIn('data-mb-local="00_PARA-VOCE/second.html"', result)
        self.assertIn('data-mb-external="https://example.test/reference"', result)
        self.assertIn("if(event.isTrusted)send(local?'open-local':'open-external'", result)
        for prohibited in ['target="_blank"', 'ping=', 'javascript:alert', 'href="https://']:
            self.assertNotIn(prohibited, result)

    def test_legacy_catalogue_absolute_file_links_open_inside_project(self):
        target = self.put('00_PARA-VOCE/second.html', '<h1>Second</h1>')
        result = self.render('<a href="'+target.as_uri()+'">File URI</a>')
        self.assertIn('data-mb-local="00_PARA-VOCE/second.html"', result)
        outside = self.root.parent / 'outside.html'
        result = self.render('<a href="'+outside.as_uri()+'">Outside</a>')
        self.assertNotIn('data-mb-local=', result)

    def test_links_to_large_html_use_report_limit_without_spending_resource_budget(self):
        target = self.put('00_PARA-VOCE/large.html', b'x' * (reports.MAX_RESOURCE + 1))
        html_text='<a href="../large.html">Relative</a><a href="'+target.as_uri()+'">File URI</a><a href="'+str(target)+'">Absolute</a>'
        with patch.object(reports,'MAX_BUNDLE',1):result=self.render(html_text)
        self.assertEqual(3,result.count('data-mb-local="00_PARA-VOCE/large.html"'))

    def test_external_resources_forms_css_and_nested_frames_do_not_load(self):
        result = self.render('<base href="https://evil.test"><meta http-equiv="refresh" content="0;url=https://evil.test"><script src="https://evil.test/script.js"></script><iframe src="https://evil.test"></iframe><img src="https://evil.test/img"><style>@import "https://evil.test/main.css";body{background:url(https://evil.test/bg)}</style><form action="https://evil.test/send"><button formaction="/api/projects/p/jobs">Send</button></form>')
        for prohibited in ['https://evil.test', '<base', '<iframe', '<script src', 'http-equiv', '/api/projects/p/jobs']:
            self.assertNotIn(prohibited, result)
        self.assertIn('action="about:blank"', result)
        self.assertIn("document.addEventListener('submit',e=>{e.preventDefault();}", result)

    def test_private_and_outside_resources_are_refused_including_encoded_paths(self):
        self.put('.private/secret.js', 'window.privateSecret=true;')
        self.put('private/secret.js', 'window.otherSecret=true;')
        result = self.render('<script src="../../.private/secret.js"></script><script src="../../private/secret.js"></script><img src="../../../outside.png"><script src="../../%2Eprivate/secret.js"></script>')
        self.assertNotIn('privateSecret', result)
        self.assertNotIn('otherSecret', result)
        self.assertNotIn('src="../../../outside.png"', result)
        for path in [self.root / '.private/secret.js', self.root / 'private/secret.js']:
            with self.assertRaises(ValueError): reports.confined_file(path, self.root)

    def test_symlink_to_outside_and_hardlinks_are_refused(self):
        outside = self.root.parent / (self.root.name + '-outside.png')
        outside.write_bytes(b'outside')
        try:
            alias = self.root / 'alias.png'
            try: alias.symlink_to(outside)
            except OSError: pass
            else:
                with self.assertRaises(ValueError): reports.confined_file(alias, self.root)
            local = self.put('assets/original.png', b'local')
            linked = self.root / 'hard.png'
            try: os.link(local, linked)
            except OSError: pass
            else:
                with self.assertRaises(ValueError): reports.confined_file(linked, self.root)
        finally:
            outside.unlink()

    def test_invalid_identity_is_rejected_before_reading_any_report(self):
        for fid, token in [('" onclick="attack', self.token), (self.fid, 'short'), (self.fid, '</script>' + 'x' * 20)]:
            with self.assertRaises(ValueError): reports.wrapper_report(fid, token)
            with self.assertRaises(ValueError): reports.render_report(self.path, self.root, fid, token)

    def test_server_draft_preferred_and_unknown_script_data_is_not_executed(self):
        wrapper = reports.wrapper_report(self.fid, self.token, {'draft': 'from-server'})
        self.assertIn('initialStorage={"draft": "from-server"}', wrapper)
        self.assertIn('if(storage===null)', wrapper)
        with self.assertRaises(ValueError): reports.wrapper_report(self.fid, self.token, [])
        result = self.render('<script type="text/plain">content to display only</script>')
        self.assertIn('<script type="text/plain">content to display only</script>', result)

    def test_view_pins_report_hash_and_render_url_version(self):
        old = self.render('<h1>Old</h1>')
        old_hash = hashlib.sha256(self.path.read_bytes()).hexdigest()
        wrapper = reports.wrapper_report(self.fid, self.token, {'draft':'old'}, old_hash)
        self.path.write_text('<h1>New</h1>', encoding='utf-8')
        new_hash = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.assertNotEqual(old_hash, new_hash)
        rendered = reports.render_report(self.path,self.root,self.fid,self.token)
        self.assertIn(new_hash, rendered)
        self.assertIn('&amp;version=' + old_hash, wrapper)
        self.assertIn('let hash="' + old_hash + '"', wrapper)
        self.assertIn('if(hash&&hash!==m.hash){inner.hidden=true;', wrapper)
        self.assertIn("kind:'stale'", wrapper)
        with self.assertRaises(ValueError): reports.wrapper_report(self.fid,self.token,{},'not-a-sha256')

    def test_selfclosing_svg_shapes_keep_following_labels_as_siblings(self):
        result = self.render('<svg viewBox="0 0 400 120"><rect x="0" y="0" width="120" height="90"/><text x="10" y="30">Agora</text><path d="M130 45L170 45"/><text x="180" y="30">Resultado</text></svg>')
        self.assertIn('<rect x="0" y="0" width="120" height="90"></rect><text',result)
        self.assertIn('<path d="M130 45L170 45"></path><text',result)
        self.assertIn('>Agora</text>',result)
        self.assertIn('>Resultado</text>',result)

    def test_report_limit_is_independent_from_additional_resources(self):
        self.assertEqual(64_000_000,reports.MAX_REPORT)
        self.assertEqual(8_000_000,reports.MAX_RESOURCE)
        self.assertEqual(40_000_000,reports.MAX_BUNDLE)
        # Lower the resource budget: the HTML's own bytes must not spend it.
        self.put('00_PARA-VOCE/fixture.js','window.fixtureWorks=true;')
        with patch.object(reports,'MAX_BUNDLE',100):
            result=self.render('<p>'+('source-html '*100)+'</p><script src="../fixture.js"></script>')
        self.assertIn('window.fixtureWorks=true;',result)

    def test_all_sources_private_aliases_are_rejected_for_scripts_and_links(self):
        for folder in ['private','privado','privados','privadas','credenciais','secrets','credentials','__pycache__']:
            with self.subTest(folder=folder):
                private = self.put('00_PARA-VOCE/'+folder+'/secret.js','window.private_fixture_secret=true;')
                result = self.render('<script src="../'+folder+'/secret.js"></script><a href="../'+folder+'/secret.js">Secret</a>')
                self.assertNotIn('window.private_fixture_secret', result)
                self.assertNotIn('data-mb-local=', result)
                with self.assertRaises(ValueError): reports.confined_file(private,self.root)

    @unittest.skipUnless(importlib.util.find_spec('PySide6'), 'Use the native desktop interpreter for the Chromium probe.')
    def test_native_chromium_scripts_restore_feedback_and_network_confinement(self):
        # This is a local synthetic document, never a real session or vendor URL.
        import json
        import threading
        import time
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtCore import QTimer, QUrl
        from PySide6.QtWidgets import QApplication
        from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
        from PySide6.QtWebEngineWidgets import QWebEngineView
        observed = {'leaks': 0, 'messages': []}
        owner = self
        report = '''<html><head></head><body><button id="dr-finalizar">Finalizar</button><button id="dr-enviar">Enviar</button><svg viewBox="0 0 400 120"><rect x="0" y="0" width="120" height="90"/><text id="svg_label" x="10" y="30">Agora</text><path d="M130 45L170 45"/><text id="svg_result" x="180" y="30">Resultado</text></svg><script>
        const probe={kind:'decisions',respostas:{restored:localStorage.getItem('draft')==='preserved',parentDenied:false,fetchDenied:false,domReady:false,svgLabels:false},notas:[]};
        const svgLabel=document.getElementById('svg_label'),svgResult=document.getElementById('svg_result');probe.respostas.svgLabels=svgLabel.parentElement.tagName==='svg'&&svgResult.parentElement.tagName==='svg'&&svgLabel.getBBox().width>0&&svgResult.getBBox().width>0;
        document.addEventListener('DOMContentLoaded',()=>{probe.respostas.domReady=true;});
        try{parent.document.body.innerHTML;}catch{probe.respostas.parentDenied=true;}
        localStorage.setItem('newdraft','human-written');
        CursorFerramentas={iniciar:o=>({notas:()=>[{texto:'fixture note'}],note:()=>o.aoSalvarNota({texto:'fixture note'})})};
        const cursor=CursorFerramentas.iniciar({chave:'fixture'});cursor.note();
        DecisoesRespondiveis={iniciar:()=>({respostas:()=>probe.respostas,resumoTexto:()=> 'Fixture decision'})};DecisoesRespondiveis.iniciar({});
        fetch('/leak').catch(()=>{probe.respostas.fetchDenied=true;document.getElementById('dr-finalizar').click();setTimeout(()=>document.getElementById('dr-enviar').click(),30);});
        const image=new Image();image.src=location.origin+'/leak-image';
        const form=document.createElement('form');form.action='/leak-post';form.method='POST';document.body.append(form);form.submit();
        </script></body></html>'''
        self.path.write_text(report, encoding='utf-8')
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        rendered = reports.render_report(self.path, self.root, self.fid, self.token)
        class Fixture(BaseHTTPRequestHandler):
            def do_GET(server):
                headers = {}
                if server.path == '/':
                    headers = {'Content-Security-Policy': "default-src 'none'; script-src 'unsafe-inline'; frame-src 'self'"}
                    key = 'megabrain-report:' + owner.fid + ':' + digest
                    body = '<script>window.results=[];sessionStorage.setItem('+json.dumps(key)+',JSON.stringify({draft:"preserved"}));addEventListener("message",e=>{if(e.data?.channel==="megabrain-report")results.push(e.data)})</script><iframe sandbox="allow-scripts allow-same-origin" src="/viewer"></iframe><iframe id="stale" sandbox="allow-scripts allow-same-origin" src="/stale"></iframe>'
                elif server.path == '/viewer':
                    headers = reports.view_headers; body = reports.wrapper_report(owner.fid, owner.token, None, digest)
                elif server.path == '/stale':
                    headers = reports.view_headers; body = reports.wrapper_report(owner.fid, owner.token, {'draft':'must-not-restore'},'0'*64)
                elif server.path.startswith('/api/reports/'):
                    headers = reports.render_headers; body = rendered
                else:
                    observed['leaks'] += 1; body = 'unexpected network'
                server.send_response(200);server.send_header('Content-Type','text/html; charset=utf-8')
                for k,v in headers.items():server.send_header(k,v)
                server.end_headers();server.wfile.write(body.encode())
            def do_POST(server):
                observed['leaks'] += 1;server.send_response(204);server.end_headers()
            def log_message(self,*args): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Fixture)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        app = QApplication.instance() or QApplication([])
        view = QWebEngineView(); profile = QWebEngineProfile(view); page = QWebEnginePage(profile, view)
        view.setPage(page); view.resize(390,700)
        deadline=time.monotonic()+10
        def collect():
            def done(value):
                data=json.loads(value or '{}');observed['messages']=data.get('messages',[]);observed['stale_notice']=data.get('stale_notice')
                if any(m.get('kind')=='feedback' and m.get('payload',{}).get('kind')=='decisions' for m in observed['messages']) and observed['stale_notice'] or time.monotonic()>=deadline:app.quit()
                else:QTimer.singleShot(200,collect)
            page.runJavaScript('JSON.stringify({messages:window.results||[],stale_notice:document.getElementById("stale")?.contentDocument?.getElementById("report-error")?.textContent})', done)
        QTimer.singleShot(500, collect)
        QTimer.singleShot(12000, app.quit)
        view.load(QUrl('http://127.0.0.1:'+str(server.server_port)+'/'));app.exec()
        server.shutdown();server.server_close();view.close()
        decisions = [m['payload'] for m in observed['messages'] if m['kind']=='feedback' and m['payload'].get('kind')=='decisions']
        self.assertTrue(decisions, observed)
        self.assertTrue(decisions[-1]['respostas']['restored'], observed)
        self.assertTrue(decisions[-1]['respostas']['parentDenied'], observed)
        self.assertTrue(decisions[-1]['respostas']['fetchDenied'], observed)
        self.assertTrue(decisions[-1]['respostas']['domReady'], observed)
        self.assertTrue(decisions[-1]['respostas']['svgLabels'], observed)
        self.assertTrue(any(m['kind']=='feedback' and m['payload'].get('kind')=='notes' for m in observed['messages']), observed)
        self.assertEqual(0, observed['leaks'], observed)
        self.assertTrue(all(m['hash']==digest and m['token']==self.token for m in observed['messages'] if m['kind']!='stale'))
        self.assertTrue(any(m['kind']=='stale' and m['hash']=='0'*64 for m in observed['messages']), observed)
        self.assertIn('Reabra o resultado', observed['stale_notice'])
        self.assertEqual(1,len(decisions),observed)


if __name__ == '__main__': unittest.main()
