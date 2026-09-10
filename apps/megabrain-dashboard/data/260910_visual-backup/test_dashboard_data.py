import sys
from pathlib import Path
import tempfile
import unittest


APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from dashboard_data import collect
from render_html import render


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
        self.assertIn("Micro · novidades e decisões recentes", html)
        self.assertIn("&lt;não executar&gt;", html)


if __name__ == "__main__":
    unittest.main()
