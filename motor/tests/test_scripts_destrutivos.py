"""
test_scripts_destrutivos.py — cobre os dois scripts que copiam/escrevem
árvores: mb-check-version.py (central -> projeto) e
mb-sync-projeto-para-central.py (projeto -> central).

Até 260819 nenhum dos dois tinha teste — justamente os mais perigosos
(lição: "corrigido no changelog != corrigido no disco"). Tudo roda em
diretórios temporários; a central real nunca é tocada.

Roda sozinho:      python tests/test_scripts_destrutivos.py
Roda na suíte:     python -m unittest discover tests
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# v7.1: a suíte pode viver plana (tests/) ou dentro de motor/ (etapa 2 da
# reorg). Achar a raiz subindo até bin/mb_utils.py vale nos dois casos.
def _raiz() -> Path:
    aqui = Path(__file__).resolve()
    for cand in aqui.parents:
        if (cand / "bin" / "mb_utils.py").is_file():
            return cand
    return aqui.parent.parent


RAIZ = _raiz()
CHECK_VERSION = RAIZ / "bin" / "mb-check-version.py"
SYNC_PARA_CENTRAL = RAIZ / "bin" / "mb-sync-projeto-para-central.py"

LICOES_CENTRAL = """# licoes megabrain (fixture)

## 260801 — licao antiga da central
GATILHO: situacao antiga
LICAO: ja registrada na central
"""

LICAO_NOVA = """## 260815 — licao nova do projeto
GATILHO: situacao nova
LICAO: descoberta dentro do projeto
"""


def rodar(script: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )


def snapshot(pasta: Path) -> dict[str, bytes]:
    """Mapa caminho-relativo -> conteúdo, pra provar que nada mudou."""
    return {
        str(f.relative_to(pasta)): f.read_bytes()
        for f in sorted(pasta.rglob("*"))
        if f.is_file()
    }


class Base(unittest.TestCase):
    def tmp(self, prefixo: str) -> Path:
        p = Path(tempfile.mkdtemp(prefix=prefixo))
        self.addCleanup(shutil.rmtree, p, ignore_errors=True)
        return p

    def central_falsa(self) -> Path:
        """Central mínima completa: todos os itens do MAPEAMENTO existem."""
        c = self.tmp("mb-central-")
        (c / "VERSAO.txt").write_text("2026-08-19 · v5.9 — fixture de teste\n", encoding="utf-8")
        (c / "MEGABRAIN.md").write_text("# MEGABRAIN fixture\n", encoding="utf-8")
        (c / "OFFLINE.md").write_text("# offline fixture\n", encoding="utf-8")
        (c / "skills" / "megabrain").mkdir(parents=True)
        (c / "skills" / "megabrain" / "SKILL.md").write_text("# skill fixture\n", encoding="utf-8")
        (c / "referencias").mkdir()
        (c / "referencias" / "ref-central.md").write_text("ref da central\n", encoding="utf-8")
        (c / "bin").mkdir()
        (c / "bin" / "leia.md").write_text("bin fixture\n", encoding="utf-8")
        (c / "dna").mkdir()
        (c / "dna" / "README.md").write_text("dna fixture\n", encoding="utf-8")
        (c / "licoes-megabrain.md").write_text(LICOES_CENTRAL, encoding="utf-8")
        return c

    def central_falsa_motor(self) -> Path:
        """Central no layout v7.1: humano na raiz, máquina em motor/.
        Prova que o sync continua entregando cópia PLANA no projeto."""
        c = self.tmp("mb-central-motor-")
        (c / "memoria" / "nucleo").mkdir(parents=True)
        (c / "memoria" / "nucleo" / "VERSAO.txt").write_text(
            "2026-08-24 · v7.1 — fixture motor\n", encoding="utf-8")
        (c / "memoria" / "nucleo" / "MEGABRAIN.md").write_text("# MEGABRAIN fixture\n", encoding="utf-8")
        (c / "memoria" / "nucleo" / "OFFLINE.md").write_text("# offline fixture\n", encoding="utf-8")
        (c / "memoria" / "nucleo" / "licoes-megabrain.md").write_text(LICOES_CENTRAL, encoding="utf-8")
        (c / "bin").mkdir()
        (c / "bin" / "leia.md").write_text("bin fixture\n", encoding="utf-8")
        (c / "motor" / "skills" / "megabrain").mkdir(parents=True)
        (c / "motor" / "skills" / "megabrain" / "SKILL.md").write_text("# skill fixture\n", encoding="utf-8")
        (c / "motor" / "referencias").mkdir(parents=True)
        (c / "motor" / "referencias" / "ref-central.md").write_text("ref da central\n", encoding="utf-8")
        (c / "motor" / "dna").mkdir(parents=True)
        (c / "motor" / "dna" / "README.md").write_text("dna fixture\n", encoding="utf-8")
        (c / "motor" / "modelos" / "cerebro").mkdir(parents=True)
        return c

    def projeto_com_megabrain(self) -> Path:
        p = self.tmp("mb-projeto-")
        mb = p / "MEGABRAIN"
        (mb / "skills" / "megabrain").mkdir(parents=True)
        (mb / "MEGABRAIN.md").write_text("# MEGABRAIN do projeto\n", encoding="utf-8")
        (mb / "skills" / "megabrain" / "SKILL.md").write_text("# skill do projeto\n", encoding="utf-8")
        (mb / "referencias").mkdir()
        (mb / "referencias" / "ref-projeto.md").write_text("ref do projeto\n", encoding="utf-8")
        (mb / "VERSAO.txt").write_text("2026-08-19 · v5.9 — projeto\n", encoding="utf-8")
        (mb / "licoes-megabrain.md").write_text(
            LICOES_CENTRAL + "\n" + LICAO_NOVA, encoding="utf-8"
        )
        return p


class TestCheckVersion(Base):
    def test_dry_run_le_versao_da_copia_magra_sem_perguntar(self):
        central = self.central_falsa()
        projeto = self.tmp("mb-projeto-magro-")
        mb = projeto / "MEGABRAIN"
        mb.mkdir()
        (mb / ".mb-origem.json").write_text(json.dumps({
            "formato": "magra",
            "versao_curta": "2026-08-19 · v5.9",
        }), encoding="utf-8")
        antes = snapshot(projeto)

        r = rodar(CHECK_VERSION, "--projeto", str(projeto), "--central", str(central),
                  "--offline", "--dry-run")

        self.assertEqual(r.returncode, 0, f"dry-run magro devia concluir: {r.stdout}{r.stderr}")
        self.assertIn("versões iguais", r.stdout)
        self.assertNotIn("EOFError", r.stderr)
        self.assertEqual(snapshot(projeto), antes, "dry-run alterou o ponteiro magro")

    def test_dry_run_magro_sem_versao_nao_abre_prompt(self):
        central = self.central_falsa()
        projeto = self.tmp("mb-projeto-magro-")
        mb = projeto / "MEGABRAIN"
        mb.mkdir()
        (mb / ".mb-origem.json").write_text(
            json.dumps({"formato": "magra"}), encoding="utf-8")

        r = rodar(CHECK_VERSION, "--projeto", str(projeto), "--central", str(central),
                  "--offline", "--dry-run")

        self.assertEqual(r.returncode, 0, f"dry-run sem versão devia concluir: {r.stdout}{r.stderr}")
        self.assertIn("dry-run: gravaria .mb-origem.json", r.stdout)
        self.assertNotIn("EOFError", r.stderr)

    def test_central_externa_e_aceita(self):
        """Regressao 260819: --central valido fora da central detectada era
        recusado (bug A5 reencarnado)."""
        central = self.central_falsa()
        projeto = self.tmp("mb-projeto-")
        r = rodar(CHECK_VERSION, "--projeto", str(projeto), "--central", str(central),
                  "--auto", "--dry-run")
        self.assertNotIn("central inválida", r.stdout + r.stderr)
        self.assertEqual(r.returncode, 0, f"central externa devia ser aceita: {r.stdout}{r.stderr}")

    def test_central_sem_versao_e_recusada(self):
        vazia = self.tmp("mb-vazia-")
        projeto = self.tmp("mb-projeto-")
        r = rodar(CHECK_VERSION, "--projeto", str(projeto), "--central", str(vazia), "--auto")
        self.assertNotEqual(r.returncode, 0, "pasta sem VERSAO.txt nao pode passar por central")

    def test_dry_run_nao_escreve_nada(self):
        central = self.central_falsa()
        projeto = self.tmp("mb-projeto-")
        rodar(CHECK_VERSION, "--projeto", str(projeto), "--central", str(central),
              "--auto", "--dry-run")
        self.assertEqual(snapshot(projeto), {}, "dry-run criou arquivos no projeto")

    def test_sync_real_cria_megabrain_no_projeto(self):
        central = self.central_falsa()
        projeto = self.tmp("mb-projeto-")
        r = rodar(CHECK_VERSION, "--projeto", str(projeto), "--central", str(central), "--auto")
        self.assertEqual(r.returncode, 0, f"sync devia concluir: {r.stdout}{r.stderr}")
        mb = projeto / "MEGABRAIN"
        for rel in ("MEGABRAIN.md", "VERSAO.txt", "skills/megabrain/SKILL.md",
                    "referencias/ref-central.md", "licoes-megabrain.md"):
            self.assertTrue((mb / rel).exists(), f"faltou {rel} apos sync")

    def test_sync_de_central_v71_entrega_copia_plana(self):
        """Etapa 2 da reorg: central com a máquina em motor/ tem que sincronizar
        igual — e a cópia do projeto continua PLANA (skills/, referencias/)."""
        central = self.central_falsa_motor()
        projeto = self.tmp("mb-projeto-")
        r = rodar(CHECK_VERSION, "--projeto", str(projeto), "--central", str(central), "--auto")
        self.assertEqual(r.returncode, 0, f"sync devia concluir: {r.stdout}{r.stderr}")
        mb = projeto / "MEGABRAIN"
        for rel in ("MEGABRAIN.md", "VERSAO.txt", "skills/megabrain/SKILL.md",
                    "referencias/ref-central.md", "dna/README.md"):
            self.assertTrue((mb / rel).exists(), f"faltou {rel} apos sync de central v7.1")
        self.assertFalse((mb / "motor").exists(), "a copia do projeto nao pode nascer com motor/")

    def test_projeto_igual_central_e_recusado(self):
        central = self.central_falsa()
        r = rodar(CHECK_VERSION, "--projeto", str(central), "--central", str(central), "--auto")
        self.assertNotEqual(r.returncode, 0, "sincronizar a central dentro dela mesma e proibido")

    def test_copia_tocada_e_acusada(self):
        """v6 fase 4 (requisito 1): mesma versao declarada + conteudo diferente
        = copia tocada localmente, exit 2 com aviso."""
        central = self.central_falsa()
        projeto = self.tmp("mb-projeto-")
        rodar(CHECK_VERSION, "--projeto", str(projeto), "--central", str(central), "--auto")
        (projeto / "MEGABRAIN" / "MEGABRAIN.md").write_text(
            "# editado localmente\n", encoding="utf-8")
        r = rodar(CHECK_VERSION, "--projeto", str(projeto), "--central", str(central), "--auto")
        self.assertEqual(r.returncode, 2, f"copia tocada devia sair 2: {r.stdout}{r.stderr}")
        self.assertIn("TOCADA", r.stdout)

    def test_gate_drift_acusa_export_desatualizado(self):
        """v6 fase 4: export sem VERSAO (ou versao diferente) = drift, exit 1."""
        import os
        central = self.central_falsa()
        (central / "_github/export").mkdir(parents=True)
        (central / "_github/repo-local").mkdir()
        env = {**os.environ, "MEGABRAIN_CENTRAL": str(central)}
        r = rodar(CHECK_VERSION, "--gate-drift", env=env)
        self.assertEqual(r.returncode, 1, f"export vazio devia acusar drift: {r.stdout}")
        self.assertIn("DRIFT", r.stdout.upper())


class TestSyncProjetoParaCentral(Base):
    def test_dry_run_nao_altera_central(self):
        central = self.central_falsa()
        projeto = self.projeto_com_megabrain()
        antes = snapshot(central)
        r = rodar(SYNC_PARA_CENTRAL, "--projeto", str(projeto), "--central", str(central),
                  "--dry-run")
        self.assertEqual(r.returncode, 0, f"dry-run devia concluir: {r.stdout}{r.stderr}")
        self.assertEqual(snapshot(central), antes, "dry-run alterou a central")

    def test_merge_licoes_apenda_sem_apagar(self):
        central = self.central_falsa()
        projeto = self.projeto_com_megabrain()
        r = rodar(SYNC_PARA_CENTRAL, "--projeto", str(projeto), "--central", str(central))
        self.assertEqual(r.returncode, 0, f"sync devia concluir: {r.stdout}{r.stderr}")

        licoes = (central / "licoes-megabrain.md").read_text(encoding="utf-8")
        self.assertIn("260801 — licao antiga da central", licoes, "merge apagou licao da central")
        self.assertIn("260815 — licao nova do projeto", licoes, "licao do projeto nao subiu")

    def test_merge_e_idempotente(self):
        central = self.central_falsa()
        projeto = self.projeto_com_megabrain()
        rodar(SYNC_PARA_CENTRAL, "--projeto", str(projeto), "--central", str(central))
        rodar(SYNC_PARA_CENTRAL, "--projeto", str(projeto), "--central", str(central))
        licoes = (central / "licoes-megabrain.md").read_text(encoding="utf-8")
        self.assertEqual(licoes.count("260815 — licao nova do projeto"), 1,
                         "rodar 2x duplicou a licao")

    def test_merge_preserva_arquivo_so_da_central(self):
        central = self.central_falsa()
        projeto = self.projeto_com_megabrain()
        rodar(SYNC_PARA_CENTRAL, "--projeto", str(projeto), "--central", str(central))
        self.assertTrue((central / "referencias" / "ref-central.md").exists(),
                        "merge de referencias/ apagou arquivo que so existia na central")
        self.assertTrue((central / "referencias" / "ref-projeto.md").exists(),
                        "referencia do projeto nao subiu")

    def test_central_invalida_e_recusada(self):
        vazia = self.tmp("mb-vazia-")
        projeto = self.projeto_com_megabrain()
        antes = snapshot(vazia)
        r = rodar(SYNC_PARA_CENTRAL, "--projeto", str(projeto), "--central", str(vazia))
        self.assertNotEqual(r.returncode, 0, "pasta sem cara de central nao pode receber escrita")
        self.assertEqual(snapshot(vazia), antes)


if __name__ == "__main__":
    unittest.main()
