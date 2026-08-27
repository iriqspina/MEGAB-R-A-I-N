"""260827: o Cowork recusou o .plugin v1.7.0 com "Plugin description must be at
most 500 characters" (a fonte tinha 521). O erro só aparecia no clique de
instalação, em outra máquina — a suíte não tinha dente nenhum nesse campo."""
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "bin"))
spec = importlib.util.spec_from_file_location(
    "mb_build_plugin_claude", RAIZ / "bin" / "mb-build-plugin-claude.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

MANIFESTO = RAIZ / "motor" / build.PLUGIN_DIR / ".claude-plugin" / "plugin.json"


class TestDescriptionDoPlugin(unittest.TestCase):
    """A fonte real: a instância que não tem o plugin pula; a que tem, cobra."""

    def setUp(self):
        if not MANIFESTO.parent.is_dir():
            self.skipTest(f"instância sem {build.PLUGIN_DIR} (pacote público)")
        self.assertTrue(MANIFESTO.is_file(), f"{MANIFESTO.name} ausente na fonte")
        self.dados = json.loads(MANIFESTO.read_text(encoding="utf-8"))

    def test_description_cabe_no_instalador(self):
        desc = self.dados.get("description", "")
        self.assertLessEqual(
            len(desc), build.LIMITE_DESCRIPTION,
            f"description com {len(desc)} chars: o instalador recusa acima de "
            f"{build.LIMITE_DESCRIPTION}")

    def test_description_nao_ficou_vazia_ao_encurtar(self):
        self.assertGreaterEqual(len(self.dados.get("description", "")), 80)


class TestValidarReprova(unittest.TestCase):
    """O gate em si: copia o plugin, estoura a description, espera reprovação."""

    def setUp(self):
        if not MANIFESTO.parent.is_dir():
            self.skipTest(f"instância sem {build.PLUGIN_DIR} (pacote público)")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.plugin = Path(tmp.name) / "plugin"
        shutil.copytree(MANIFESTO.parents[1], self.plugin)
        self.manifesto = self.plugin / ".claude-plugin" / "plugin.json"

    def _erros_de_description(self) -> list[str]:
        return [e for e in build.validar(self.plugin) if "description com" in e]

    def test_reprova_acima_do_limite(self):
        dados = json.loads(self.manifesto.read_text(encoding="utf-8"))
        dados["description"] = "x" * (build.LIMITE_DESCRIPTION + 1)
        self.manifesto.write_text(json.dumps(dados, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        self.assertTrue(self._erros_de_description(),
                        "validar() aceitou description acima do limite")

    def test_aprova_no_limite(self):
        dados = json.loads(self.manifesto.read_text(encoding="utf-8"))
        dados["description"] = "x" * build.LIMITE_DESCRIPTION
        self.manifesto.write_text(json.dumps(dados, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        self.assertFalse(self._erros_de_description(),
                         "validar() reprovou description exatamente no limite")


if __name__ == "__main__":
    unittest.main()
