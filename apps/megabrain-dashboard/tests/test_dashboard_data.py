import sys
from pathlib import Path
import tempfile
import unittest
from html.parser import HTMLParser
import json
from unittest.mock import patch


APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from dashboard_data import collect
from render_html import render
import dashboard


class DashboardTests(unittest.TestCase):
    def test_project_state_has_priority_over_embedded_megabrain_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "Projeto"
            project.mkdir()
            (project / "ESTADO.md").write_text("TL;DR: Projeto real\nBLOQUEIO: Aprovar o escopo\nPRÓXIMO PASSO: Revisar a tela", encoding="utf-8")
            embedded = project / "MEGABRAIN" / "memoria" / "estado"
            embedded.mkdir(parents=True)
            (embedded / "ESTADO.md").write_text("TL;DR: Copia antiga", encoding="utf-8")
            data = collect(project)
            self.assertEqual(data["tldr"], "Projeto real")
            self.assertIn("Projeto", data["state_path"])
            self.assertEqual(data["root"], str(project / "MEGABRAIN"))

    def test_html_exposes_macro_micro_and_escapes_project_text(self):
        data = {"name": "Teste", "updated_at": "Não medido", "tldr": "<não executar>",
                "root": "C:/Teste", "blocker": "Aprovar", "next_step": "Abrir", "version": "v7.13",
                "lock": "livre", "git_dirty": 0, "projects_current": 1, "projects_total": 2,
                "stale_projects": [], "recent_decisions": ["Decisão"], "is_central": False,
                "state_path": "C:/Teste/ESTADO.md", "handoff_path": "C:/Teste/HANDOFF.md",
                "decisions_path": "C:/Teste/DECISOES.md"}
        html = render(data)
        self.assertIn("Macro · projeto inteiro", html)
        self.assertIn("O que mudou", html)
        self.assertIn("&lt;não executar&gt;", html)

    def test_missing_measurements_remain_unknown_not_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            data = collect(temp)
            html = render(data)
            self.assertIsNone(data['git_dirty'])
            self.assertIsNone(data['projects_total'])
            self.assertIn('Sincronização: Não medido', html)
            self.assertIn('Bloqueio não medido', html)
            self.assertNotIn('class="num">0', html)
            self.assertNotIn('Sem bloqueio informado', html)

    def test_actual_zero_is_distinct_from_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            data = collect(temp)
            data.update(git_dirty=0, projects_total=0, projects_current=0)
            html = render(data)
            self.assertEqual(html.count('class="num">0</span>'), 3)

    def test_one_action_and_no_repeated_priority(self):
        with tempfile.TemporaryDirectory() as temp:
            data = collect(temp)
            data.update(blocker='Aprovar a tela', next_step='Aprovar a tela')
            html = render(data)
            self.assertEqual(html.count('Aprovar a tela'), 1)
            self.assertLess(html.index('id="agora"'), html.index('id="overview-title"'))

    def test_existing_sources_are_encoded_local_links_only(self):
        with tempfile.TemporaryDirectory(prefix='dashboard espaço ') as temp:
            project = Path(temp)
            state = project / 'ESTADO.md'
            state.write_text('TL;DR: teste', encoding='utf-8')
            data = collect(project)
            html = render(data)
            self.assertIn(state.as_uri(), html)
            self.assertIn('Handoff · não encontrado', html)
            data['state_path'] = 'javascript:alert(1)'
            self.assertNotIn('href="javascript:', render(data))

    def test_snapshot_source_exposed_without_changing_collector_precedence(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            (project / 'dados').mkdir()
            snapshot = project / 'dados' / 'estado.json'
            snapshot.write_text(json.dumps({'estado': {'tldr': 'Fotografia original'}}), encoding='utf-8')
            (project / 'ESTADO.md').write_text('TL;DR: Documento posterior', encoding='utf-8')
            data = collect(project)
            self.assertEqual(data['tldr'], 'Fotografia original')
            self.assertEqual(data['snapshot_path'], str(snapshot))
            self.assertIn(snapshot.as_uri(), render(data))

    def test_user_content_cannot_add_elements_or_network_resources(self):
        class Tags(HTMLParser):
            def __init__(self):
                super().__init__()
                self.tags = []
                self.resources = []
            def handle_starttag(self, tag, attrs):
                self.tags.append(tag)
                self.resources.extend(value for key, value in attrs if key in {'src', 'href'})
        with tempfile.TemporaryDirectory() as temp:
            data = collect(temp)
            attack = '<script>alert(1)</script><img src="https://example.com/pixel">'
            data.update(name=attack, blocker=attack, next_step=attack, tldr=attack,
                        recent_decisions=[attack], stale_projects=[{'projeto': attack, 'versao': attack}])
            parser = Tags()
            parser.feed(render(data))
            self.assertNotIn('script', parser.tags)
            self.assertFalse(any(value.startswith(('https:', 'http:', '//')) for value in parser.resources))

    def test_standalone_refresh_is_not_presented_as_live_collection(self):
        with tempfile.TemporaryDirectory() as temp:
            data = collect(temp)
            self.assertIn('Recarregar prévia', render(data))
            self.assertIn('apenas reabre o HTML gerado', render(data))
            self.assertNotIn('location.reload()', render(data, native=True))

    def test_unavailable_snapshot_does_not_claim_sync_is_current(self):
        with tempfile.TemporaryDirectory() as temp:
            data = collect(temp)
            self.assertIn('Dados desta leitura · não encontrado', render(data))
            self.assertIn('Leitura dos documentos locais', render(data))

    def test_refresh_rereads_project_and_does_not_write_to_its_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / 'project'
            project.mkdir()
            source = project / 'ESTADO.md'
            source.write_text('PRÓXIMO PASSO: Revisar primeira tela', encoding='utf-8')
            with patch.object(dashboard, 'APP', Path(temp) / 'output'):
                output = dashboard.refresh(project)
                self.assertIn('Revisar primeira tela', output.read_text(encoding='utf-8'))
                source.write_text('PRÓXIMO PASSO: Revisar segunda tela', encoding='utf-8')
                original = source.read_bytes()
                dashboard.refresh(project, native=True)
                self.assertIn('Revisar segunda tela', output.read_text(encoding='utf-8'))
                self.assertNotIn('Recarregar prévia', output.read_text(encoding='utf-8'))
                self.assertEqual(source.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
