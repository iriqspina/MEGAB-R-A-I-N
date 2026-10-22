"""No models, real database writes or external processes."""
import json
from pathlib import Path
from unittest import mock
from test_central_bridge import Base, FakeSources
import central_bridge as bridge
from central_store import Store, Conflict, ident
from central_project_control import read, save, check, check_path

class ProjectControlTests(Base):
    def setUp(self):
        super().setUp()
        self.store=Store(self.central/'apps/megabrain-dashboard/data/central.sqlite3')
        self.pid=ident(self.projeto.resolve())
        self.launches=[]
        self.p=bridge.Ponte(self.store,FakeSources(),lancar=lambda *x:self.launches.append(x),central=self.central)
    def mode(self, mode):
        return save(self.store,self.pid,read(self.store,self.pid)['revision'],mode)
    def comment(self):
        return self.store.add('comments',self.pid,dict(text='test',target='file:x',status='Recebido'))
    def test_revision_persistence_isolation_and_explicit_resume(self):
        first=self.mode('aguardando')
        with self.assertRaises(Conflict):save(self.store,self.pid,first['revision']-1,'ativo')
        fresh=Store(self.store.path)
        self.assertEqual(read(fresh,self.pid)['data']['modo'],'aguardando')
        check(fresh,'different-project')
        with self.assertRaises(ValueError):check_path(self.projeto,self.central)
        check_path(self.projeto,self.central,etapa=True)
        self.mode('pausado')
        with self.assertRaises(ValueError):check_path(self.projeto,self.central,etapa=True)
        self.mode('ativo');check_path(self.projeto,self.central)
    def test_wait_blocks_timer_manual_order_and_complement(self):
        c=self.comment();self.p.receber(self.pid,self.projeto,c)
        for key in self.p._pendentes():
            d=self.store.get(key,{});self.store.put(key,d['revision'],dict(d['data'],lancar_apos=0))
        clock=self.store.get('bridge-clock:'+self.pid,{})
        self.store.put('bridge-clock:'+self.pid,clock['revision'],dict(clock['data'],mudou_em=0))
        self.mode('aguardando');self.p.tick();self.p.tick()
        self.assertEqual(self.launches,[])
        with self.assertRaises(ValueError):self.p.enviar_agora(self.pid,self.projeto,[c['id']])
        with self.assertRaises(ValueError):self.ordem()
        with self.assertRaises(ValueError):self.p._continuar(self.pid,{},[c])
        self.assertEqual(read(self.store,self.pid)['data']['modo'],'aguardando')
        self.mode('ativo');self.p.tick();self.assertEqual(len(self.launches),1)
    def test_pause_blocks_child_and_all_launch_entrypoints(self):
        order=self.ordem();directory=Path(order['dir']);node=directory/'nos/n0'
        self.mode('pausado')
        with self.assertRaises(ValueError):bridge.despachar(directory,'n0','worker',None,'test','test',central=self.central,lancador=lambda *a:self.fail('launched'))
        for fn,args in [(bridge.iniciar_planejador,(directory,)),(bridge.lancar_segundo_plano,(node,)),(bridge.lancar_janela,(node,)),(bridge.supervisionar,(node,))]:
            with self.subTest(fn=fn.__name__),self.assertRaises(ValueError):fn(*args)
        self.assertFalse((directory/'PARAR').exists())
    def test_wait_blocks_new_child_and_planner_resume(self):
        order=self.ordem();directory=Path(order['dir'])
        self.mode('aguardando')
        with self.assertRaises(ValueError):bridge.despachar(directory,'n0','worker',None,'test','test',central=self.central,lancador=lambda *a:self.launches.append(a))
        self.assertEqual(len(self.launches),0)
        with self.assertRaises(ValueError):bridge.iniciar_planejador(directory,lancador=lambda *a:self.fail('resumed'))
    def test_returns_are_reconciled_during_pause_and_do_not_resume(self):
        c=self.comment();out=self.p.enviar_agora(self.pid,self.projeto,[c['id']],vendor='gpt')
        self.mode('pausado')
        bridge.concluir(out['dir'],'parcial','Finished existing work',[],[])
        self.p.tick()
        comment=self.store.listing('comments',self.pid,include_resolved=True)[0]
        self.assertIn('Finished existing work',comment['correction'])
        self.assertEqual(read(self.store,self.pid)['data']['modo'],'pausado')
        self.assertEqual(len(self.launches),1)
    def test_auto_setting_never_clears_pause(self):
        self.mode('pausado');cfg=self.p.config(self.pid)
        self.p.salvar_config(self.pid,cfg['revision'],dict(cfg['data'],auto=True))
        with self.assertRaises(ValueError):check(self.store,self.pid)
    def test_invalid_mode_does_not_write(self):
        with self.assertRaises(ValueError):self.mode('timer')
        self.assertEqual(read(self.store,self.pid)['revision'],0)
