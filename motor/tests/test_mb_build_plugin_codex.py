import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "bin"))
spec = importlib.util.spec_from_file_location(
    "mb_build_plugin_codex", RAIZ / "bin" / "mb-build-plugin-codex.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class TestBuildPluginCodex(unittest.TestCase):
    def tmpdir(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def central_fake(self) -> Path:
        raiz = self.tmpdir()
        for nome in build.SKILLS_CANONICAS:
            p = raiz / "motor" / "skills" / nome / "SKILL.md"
            p.parent.mkdir(parents=True)
            p.write_text(f"---\nname: {nome}\ndescription: x\n---\n{nome}\n",
                         encoding="utf-8")
        fonte = raiz / "motor" / "plugin-megabrain-codex"
        manifesto = fonte / ".codex-plugin" / "plugin.json"
        manifesto.parent.mkdir(parents=True)
        manifesto.write_text(json.dumps({
            "name": "megabrain",
            "version": "1",
            "skills": "./skills/",
        }), encoding="utf-8")
        registrar = fonte / "skills" / "registrar-licao" / "SKILL.md"
        registrar.parent.mkdir(parents=True)
        registrar.write_text(
            "---\nname: registrar-licao\ndescription: x\n---\nadaptação Codex\n",
            encoding="utf-8",
        )
        return raiz

    def test_destino_vazio_recebe_manifesto_e_seis_skills(self):
        central = self.central_fake()
        destino = self.tmpdir()
        build.montar(central, destino)

        self.assertEqual(build.conferir_drift(central, destino), [])
        self.assertEqual(build.validar(destino), [])
        self.assertTrue((destino / ".codex-plugin/plugin.json").is_file())
        self.assertTrue((destino / "skills/registrar-licao/SKILL.md").is_file())
        self.assertEqual(
            set(build._arquivos_atuais(destino)),
            set(build.arquivos_esperados(central)),
        )

    def test_duas_montagens_vazias_sao_identicas_byte_a_byte(self):
        central = self.central_fake()
        destino_a = self.tmpdir()
        destino_b = self.tmpdir()
        build.montar(central, destino_a)
        build.montar(central, destino_b)
        self.assertEqual(build._arquivos_atuais(destino_a),
                         build._arquivos_atuais(destino_b))

    def test_fonte_codex_ausente_recusa_build(self):
        central = self.central_fake()
        (central / "motor/plugin-megabrain-codex/skills/registrar-licao/SKILL.md").unlink()
        with self.assertRaises(FileNotFoundError):
            build.montar(central, self.tmpdir())

    def test_drift_detecta_ausente_extra_e_divergente(self):
        central = self.central_fake()
        destino = self.tmpdir()
        build.montar(central, destino)
        (destino / ".codex-plugin/plugin.json").unlink()
        (destino / "skills/megabrain/SKILL.md").write_text("velho\n", encoding="utf-8")
        (destino / "extra.txt").write_text("órfão\n", encoding="utf-8")
        drift = build.conferir_drift(central, destino)
        self.assertIn("AUSENTE: .codex-plugin/plugin.json", drift)
        self.assertIn("DIVERGE: skills/megabrain/SKILL.md", drift)
        self.assertIn("EXTRA: extra.txt", drift)

    def test_manifesto_invalido_recusa_build(self):
        central = self.central_fake()
        manifesto = central / "motor/plugin-megabrain-codex/.codex-plugin/plugin.json"
        manifesto.write_text(json.dumps({"name": "outro", "skills": "./skills/"}),
                             encoding="utf-8")
        with self.assertRaises(ValueError):
            build.montar(central, self.tmpdir())


if __name__ == "__main__":
    unittest.main()
