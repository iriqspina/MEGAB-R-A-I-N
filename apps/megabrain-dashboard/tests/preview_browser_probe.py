"""Independent Qt/Chromium containment probe using synthetic local HTTP fixtures.

Run with the desktop's PySide6 interpreter. No real sessions, project content,
vendor models, internet endpoint or generated user code is involved.
"""
import json
import hashlib
import os
from pathlib import Path
import sys
import threading
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from central_artifacts import preview_wrapper,PREVIEW_WRAPPER_HEADERS,RENDER_HEADERS
from PySide6.QtCore import QTimer,QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import QWebEnginePage,QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView

baseline='--baseline-no-forms' in sys.argv
state={'leaks':0,'external_posts':0,'same_origin_posts':0,'authenticated_render':False,'violations':[]}
class Sink(BaseHTTPRequestHandler):
    def do_GET(self):
        state['leaks']+=1;self.send_response(204);self.end_headers()
    def do_POST(self):
        state['leaks']+=1;state['external_posts']+=1;self.send_response(204);self.end_headers()
    def log_message(self,*args):pass
sink=ThreadingHTTPServer(('127.0.0.1',0),Sink)
threading.Thread(target=sink.serve_forever,daemon=True).start()
destination='http://127.0.0.1:'+str(sink.server_port)
jid='a'*32
probe_ids={'b'*24:'general','c'*24:'external_post','d'*24:'same_origin_post'}
class Fixture(BaseHTTPRequestHandler):
    def do_GET(self):
        headers={};status=200
        aid=self.path.rsplit('/',1)[-1];mode=probe_ids.get(aid)
        if self.path=='/':
            headers={'Set-Cookie':'mb_probe=synthetic; HttpOnly; SameSite=Strict; Path=/',
                     'Content-Security-Policy':"default-src 'none'; script-src 'unsafe-inline'; frame-src 'self' http:; style-src 'unsafe-inline'"}
            permissions='allow-scripts allow-same-origin'+('' if baseline else ' allow-forms')
            body='<script>window.fixture=[];window.topSecret="unreadable";addEventListener("message",e=>{if(e.data&&e.data.probe)fixture.push({origin:e.origin,...e.data})})</script>'+''.join('<iframe sandbox="'+permissions+'" src="/api/jobs/'+jid+'/preview/'+identifier+'"></iframe>' for identifier in probe_ids)
        elif mode and self.path.endswith('/preview/'+aid):headers=PREVIEW_WRAPPER_HEADERS;body=preview_wrapper(jid,aid)
        elif mode and self.path.endswith('/render/'+aid):
            state['authenticated_render']='mb_probe=synthetic' in self.headers.get('Cookie','')
            if not state['authenticated_render']:status=401;body='Missing fixture cookie'
            else:
                headers=RENDER_HEADERS
                body='''<button id="test">Click</button><form id="local"><input name="name" value="Synthetic item" required><button type="submit">Add item</button></form><output id="count">0</output><script>
const r={probe:true,mode:PROBE_MODE,inline_js:true,click:false,parent_denied:false,top_denied:false,cookie_denied:false,fetch_denied:false,local_submit:false,local_count:0,external_post_attempted:false,same_origin_post_attempted:false};
document.querySelector('#test').onclick=()=>{r.click=true};document.querySelector('#test').click();
document.querySelector('#local').addEventListener('submit',e=>{e.preventDefault();r.local_submit=true;r.local_count++;document.querySelector('#count').textContent=String(r.local_count)});
document.querySelector('#local button').click();
try{parent.document.body.innerHTML}catch(e){r.parent_denied=true}
try{top.topSecret}catch(e){r.top_denied=true}
try{document.cookie}catch(e){r.cookie_denied=true}
if(r.mode==='external_post'){const external=document.createElement('form');external.method='POST';external.action='''+json.dumps(destination+'/form-post')+''';document.body.append(external);r.external_post_attempted=true;top.postMessage(r,'*');external.submit()}
if(r.mode==='same_origin_post'){const same=document.createElement('form');same.method='POST';same.action='/api/probe-post';document.body.append(same);r.same_origin_post_attempted=true;top.postMessage(r,'*');same.submit()}
fetch('''+json.dumps(destination+'/fetch')+''').then(()=>{r.fetch_denied=false}).catch(()=>{r.fetch_denied=true}).finally(()=>{top.postMessage(r,'*')});
const img=new Image();img.src='''+json.dumps(destination+'/image')+''';
if(r.mode==='general')setTimeout(()=>{top.postMessage({...r,navigation_attempted:true},'*');location.href='''+json.dumps(destination+'/navigation')+'''},600);
</script>'''
                body=body.replace('PROBE_MODE',json.dumps(mode))
        else:status=404;body='fixture not found'
        if baseline:
            headers={key:value.replace(' allow-forms','') for key,value in headers.items()}
            body=body.replace(' allow-forms','')
        if '/api/' in self.path and 'mb_probe=synthetic' not in self.headers.get('Cookie',''):status=401;body='Missing fixture cookie'
        self.send_response(status);self.send_header('Content-Type','text/html; charset=utf-8')
        for key,value in headers.items():self.send_header(key,value)
        self.end_headers();self.wfile.write(body.encode())
    def do_POST(self):
        state['same_origin_posts']+=1;self.send_response(204);self.end_headers()
    def log_message(self,*args):pass
fixture=ThreadingHTTPServer(('127.0.0.1',0),Fixture)
threading.Thread(target=fixture.serve_forever,daemon=True).start()
app=QApplication([])
class Page(QWebEnginePage):
    def javaScriptConsoleMessage(self,level,message,line,source):
        if 'Content Security Policy' in message or 'violates' in message or 'Refused' in message:
            state['violations'].append(message[:400])
view=QWebEngineView();profile=QWebEngineProfile(view);page=Page(profile,view);view.setPage(page)
view.resize(600,600)
def collect():
    def done(value):
        try:reports=json.loads(value) if isinstance(value,str) else value
        except ValueError:reports=[]
        reports=reports if isinstance(reports,list) else []
        general=[r for r in reports if r.get('mode')=='general']
        observed=general[-1] if general else {}
        checks={name:observed.get(name) is True for name in ('inline_js','click','parent_denied','top_denied','cookie_denied','fetch_denied','navigation_attempted')}
        for name in ('external_post_attempted','same_origin_post_attempted'):
            checks[name]=any(r.get(name) is True for r in reports)
        checks.update(opaque_origin=observed.get('origin')=='null',authenticated_render=state['authenticated_render'],external_requests_blocked=state['leaks']==0,
            local_preventdefault_form_works=observed.get('local_submit') is True and observed.get('local_count')==1,
            external_post_blocked=state['external_posts']==0,same_origin_post_blocked=state['same_origin_posts']==0)
        result={'at':datetime.now(timezone.utc).isoformat(),'engine':'Qt QWebEngine/Chromium','synthetic_local_fixtures_only':True,
                'all_pass':all(checks.values()),'checks':checks,'baseline_no_forms':baseline,'local_submit_count':observed.get('local_count'),
                'sink_requests':state['leaks'],'external_posts':state['external_posts'],'same_origin_posts':state['same_origin_posts'],
                'csp_violations_observed':len(state['violations']),'synthetic_console':state['violations'],
                'source_sha256':{str(p.relative_to(APP)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [APP/'central_artifacts.py',Path(__file__)]}}
        name='preview-browser-forms-before.json' if baseline else 'preview-browser-forms-after.json'
        out=APP.parents[1]/'evidence/261011_app-megabrain'/name
        out.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
        fixture.shutdown();sink.shutdown();app.exit(0 if result['all_pass'] else 1)
    page.runJavaScript('JSON.stringify(window.fixture || [])',done)
view.load(QUrl('http://127.0.0.1:'+str(fixture.server_port)+'/'))
QTimer.singleShot(4000,collect);QTimer.singleShot(15000,lambda:app.exit(2))
raise SystemExit(app.exec())
