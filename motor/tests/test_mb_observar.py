"""
test_mb_observar.py — contrato do endpoint de observabilidade (v6, fase 1).

O que NUNCA pode quebrar:
- exit 0 sempre, até com payload lixo (hook não derruba sessão);
- stdout vazio no modo hook (em UserPromptSubmit o stdout vira contexto);
- a linha cai no .mb-log do projeto certo, ou no balde central fora de projeto;
- importador do gerenteneuron é incremental (rodar 2x não duplica).

Roda sozinho:      python tests/test_mb_observar.py
Roda na suíte:     python -m unittest discover tests
"""

from __future__ import annotations

import json
import os
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
OBSERVAR = RAIZ / "bin" / "mb-observar.py"


class Base(unittest.TestCase):
    def setUp(self):
        self.raiz_projetos = Path(tempfile.mkdtemp(prefix="mb-raiz-"))
        self.addCleanup(shutil.rmtree, self.raiz_projetos, ignore_errors=True)
        self.central = self.raiz_projetos / "central-falsa"
        self.central.mkdir()
        self.projeto = self.raiz_projetos / "projeto-x"
        (self.projeto / "sub" / "pasta").mkdir(parents=True)
        self.env = {
            **os.environ,
            "MEGABRAIN_CENTRAL": str(self.central),
            "MEGABRAIN_PROJETOS_ROOT": str(self.raiz_projetos),
        }

    def rodar(self, *args: str, stdin: str = "") -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(OBSERVAR), *args],
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=self.env,
        )

    def linhas_log(self, pasta: Path) -> list[dict]:
        saida = []
        if not pasta.is_dir():
            return saida
        for arq in sorted(pasta.glob("eventos-*.jsonl")):
            for linha in arq.read_text(encoding="utf-8").splitlines():
                saida.append(json.loads(linha))
        return saida


class TestModoHook(Base):
    def test_prompt_gera_linha_no_projeto(self):
        payload = json.dumps({
            "session_id": "abc123",
            "cwd": str(self.projeto / "sub" / "pasta"),
            "prompt": "conserta o bug do menu",
        })
        r = self.rodar("--agente", "claude", "--evento", "prompt", stdin=payload)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "", "modo hook não pode escrever no stdout")

        linhas = self.linhas_log(self.projeto / ".mb-log")
        self.assertEqual(len(linhas), 1, "devia ter exatamente 1 evento no projeto")
        evento = linhas[0]
        self.assertEqual(evento["agente"], "claude")
        self.assertEqual(evento["evento"], "prompt")
        self.assertEqual(evento["prompt"], "conserta o bug do menu")
        self.assertEqual(evento["session_id"], "abc123")

    def test_payload_com_bom_e_aceito(self):
        """Regressao 260819: pipe do PowerShell 5.1 injeta BOM e o JSON era
        descartado como invalido — prompt chegava null no log."""
        payload = "﻿" + json.dumps({"cwd": str(self.projeto), "prompt": "com bom"})
        r = self.rodar("--agente", "claude", "--evento", "prompt", stdin=payload)
        self.assertEqual(r.returncode, 0, r.stderr)
        linhas = self.linhas_log(self.projeto / ".mb-log")
        self.assertEqual(len(linhas), 1)
        self.assertEqual(linhas[0]["prompt"], "com bom")

    def test_payload_lixo_sai_zero_e_silencioso(self):
        r = self.rodar("--agente", "claude", "--evento", "prompt", stdin="{isso nao e json")
        self.assertEqual(r.returncode, 0, "hook nunca pode falhar")
        self.assertEqual(r.stdout, "")

    def test_cwd_fora_da_raiz_cai_no_balde_central(self):
        fora = Path(tempfile.mkdtemp(prefix="mb-fora-"))
        self.addCleanup(shutil.rmtree, fora, ignore_errors=True)
        payload = json.dumps({"cwd": str(fora), "prompt": "oi"})
        r = self.rodar("--agente", "kimi", "--evento", "prompt", stdin=payload)
        self.assertEqual(r.returncode, 0, r.stderr)

        balde = self.central / ".mb-log" / "fora-de-projeto"
        linhas = self.linhas_log(balde)
        self.assertEqual(len(linhas), 1, "evento fora de projeto devia cair no balde central")
        self.assertNotIn(".mb-log", [p.name for p in fora.iterdir()],
                         "não pode criar .mb-log em pasta que não é projeto")

    def test_evento_arquivo_extrai_file_path(self):
        payload = json.dumps({
            "cwd": str(self.projeto),
            "tool_name": "Edit",
            "tool_input": {"file_path": str(self.projeto / "src" / "app.py")},
        })
        r = self.rodar("--agente", "claude", "--evento", "arquivo", stdin=payload)
        self.assertEqual(r.returncode, 0, r.stderr)
        linhas = self.linhas_log(self.projeto / ".mb-log")
        self.assertEqual(len(linhas), 1)
        self.assertIn("app.py", linhas[0]["arquivo"])


class TestImportadorFeedback(Base):
    def montar_feedback(self) -> Path:
        gn = self.raiz_projetos / "gerenteneuron-falso"
        (gn / "data").mkdir(parents=True)
        arq = gn / "data" / "feedback.jsonl"
        linhas = [
            {"timestamp": "2026-08-16T17:00:00+00:00", "aba": "chat", "mensagem": "primeira",
             "estrategia": "cheap", "provider": "ollama", "modelo_usado": "qwen",
             "custo_estimado_usd": 0.0, "tokens_entrada": 1, "tokens_saida": 2,
             "erro": None, "feedback": None},
            {"timestamp": "2026-08-16T18:00:00+00:00", "aba": "chat", "mensagem": "segunda",
             "estrategia": "cheap", "provider": "gemini", "modelo_usado": "flash",
             "custo_estimado_usd": 0.01, "tokens_entrada": 5, "tokens_saida": 9,
             "erro": None, "feedback": None},
        ]
        arq.write_text("\n".join(json.dumps(x) for x in linhas) + "\n", encoding="utf-8")
        return arq

    def test_importa_e_nao_duplica(self):
        arq = self.montar_feedback()
        r1 = self.rodar("--importar-feedback", "--feedback", str(arq))
        self.assertEqual(r1.returncode, 0, r1.stderr)
        self.assertIn("importadas 2", r1.stdout)

        r2 = self.rodar("--importar-feedback", "--feedback", str(arq))
        self.assertIn("importadas 0", r2.stdout, "segunda rodada devia importar 0 (incremental)")

        log_dir = arq.parent.parent / ".mb-log"
        linhas = self.linhas_log(log_dir)
        self.assertEqual(len(linhas), 2)
        self.assertEqual(linhas[0]["agente"], "gerenteneuron")
        self.assertEqual(linhas[1]["extra"]["provider"], "gemini")


if __name__ == "__main__":
    unittest.main()
