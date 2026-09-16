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


class TestMapaFontes(unittest.TestCase):
    def test_orquestracao1_vem_da_fonte_canonica(self):
        mapa = build.mapa_fontes(RAIZ)
        fonte, derivar = mapa["skills/orquestracao1/SKILL.md"]
        self.assertEqual(fonte, RAIZ / "motor/skills/orquestracao1/SKILL.md")
        texto = fonte.read_text(encoding="utf-8")
        self.assertEqual(derivar(texto), texto)

    def test_hypadododiabo_vem_da_fonte_canonica(self):
        mapa = build.mapa_fontes(RAIZ)
        fonte, derivar = mapa["skills/hypadododiabo/SKILL.md"]
        self.assertEqual(fonte, RAIZ / "motor/skills/hypadododiabo/SKILL.md")
        texto = fonte.read_text(encoding="utf-8")
        self.assertEqual(derivar(texto), texto)

    def test_quaseultracode_vem_da_fonte_canonica(self):
        mapa = build.mapa_fontes(RAIZ)
        fonte, derivar = mapa["skills/quaseultracode/SKILL.md"]
        self.assertEqual(fonte, RAIZ / "motor/skills/quaseultracode/SKILL.md")
        texto = fonte.read_text(encoding="utf-8")
        self.assertEqual(derivar(texto), texto)

    def test_orquestracao2_vem_da_fonte_canonica(self):
        mapa = build.mapa_fontes(RAIZ)
        fonte, derivar = mapa["skills/orquestracao2/SKILL.md"]
        self.assertEqual(fonte, RAIZ / "motor/skills/orquestracao2/SKILL.md")
        texto = fonte.read_text(encoding="utf-8")
        self.assertEqual(derivar(texto), texto)


class TestBootstrapDeModos(unittest.TestCase):
    def test_oferta_compacta_aparece_uma_vez_e_nao_e_pergunta(self):
        hook = (RAIZ / "motor" / build.PLUGIN_DIR /
                "scripts" / "260821_session-start.js")
        texto = hook.read_text(encoding="utf-8")
        oferta = ("Orquestração: /orquestracao1 é a V6 primária para trabalho multiagente novo; "
                  "/orquestracao2 mantém a V5 apenas para retomada ou pedido explícito. "
                  "/hypadododiabo explora o melhor caso com limites reais.")
        self.assertEqual(texto.count(oferta), 1)
        self.assertNotIn("?", oferta)

    def test_quaseultracode_so_e_sugerido_para_projeto_grande(self):
        hook = (RAIZ / "motor" / build.PLUGIN_DIR /
                "scripts" / "260821_session-start.js")
        texto = hook.read_text(encoding="utf-8")
        regra = ("Em projeto grande, sugerir /quaseultracode uma vez; "
                 "não sugerir em conversa ordinária ou tarefa pequena.")
        self.assertEqual(texto.count(regra), 1)


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


class TestContratosDeOrquestracao(unittest.TestCase):
    def setUp(self):
        skills = RAIZ / "motor" / "skills"
        self.orq = (skills / "orquestracao1" / "SKILL.md").read_text(encoding="utf-8")
        self.quase = (skills / "quaseultracode" / "SKILL.md").read_text(encoding="utf-8")
        self.hypado = (skills / "hypadododiabo" / "SKILL.md").read_text(encoding="utf-8")

    def test_v6_declara_rota_revisao_e_limites(self):
        self.assertIn("V6 primária", self.orq)
        self.assertIn("revisa o plano antes de produzir", self.orq)  # rota do dono 260915: Opus/fable revisa, Astra produz
        self.assertIn("`review_approved` significa somente", self.orq)
        self.assertIn("`NAO_MEDIDO`", self.orq)

    def test_casa_nao_e_cabana_e_ponte_tem_cadeia(self):
        self.assertIn("se o pedido é **casa**, uma **cabana** não é solução", self.quase)
        self.assertIn("Ela só pode ser `PONTE`", self.quase)
        for termo in ("cadeia causal", "prazo/etapa", "evidência", "próximo passo",
                      "custo e kill criteria"):
            self.assertIn(termo, self.quase)

    def test_distracao_fica_fora_e_melhoria_exige_prova(self):
        self.assertIn("`DISTRAÇÃO` não entra no backlog apresentado", self.quase)
        self.assertIn("supera ou\n  preserva o baseline e tem prova adequada", self.quase)

    def test_headhunter_passa_pela_segunda_leitura(self):
        self.assertIn("segunda leitura “casa ≠ cabana”", self.hypado)
        self.assertIn("Somente `SOLUÇÃO` ou `PONTE` defensável chega ao Sol", self.hypado)


if __name__ == "__main__":
    unittest.main()
