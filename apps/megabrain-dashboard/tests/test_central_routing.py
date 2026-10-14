import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from central_routing import preview,DEFAULT_ROUTES,validate_routing
from central_store import validate_process

class RoutingTests(unittest.TestCase):
    def test_review_cannot_move_before_production(self):
        data=copy.deepcopy(DEFAULT_ROUTES)
        stages=data['routes'][3]['stages'];stages.insert(1,stages.pop())
        with self.assertRaisesRegex(ValueError,'depois'):validate_routing(data)
    def test_composition_preserves_order_and_required_steps(self):
        out=preview(DEFAULT_ROUTES,'Pedido misto',categories=['pesquisa','visual'])
        self.assertEqual(len(out['stages']),10)
        self.assertEqual([s['source_category'] for s in out['stages']],['pesquisa']*3+['visual']*7)
        self.assertEqual(len(set(s['id'] for s in out['stages'])),10)
        self.assertEqual(sum(bool(s.get('required')) for s in out['stages']),5)
        validate_process({'mode':'analysis','stages':out['stages']})
    def test_composition_rejects_duplicates_and_unknown_routes(self):
        for categories in [['visual','visual'],['unknown'],['pergunta','visual','codigo']]:
            with self.assertRaises(ValueError):preview(DEFAULT_ROUTES,'teste',categories=categories)
    def test_glm_never_runs_below_verified_max_route(self):
        data=copy.deepcopy(DEFAULT_ROUTES);data['routes'][1]['stages'][-1]['effort']='high'
        with self.assertRaisesRegex(ValueError,'máximo'):validate_routing(data)
    def test_api_is_not_a_substring_of_rapido(self):
        self.assertEqual(preview(DEFAULT_ROUTES,'explique rápido')['category'],'pergunta')
    def test_required_review_cannot_become_creator(self):
        data=copy.deepcopy(DEFAULT_ROUTES)
        review=data['routes'][1]['stages'][-1]
        review.update(role='creator',model='codex',effort='xhigh')
        with self.assertRaisesRegex(ValueError,'revisão'):validate_routing(data)
    def test_legacy_upgrade_preserves_human_instruction(self):
        from central_routing import LEGACY_ROUTES,upgrade_legacy
        old=copy.deepcopy(LEGACY_ROUTES);old['routes'][2]['stages'][2]['instruction']='Minha instrução específica, sem trocar por template.'
        upgraded=upgrade_legacy(old)
        self.assertEqual(upgraded['routes'][2]['stages'][2]['instruction'],old['routes'][2]['stages'][2]['instruction'])
        self.assertEqual(upgraded['routes'][1]['stages'][0]['capability'],'research')
        self.assertEqual(upgraded['routes'][1]['stages'][0]['model'],'claude')
        validate_routing(upgraded)
    def test_capabilities_cannot_silently_use_other_models(self):
        for capability,model in [('research','codex'),('code','claude'),('code','glm')]:
            data=copy.deepcopy(DEFAULT_ROUTES);data['routes'][0]['stages'][0].update(capability=capability,model=model)
            with self.assertRaises(ValueError):validate_routing(data)

if __name__=='__main__':unittest.main()
