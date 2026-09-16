from pathlib import Path
import os,sys,json,tempfile,importlib.util,traceback
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QTWEBENGINE_CHROMIUM_FLAGS']='--disable-gpu'
sys.path.insert(0,str(ROOT/'apps/megabrain-dashboard'));sys.path.insert(0,str(ROOT/'bin'))
from PySide6.QtWidgets import QApplication,QMainWindow,QPushButton
from PySide6.QtCore import QTimer,Qt,QUrl
from PySide6.QtTest import QTest
from PySide6.QtGui import QDesktopServices,QFontDatabase,QFont
from PySide6.QtWebEngineCore import QWebEnginePage
from mb_entregas_registro import registrar
from mb_triagem import ler_config
import dashboard
fixture=Path(tempfile.mkdtemp(prefix='260916-native-',dir=ROOT/'.scratch')).resolve()
(fixture/'00_PARA-VOCE/tarefa').mkdir(parents=True);entry=fixture/'00_PARA-VOCE/tarefa/index.html';entry.write_text('<h1>Entrega de teste</h1>',encoding='utf-8')
registrar(fixture,{'id':'test','titulo':'Tarefa teste','tarefa':'Verificar navegação','sessao':'teste local','pasta':str(entry.parent),'arquivo':str(entry),'estado':'em_revisao','proxima_acao':'Abrir o documento'})
app=QApplication([])
# O plugin offscreen não enumera fontes do Windows; carregar a mesma fonte usada no app.
for name in ('segoeui.ttf','segoeuib.ttf'):
    font=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/name
    if font.exists():QFontDatabase.addApplicationFont(str(font))
app.setFont(QFont('Segoe UI',10));results=[]
def check(name,condition):results.append({'name':name,'pass':bool(condition)})
def stage1():
    try:
        w=next(x for x in app.topLevelWidgets() if isinstance(x,QMainWindow))
        w.grab().save(str(HERE/'app-nativo.png'))
        check('entrada no app',w.browser.url().toLocalFile().endswith('INICIO.html'))
        w.sensibilidade.setFocus();QTest.keyClick(w.sensibilidade,Qt.Key.Key_Down)
        check('controle grava preferencia real',ler_config(fixture)['sensibilidade']=='criteriosa')
        opened=[];original=QDesktopServices.openUrl
        QDesktopServices.openUrl=lambda u:opened.append(u.toLocalFile()) or True
        try:
            accepted=w.page.acceptNavigationRequest(QUrl.fromLocalFile(str(entry.parent)),QWebEnginePage.NavigationType.NavigationTypeLinkClicked,True)
            check('pasta encaminhada ao aplicativo do sistema',not accepted and len(opened)==1 and Path(opened[0]).resolve()==entry.parent)
        finally:QDesktopServices.openUrl=original
        w.browser.load(QUrl.fromLocalFile(str(entry)))
        QTimer.singleShot(400,lambda:stage2(w))
    except Exception:results.append({'name':'exception','pass':False,'error':traceback.format_exc()});finish()
def stage2(w):
    try:
        check('entrega abriu dentro do app',Path(w.browser.url().toLocalFile()).resolve()==entry)
        w.reload();check('timer preserva leitura',Path(w.browser.url().toLocalFile()).resolve()==entry)
        home=next(b for b in w.findChildren(QPushButton) if b.text()=='Início');QTest.mouseClick(home,Qt.MouseButton.LeftButton)
        QTimer.singleShot(400,lambda:stage3(w))
    except Exception:results.append({'name':'exception','pass':False,'error':traceback.format_exc()});finish()
def stage3(w):
    check('botao retorna ao inicio',w.browser.url().toLocalFile().endswith('INICIO.html'));w.close();finish()
def finish():
    (HERE/'ui-nativo.json').write_text(json.dumps({'pass':all(x['pass'] for x in results),'tests':results},ensure_ascii=False,indent=2),encoding='utf-8');app.quit()
QTimer.singleShot(1800,stage1);QTimer.singleShot(15000,lambda:(results.append({'name':'timeout','pass':False}),finish()))
sys.argv=['dashboard.py','--inicio','--project',str(fixture)];dashboard.main()
print(json.dumps(results,ensure_ascii=False,indent=2));sys.exit(0 if results and all(x['pass'] for x in results) else 1)
