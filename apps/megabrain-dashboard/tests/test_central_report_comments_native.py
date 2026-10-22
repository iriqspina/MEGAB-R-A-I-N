"""Native Chromium + real ASGI routes; synthetic sources, auth and SQLite only.

QTest clicks/type target the opaque child through the native view. The parent is
a minimal receipt host, not a claim that all React flows were exercised here.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(APP), str(APP/'runtime-packages'), str(APP/'tests')]
import test_central_security as harness
from central_store import Store

EVIDENCE = APP.parents[1]/'evidence/261014_comentarios-central/prototipos/v3'


@unittest.skipUnless(importlib.util.find_spec('PySide6'), 'Run with the native Qt interpreter.')
class NativePrototypeComments(unittest.TestCase):
    def test_real_pointer_comments_draft_restore_legacy_and_version_isolation(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--disable-gpu --disable-gpu-compositing --use-angle=swiftshader --enable-unsafe-swiftshader')
        from PySide6.QtCore import QPoint, Qt, QUrl
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
        from PySide6.QtWebEngineWidgets import QWebEngineView
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        with patch.object(harness, 'TEMP_BASE', EVIDENCE/'fixtures'):
            fixture=harness.CentralSecurityTests();fixture.setUp()
        auth=fixture.local_login()
        source='''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>html,body{margin:0;background:#f4f1e8;color:#20212b;font:16px system-ui}main{padding:24px}button{padding:10px}#target{margin-top:20px;padding:24px;border:2px solid #7552ca;min-height:80px}</style></head><body><main><h1>Protótipo sintético</h1><button id="normal" onclick="window.normalClicks=(window.normalClicks||0)+1">Abrir card</button><section id="target" data-cf-ancora="fixture-card"><h2>Card da atividade</h2><p>Âncora real para uma nota de teste.</p></section></main></body></html>'''
        self.assertNotIn('CursorFerramentas',source)
        paths={};fids={};digests={};tokens={}
        for name,extra in [('newA',''),('newB',''),('legacyDom',"document.addEventListener('DOMContentLoaded',()=>{window.legacy=CursorFerramentas.iniciar({modo:'local',chave:'legacy-dom'});});"),('legacyLoad',"window.addEventListener('load',()=>{window.legacy=CursorFerramentas.iniciar({modo:'local',chave:'legacy-load'});});"),('legacyAsync',"setTimeout(()=>{window.legacy=CursorFerramentas.iniciar({modo:'local',chave:'legacy-async'});},120);"),('bar',''),('throws',"CursorFerramentas={iniciar(){throw new Error('synthetic initializer failure');}};"),('invalidApi',"CursorFerramentas={iniciar(){return {};}};"),('lateBar',"setTimeout(()=>{const b=document.createElement('div');b.className='dr-barra';b.style.cssText='position:fixed;bottom:0;left:0;width:100%;height:64px;background:#223;color:white';b.textContent='Barra criada depois';document.body.appendChild(b);},300);")]:
            path=fixture.project/'00_PARA-VOCE'/f'{name}.html'
            text=source if not extra else source.replace('</body>',f'<script>{extra}</script></body>')
            if name=='bar':text=text.replace('</body>','<div class="dr-barra" style="position:fixed;bottom:0;left:0;width:100%;height:64px;background:#223;color:white">Decisões respondíveis sintéticas</div></body>')
            path.write_text(text,encoding='utf-8')
            paths[name]=path;fids[name]=fixture.sources.index_file(path,fixture.project)['id'];digests[name]=hashlib.sha256(path.read_bytes()).hexdigest();tokens[name]='synthetic_'+name+'_ticket_261014'
        originals={name:p.read_bytes() for name,p in paths.items()}
        receipts=[];unexpected=[]
        frame_markup=''.join(f'<iframe name="{name}" sandbox="allow-scripts allow-same-origin allow-forms" src="/api/reports/{fid}/view?ticket={tokens[name]}"></iframe>'for name,fid in fids.items())
        identities=json.dumps({fid:tokens[name]for name,fid in fids.items()})
        parent='''<!doctype html><html><head><meta charset="utf-8"><link rel="icon" href="data:,"><style>body{margin:0;display:flex;flex-wrap:wrap}iframe{width:390px;height:480px;border:0}#receipt{padding:12px}button{padding:8px}</style></head><body>'''+frame_markup+'''<div id="receipt"><button id="save">Salvar no projeto</button><span id="notice">Sem feedback preparado</span></div><script>
        window.receipts=[];window.pending={};window.draftWrites=[];window.draftQueue=Promise.resolve();const identities='''+identities+''';
        addEventListener('message',e=>{const m=e.data;if(e.origin!==location.origin||!m||m.channel!=='megabrain-report'||identities[m.fid]!==m.token||!Array.from(document.querySelectorAll('iframe')).some(f=>f.contentWindow===e.source))return;receipts.push(m);
          if(m.kind==='draft'){draftQueue=draftQueue.then(()=>fetch('/api/reports/'+m.fid+'/draft',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({hash:m.hash,storage:m.payload.storage})}));draftWrites.push(draftQueue);}
          if(m.kind==='feedback'){const old=pending[m.fid]?.payload,incoming=m.payload;if(incoming.kind==='notes'){const notes=[...(old?.notas||[]),...(incoming.notas||[])];pending[m.fid]={...m,payload:{...old,...incoming,kind:old?.kind==='decisions'?'decisions':'notes',notas:notes.filter((v,i)=>!v.id||!notes.slice(i+1).some(n=>n.id===v.id))}};}else pending[m.fid]=m;document.getElementById('notice').textContent='Feedback preparado; ainda não enviado';}
        });
        document.getElementById('save').onclick=async()=>{await Promise.all(draftWrites);for(const m of Object.values(pending)){const r=await fetch('/api/reports/'+m.fid+'/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({hash:m.hash,feedback:m.payload,note:''})});if(r.ok)document.getElementById('notice').textContent='Recebido, aguardando correção';}};
        </script></body></html>'''
        class Handler(BaseHTTPRequestHandler):
            def route(server):
                if server.path=='/':status=200;headers={'content-type':'text/html; charset=utf-8'};body=parent.encode()
                elif server.path.startswith('/api/reports/'):
                    length=int(server.headers.get('content-length','0'));raw=server.rfile.read(length) if length else None
                    status,headers,body=fixture.request(fixture.local,server.path,method=server.command,body=raw,headers=auth)
                    receipts.append(dict(method=server.command,path=server.path,status=status))
                else:unexpected.append(server.path);status=404;headers={};body=b'Unavailable fixture route'
                server.send_response(status)
                for key,value in headers.items():
                    if key not in {'content-length','transfer-encoding','connection'}:server.send_header(key,value)
                server.send_header('Content-Length',str(len(body)));server.end_headers();server.wfile.write(body)
            do_GET=route;do_POST=route
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        app=QApplication.instance()or QApplication([]);view=QWebEngineView();profile=QWebEngineProfile(view);page=QWebEnginePage(profile,view);view.setPage(page);view.resize(1440,1000);view.show()
        def wait(test,timeout=8):
            end=time.monotonic()+timeout
            while time.monotonic()<end:
                app.processEvents()
                if test():return
                time.sleep(.01)
            raise AssertionError('Native fixture timed out')
        def js(frame,code):
            box=[];frame.runJavaScript(code,0,lambda value:box.append(value));wait(lambda:bool(box));return box[0]
        def child(name):
            outer=next((f for f in page.mainFrame().children()if f.htmlName()==name),None)
            return outer.children()[0]if outer and outer.children()else None
        def value(name,code):return js(child(name),'JSON.stringify('+code+')')
        def rect(name,selector):
            return json.loads(value(name,"(()=>{const r=document.querySelector("+json.dumps(selector)+").getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,w:r.width,h:r.height}})()"))
        def click(name,selector):
            r=rect(name,selector)
            outer=json.loads(js(page.mainFrame(),"JSON.stringify((()=>{const r=document.querySelector('iframe[name="+name+"]').getBoundingClientRect();return {x:r.x,y:r.y}})())"))
            QTest.mouseClick(view.focusProxy(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(round(outer['x']+r['x']),round(outer['y']+r['y'])));QTest.qWait(80);app.processEvents()
        checks={};note_text='Corrigir a atividade sem apagar minha nota 261014.'
        try:
            view.load(QUrl(f'http://127.0.0.1:{server.server_port}/'))
            wait(lambda:len(receipts)>=10 and all(child(name)is not None for name in fids))
            wait(lambda:json.loads(value('newA',"Boolean(document.querySelector('.mb-report-tools button'))")))
            time.sleep(.2);app.processEvents()
            for name in ('legacyDom','legacyLoad','legacyAsync'):
                wait(lambda n=name:json.loads(value(n,"Boolean(window.legacy)")))
                state=json.loads(value(name,"({chips:document.querySelectorAll('.cf-chip-btn').length,fallback:document.querySelectorAll('.mb-report-tools').length,version:CursorFerramentas.versao})"))
                self.assertEqual({'chips':1,'fallback':0,'version':'1.5'},state);checks[name]=state
            failure_messages=json.loads(js(page.mainFrame(),'JSON.stringify(window.receipts)'))
            self.assertTrue(any(m['fid']==fids['throws']and m['kind']=='loaded'and m['payload'].get('comments_available')is False for m in failure_messages))
            self.assertIn('Comentários indisponíveis',json.loads(value('throws',"document.querySelector('[role=alert]').textContent")));checks['initializer_failure_still_loaded_and_visible']=True
            self.assertTrue(any(m['fid']==fids['invalidApi']and m['kind']=='loaded'and m['payload'].get('comments_available')is False for m in failure_messages))
            self.assertIn('Comentários indisponíveis',json.loads(value('invalidApi',"document.querySelector('[role=alert]').textContent")));checks['unsupported_cursor_warns_instead_of_dead_button']=True
            wait(lambda:json.loads(value('lateBar',"Boolean(document.querySelector('.dr-barra'))")))
            late=json.loads(value('lateBar',"(()=>{const t=document.querySelector('.mb-report-tools').getBoundingClientRect(),b=document.querySelector('.dr-barra').getBoundingClientRect();return {bottom:t.bottom,barTop:b.top}})()"))
            self.assertLess(late['bottom'],late['barTop']);checks['late_decision_bar_observed']=late
            click('newA','#normal');self.assertEqual(1,json.loads(value('newA','window.normalClicks')));checks['normal_interaction']=True
            click('newA','.mb-report-tools button:first-child');self.assertEqual('true',json.loads(value('newA',"document.querySelector('.mb-report-tools button:first-child').getAttribute('aria-pressed')")))
            click('newA','#target');wait(lambda:json.loads(value('newA',"Boolean(document.querySelector('.cf-editor textarea'))")))
            click('newA','.cf-editor textarea');QTest.qWait(40)
            wait(lambda:json.loads(value('newA',"document.activeElement===document.querySelector('.cf-editor textarea')")))
            QTest.keyClicks(view.focusProxy(),note_text);app.processEvents()
            wait(lambda:json.loads(value('newA',"document.querySelector('.cf-editor textarea').value"))==note_text)
            draft_key='report-draft:'+fids['newA']+':'+digests['newA']
            wait(lambda:note_text in json.dumps(fixture.store.get(draft_key,{})['data']))
            self.assertEqual([],fixture.store.listing('comments',fixture.pid));checks['incomplete_draft_without_submission']=True
            # Close the synthetic frame with a draft, reopen through the real view route.
            js(page.mainFrame(),"document.querySelector('iframe[name=newA]').remove();undefined")
            js(page.mainFrame(),"(()=>{const f=document.createElement('iframe');f.name='newA';f.setAttribute('sandbox','allow-scripts allow-same-origin allow-forms');f.src="+json.dumps('/api/reports/'+fids['newA']+'/view?ticket='+tokens['newA'])+";document.body.prepend(f);})()")
            wait(lambda:child('newA')is not None and json.loads(value('newA',"Boolean(document.querySelector('.cf-pino'))")))
            click('newA','.cf-pino');wait(lambda:json.loads(value('newA',"Boolean(document.querySelector('.cf-editor textarea'))")))
            self.assertEqual(note_text,json.loads(value('newA',"document.querySelector('.cf-editor textarea').value")));checks['incomplete_draft_restored_after_close']=True
            click('newA','.cf-salvar')
            wait(lambda:bool(json.loads(js(page.mainFrame(),'JSON.stringify(window.pending)'))))
            self.assertEqual([],fixture.store.listing('comments',fixture.pid))
            payload=json.loads(js(page.mainFrame(),"JSON.stringify(window.pending["+json.dumps(fids['newA'])+"])"))
            note=payload['payload']['notas'][0];self.assertEqual(note_text,note['texto']);self.assertEqual('#target',note['ancora']['base']);self.assertTrue(all(isinstance(i,int)for i in note['ancora']['idx']));self.assertIn('Card da atividade',note['onde']);self.assertGreater(note['px'],0);self.assertGreater(note['py'],0)
            self.assertNotEqual(0,note['ox']);self.assertNotEqual(0,note['oy']);checks['feedback_anchor_geometry']=note
            self.assertEqual(digests['newA'],payload['hash']);self.assertEqual(tokens['newA'],payload['token'])
            self.assertFalse(json.loads(value('newB',"Boolean(document.querySelector('.cf-pino'))")));self.assertEqual({},fixture.store.get('report-draft:'+fids['newB']+':'+digests['newB'],{})['data']);checks['separate_frames']=True
            # The real host merges note events by ID (ReportFrame.tsx). Preserve
            # two saved notes and deduplicate a repeat before explicit submission.
            click('newA','.mb-report-tools button:first-child');click('newA','#target p');wait(lambda:json.loads(value('newA',"Boolean(document.querySelector('.cf-editor textarea'))")))
            self.assertEqual('',json.loads(value('newA',"document.querySelector('.cf-editor textarea').value")))
            click('newA','.cf-editor textarea');QTest.keyClicks(view.focusProxy(),'Second saved note remains in the receipt.');QTest.qWait(80);click('newA','.cf-salvar')
            wait(lambda:len(json.loads(js(page.mainFrame(),"JSON.stringify(window.pending["+json.dumps(fids['newA'])+"].payload.notas)")))==2)
            second= json.loads(js(page.mainFrame(),"JSON.stringify(window.pending["+json.dumps(fids['newA'])+"])"))
            self.assertEqual(2,len(second['payload']['notas']));self.assertEqual(note_text,second['payload']['notas'][0]['texto'])
            js(child('newA'),"MegaBrainReport.saveFeedback("+json.dumps(dict(kind='notes',notas=[second['payload']['notas'][1]]))+ ")")
            QTest.qWait(80);self.assertEqual(2,len(json.loads(js(page.mainFrame(),"JSON.stringify(window.pending["+json.dumps(fids['newA'])+"].payload.notas)"))))
            checks['two_saved_notes_accumulated_deduplicated']=True
            before_normal=json.loads(value('newA','window.normalClicks||0'))
            click('newA','.mb-report-tools button:last-child');click('newA','#normal');self.assertEqual(before_normal+1,json.loads(value('newA','window.normalClicks')));checks['normal_interaction_after_comment']=True
            # The parent receipt explicitly saves; pins and drafts alone never create a comment.
            js(page.mainFrame(),"document.getElementById('save').click()")
            wait(lambda:len(fixture.store.listing('comments',fixture.pid))==1)
            stored=fixture.store.listing('comments',fixture.pid)[0];self.assertEqual(digests['newA'],stored['source_hash']);self.assertEqual(note,stored['feedback']['notas'][0]);self.assertEqual(2,len(stored['feedback']['notas']));checks['explicit_saved_receipt']=stored['status']
            # Count behavior, not only a chip: a late legacy initializer must
            # produce one editor, one pin and one event for one real note.
            click('legacyAsync','.cf-chip-btn');QTest.qWait(300);click('legacyAsync','[data-cf-item=comentar]');click('legacyAsync','#target')
            wait(lambda:json.loads(value('legacyAsync',"document.querySelectorAll('.cf-editor').length"))==1)
            click('legacyAsync','.cf-editor textarea');QTest.keyClicks(view.focusProxy(),'One legacy note and one callback.');QTest.qWait(80);click('legacyAsync','.cf-salvar')
            messages=json.loads(js(page.mainFrame(),'JSON.stringify(window.receipts)'));legacy_feedback=[m for m in messages if m['fid']==fids['legacyAsync']and m['kind']=='feedback']
            self.assertEqual(1,len(legacy_feedback));self.assertEqual(1,json.loads(value('legacyAsync',"document.querySelectorAll('.cf-pino').length")));self.assertEqual(0,json.loads(value('legacyAsync',"document.querySelectorAll('.cf-editor').length")));checks['legacy_async_one_editor_one_pin_one_feedback']=True
            # Resize both viewport and the fixed decision bar's height. The
            # controls stay visible and above the bar at 390 x 480.
            js(page.mainFrame(),"(()=>{const f=document.querySelector('iframe[name=bar]');f.style.width='500px';f.style.height='620px';})()")
            QTest.qWait(80);js(child('bar'),"document.querySelector('.dr-barra').style.height='104px'");QTest.qWait(80)
            js(page.mainFrame(),"(()=>{const f=document.querySelector('iframe[name=bar]');f.style.width='390px';f.style.height='480px';})()")
            QTest.qWait(100)
            placement=json.loads(value('bar',"(()=>{const t=document.querySelector('.mb-report-tools').getBoundingClientRect(),b=document.querySelector('.dr-barra').getBoundingClientRect();return {left:t.left,right:t.right,top:t.top,bottom:t.bottom,barTop:b.top,width:innerWidth,height:innerHeight}})()"))
            self.assertEqual(390,placement['width']);self.assertEqual(480,placement['height']);self.assertGreaterEqual(placement['top'],0);self.assertLessEqual(placement['right'],390);self.assertLess(placement['bottom'],placement['barTop']);checks['toolbar_resize_above_dynamic_decision_bar']=placement
            QTest.qWait(2800);view.grab().save(str(EVIDENCE/'261014_prototipo-fixture-1440.png'))
            view.resize(390,480);app.processEvents();QTest.qWait(80)
            box=json.loads(value('newA',"(()=>{const r=document.querySelector('.mb-report-tools').getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:innerWidth,height:innerHeight}})()"))
            self.assertGreaterEqual(box['left'],0);self.assertLessEqual(box['right'],box['width']);self.assertGreaterEqual(box['top'],0);self.assertLessEqual(box['bottom'],box['height']);checks['mobile_390_480_controls']=box
            view.grab().save(str(EVIDENCE/'261014_prototipo-fixture-390.png'))
            for name,path in paths.items():self.assertEqual(originals[name],path.read_bytes())
            checks['sources_unchanged']=True
            olddraft=fixture.store.get(draft_key,{})['data']
            paths['newA'].write_text(source.replace('Protótipo sintético','Versão nova sintética'),encoding='utf-8')
            # 261017 WP2: a versão antiga não renderiza mais (409), mas o
            # rascunho e o envio feitos nela chegam marcados como versão anterior.
            status,_,_=fixture.request(fixture.local,'/api/reports/'+fids['newA']+'/render?ticket='+tokens['newA']+'&version='+digests['newA'],headers=auth);self.assertEqual(409,status)
            status,_,_=fixture.request(fixture.local,'/api/reports/'+fids['newA']+'/feedback',method='POST',body={'hash':digests['newA'],'feedback':payload['payload']},headers=auth);self.assertEqual(200,status)
            self.assertEqual(olddraft,Store(fixture.store.path).get(draft_key,{})['data'])
            status,_,_=fixture.request(fixture.local,'/api/reports/'+fids['newA']+'/draft',method='POST',body={'hash':digests['newA'],'storage':olddraft.get('storage',{})},headers=auth);self.assertEqual(200,status)
            stale_draft=Store(fixture.store.path).get(draft_key,{})['data'];self.assertTrue(stale_draft['versao_anterior']);self.assertEqual(olddraft.get('storage'),stale_draft['storage']);checks['previous_version_accepted_and_marked']=True
            self.assertEqual([],unexpected);checks['unexpected_network']=unexpected
            (EVIDENCE/'261014_native-fixture-proof.json').write_text(json.dumps(dict(kind='Synthetic local HTTP + real ASGI route + native Qt pointer/typing; minimal receipt host, not full React',checks=checks,receipts=receipts),ensure_ascii=False,indent=2),encoding='utf-8')
        except Exception:
            debug=dict(receipts=receipts,checks=checks,drafts=fixture.store.get('report-draft:'+fids['newA']+':'+digests['newA'],{}))
            try:debug['child']=json.loads(value('newA',"({active:document.activeElement?.outerHTML,textarea:document.querySelector('.cf-editor textarea')?.value,tools:document.querySelector('.mb-report-tools')?.outerHTML})"))
            except Exception:pass
            (EVIDENCE/'261014_native-failure-debug.json').write_text(json.dumps(debug,ensure_ascii=False,indent=2),encoding='utf-8')
            raise
        finally:
            view.close();page.deleteLater();app.processEvents();server.shutdown();server.server_close();fixture.tearDown()


if __name__=='__main__':unittest.main()
