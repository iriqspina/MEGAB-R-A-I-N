"""Human choices survive authenticated API transport; no model is launched."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

APP=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(APP),str(APP/'runtime-packages'),str(APP/'tests')]
import test_central_bridge as bridge_fixtures


class ChoiceApiTests(unittest.TestCase):
    setUp=bridge_fixtures.ApiTests.setUp
    tearDown=bridge_fixtures.ApiTests.tearDown
    call=bridge_fixtures.ApiTests.call

    def route(self):
        return dict(vendor='gpt',modelo='gpt-6.1-sol',effort='xhigh')

    def report_ready(self):
        self.fixture.request(self.app,f'/api/reports/{self.fid}/view?ticket=t_bridge_choices_261020',headers=self.auth)
        return hashlib.sha256(self.fixture.html.read_bytes()).hexdigest()

    def test_report_choice_and_each_note_choice_are_preserved(self):
        digest=self.report_ready(); route=self.route()
        status,body=self.call(f'/api/reports/{self.fid}/feedback','POST',dict(
            hash=digest,note='Ajuste esta interface',rota=route,
            feedback=dict(kind='notes',notas=[dict(id='note-one',texto='Aumente a legenda',rota=route)])))
        self.assertEqual(status,200,body)
        saved=next(c for c in self.fixture.store.listing('comments',self.fixture.pid) if c['id']==body['comment']['id'])
        self.assertEqual(saved['rota'],route)
        self.assertEqual(saved['feedback']['notas'][0]['rota'],route)
        from central_note_receipts import note_receipts
        receipts=note_receipts(self.fixture.store,self.fixture.pid,self.fid,digest)
        self.assertEqual(receipts['notas'][0]['rota'],route)

    def test_invalid_route_fails_before_saving(self):
        digest=self.report_ready()
        before=self.fixture.store.listing('comments',self.fixture.pid)
        for route in [dict(vendor='missing',modelo='unknown',effort='xhigh'),
                      dict(vendor='gpt',modelo='gpt-6.1-sol',effort='invented')]:
            with self.subTest(route=route):
                status,body=self.call(f'/api/reports/{self.fid}/feedback','POST',dict(hash=digest,note='Synthetic',rota=route))
                self.assertEqual(status,400,body)
        status,body=self.call(f'/api/reports/{self.fid}/feedback','POST',dict(hash=digest,note='',feedback=dict(
            kind='notes',notas=[dict(id='invalid',texto='Synthetic',rota=dict(vendor='gpt',modelo='bad-name',effort='high'))])))
        self.assertEqual(status,400,body)
        self.assertEqual(before,self.fixture.store.listing('comments',self.fixture.pid))

    def test_module_explicit_destination_enters_bridge_without_changing_project_default(self):
        pid=self.fixture.pid
        _,before=self.call(f'/api/projects/{pid}/bridge')
        status,body=self.call(f'/api/projects/{pid}/comments','POST',dict(
            text='Corrija este quadro',target='module:now',rota=self.route(),
            cursor_source=dict(note_id='module-one',storage_key='mb-cursor-notas:home')))
        self.assertEqual(status,200,body)
        self.assertIsNotNone(body['ponte'])
        self.assertEqual(body['comment']['rota'],self.route())
        _,after=self.call(f'/api/projects/{pid}/bridge')
        self.assertEqual(before['data'],after['data'])

    def test_project_profiles_have_catalog_and_source_backed_presets(self):
        status,view=self.call(f'/api/projects/{self.fixture.pid}/bridge')
        self.assertEqual(status,200,view)
        self.assertEqual(set(view['data']['pipeline']),{'planejador','orquestrador','worker','revisor'})
        self.assertEqual(view['data']['espera_segundos'],180)
        self.assertTrue(view['catalogo'])
        self.assertTrue(view['presets'])
        for preset in view['presets']:
            self.assertTrue(preset['fonte'])
            self.assertTrue(preset['tradeoff'])


if __name__=='__main__':unittest.main()
