"""Coletor de sessões do megabrain-mod (motor/mods/megabrain-mod/coletor/mb_sessoes.py).

Monta um PC falso numa pasta temporária (MB_SESSOES_HOME) com Claude no app e no
terminal, Codex 1 e 2 e ZCode, e confere o que entra, o que fica de fora e o estado.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

COLETOR = Path(__file__).resolve().parents[1] / "mods" / "megabrain-mod" / "coletor" / "mb_sessoes.py"
spec = importlib.util.spec_from_file_location("mb_sessoes", COLETOR)
mb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mb)

AGORA = 1_800_000_000_000.0  # ms
MIN = 60_000


def iso(ms: float) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def tocar(caminho: Path, ms: float) -> None:
    os.utime(caminho, (ms / 1000, ms / 1000))


class ColetorSessoes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.antes = os.environ.get("MB_SESSOES_HOME")
        os.environ["MB_SESSOES_HOME"] = str(self.home)
        h = self.home

        # Claude no app: uma ativa (conversa mexida há 1 min), uma arquivada
        app = h / "AppData/Roaming/Claude/claude-code-sessions/u/o"
        app.mkdir(parents=True)
        cwd = r"<PROJETOS_ROOT>\Portfolio"
        (app / "local_a.json").write_text(json.dumps({
            "sessionId": "local_a", "cliSessionId": "cli-a", "cwd": cwd, "title": "WhatsApp para clientes",
            "lastActivityAt": AGORA - 50 * MIN, "isArchived": False}), encoding="utf-8")
        (app / "local_b.json").write_text(json.dumps({
            "sessionId": "local_b", "cliSessionId": "cli-b", "cwd": cwd, "title": "Velha arquivada",
            "lastActivityAt": AGORA - MIN, "isArchived": True}), encoding="utf-8")
        proj = h / ".claude/projects" / mb.pasta_de_transcricao(cwd)
        proj.mkdir(parents=True)
        conversa_app = proj / "cli-a.jsonl"
        conversa_app.write_text(
            json.dumps({"type": "user", "entrypoint": "claude-desktop", "timestamp": iso(AGORA - MIN)}) + "\n"
            + json.dumps({"type": "bridge-session", "timestamp": iso(AGORA)}) + "\n",
            encoding="utf-8")
        tocar(conversa_app, AGORA)

        # sessão do app parada há 69 h, mas reconectada agora (arquivo e ponte recentes)
        (app / "local_velha.json").write_text(json.dumps({
            "sessionId": "local_velha", "cliSessionId": "cli-velha", "cwd": cwd, "title": "Parada há 69 h",
            "lastActivityAt": AGORA - 69 * 60 * MIN, "isArchived": False}), encoding="utf-8")
        velha = proj / "cli-velha.jsonl"
        velha.write_text(
            json.dumps({"type": "assistant", "entrypoint": "claude-desktop", "timestamp": iso(AGORA - 69 * 60 * MIN)}) + "\n"
            + json.dumps({"type": "bridge-session", "timestamp": iso(AGORA)}) + "\n",
            encoding="utf-8")
        tocar(velha, AGORA)

        # arquivo quebrado do app não derruba a fonte
        (app / "local_quebrado.json").write_text('["não é objeto"]', encoding="utf-8")
        for arq in app.glob("local_*.json"):
            tocar(arq, AGORA - MIN)

        # Claude no terminal: uma conversa e uma automação (claude -p)
        term = proj / "cli-t.jsonl"
        term.write_text(
            json.dumps({"type": "user", "entrypoint": "cli", "cwd": cwd,
                        "message": {"content": "<system-reminder>x</system-reminder> refazer o banner"}}) + "\n",
            encoding="utf-8")
        tocar(term, AGORA - 30 * MIN)
        auto = proj / "cli-p.jsonl"
        auto.write_text(json.dumps({"type": "user", "entrypoint": "sdk-cli", "cwd": cwd,
                                    "message": {"content": "/mb-ajustes"}}) + "\n", encoding="utf-8")
        tocar(auto, AGORA - MIN)

        # Codex 1: conversa com nome + subagente; Codex 2: exec (automação)
        for base, ident, extra, nome in (
            (".codex", "c-main", {"source": "vscode"}, "Verificar envio de WhatsApp"),
            (".codex", "c-sub", {"parent_thread_id": "c-main"}, None),
            (".codex-gpt2", "c-exec", {"source": "exec"}, None),
        ):
            pasta = h / base / "sessions/2026/10/09"
            pasta.mkdir(parents=True, exist_ok=True)
            arq = pasta / f"rollout-x-{ident}.jsonl"
            arq.write_text(
                json.dumps({"type": "session_meta", "payload": {"id": ident, "cwd": cwd, **extra}}) + "\n"
                + json.dumps({"type": "event_msg", "timestamp": iso(AGORA - 0.5 * MIN)}) + "\n",
                encoding="utf-8")
            tocar(arq, AGORA - 5 * MIN)  # data do arquivo atrasada: vale o registro
            if nome:
                (h / base / "session_index.jsonl").write_text(json.dumps({"id": ident, "thread_name": nome}) + "\n",
                                                              encoding="utf-8")

        # ZCode: raiz ativa, subagente e uma antiga demais
        db = h / ".zcode/cli/db"
        db.mkdir(parents=True)
        con = sqlite3.connect(db / "db.sqlite")
        con.execute("create table session (id text, title text, directory text, time_updated integer, "
                    "time_archived integer, parent_id text)")
        con.executemany("insert into session values (?,?,?,?,?,?)", [
            ("sess_z1", "Analisar progresso", r"<PROJETOS_ROOT>\Bounty Hunter", AGORA - 3 * MIN, None, None),
            ("sess_subagent_q", "Revisão", r"<PROJETOS_ROOT>\Bounty Hunter", AGORA - MIN, None, "sess_z1"),
            ("sess_velha", "Antiga", r"<PROJETOS_ROOT>\Bounty Hunter", AGORA - 30 * 60 * MIN, None, None),
        ])
        con.commit()
        con.close()

    def tearDown(self):
        if self.antes is None:
            os.environ.pop("MB_SESSOES_HOME", None)
        else:
            os.environ["MB_SESSOES_HOME"] = self.antes
        self.tmp.cleanup()

    def test_junta_as_cinco_fontes_e_separa_automacoes(self):
        d = mb.coletar(horas=12, agora_ms=AGORA)
        self.assertTrue(all(f["ok"] for f in d["fontes"].values()), d["fontes"])
        conversas = {(s["fonte"], s["titulo"]) for s in d["sessoes"] if not s["automacao"]}
        self.assertEqual(conversas, {
            ("Claude", "WhatsApp para clientes"),
            ("Claude terminal", "refazer o banner"),
            ("Codex 1", "Verificar envio de WhatsApp"),
            ("ZCode", "Analisar progresso"),
        })
        automacoes = {s["fonte"] for s in d["sessoes"] if s["automacao"]}
        self.assertEqual(automacoes, {"Claude terminal", "Codex 2"})

    def test_estado_pela_ultima_atividade(self):
        por_titulo = {s["titulo"]: s for s in mb.coletar(horas=12, agora_ms=AGORA)["sessoes"]}
        # app diz 50 min, mas a conversa foi mexida há 1 min: vale a mais recente
        self.assertEqual(por_titulo["WhatsApp para clientes"]["estado"], "agora")
        self.assertEqual(por_titulo["refazer o banner"]["estado"], "recente")
        self.assertEqual(por_titulo["Analisar progresso"]["projeto"], "Bounty Hunter")

    def test_reconexao_do_app_nao_revive_sessao_parada(self):
        titulos = {s["titulo"] for s in mb.coletar(horas=12, agora_ms=AGORA)["sessoes"]}
        self.assertNotIn("Parada há 69 h", titulos)

    def test_hora_do_registro_vence_data_atrasada_do_arquivo(self):
        codex = next(s for s in mb.coletar(horas=12, agora_ms=AGORA)["sessoes"] if s["fonte"] == "Codex 1")
        self.assertEqual(codex["estado"], "agora")
        self.assertEqual(codex["idade_s"], 30)

    def test_zcode_com_cerquilha_no_caminho(self):
        home2 = self.home / "home #2"
        (home2 / ".zcode/cli/db").mkdir(parents=True)
        con = sqlite3.connect(home2 / ".zcode/cli/db/db.sqlite")
        con.execute("create table session (id text, title text, directory text, time_updated integer, "
                    "time_archived integer, parent_id text)")
        con.execute("insert into session values ('sess_k', 'Com cerquilha', 'S:/x', ?, null, null)", (AGORA - MIN,))
        con.commit()
        con.close()
        itens = mb.coletar_zcode(home2, AGORA - 3600 * 1000)
        self.assertEqual([i["titulo"] for i in itens], ["Com cerquilha"])

    def test_fonte_ausente_nao_derruba_as_outras(self):
        (self.home / ".zcode/cli/db/db.sqlite").unlink()
        d = mb.coletar(horas=12, agora_ms=AGORA)
        self.assertFalse(d["fontes"]["ZCode"]["ok"])
        self.assertTrue(d["fontes"]["Claude"]["ok"])
        self.assertGreater(len(d["sessoes"]), 0)

    def test_saida_json_e_ascii(self):
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            mb.main(["--json"])
        texto = buf.getvalue()
        self.assertTrue(texto.isascii())
        self.assertIn("sessoes", json.loads(texto))

    def test_projeto_ignora_worktree_e_evidence(self):
        self.assertEqual(mb.pasta_do_projeto(r"S:\p\MEGA B R A I  N\.claude\worktrees\x"), "MEGA B R A I N")
        self.assertEqual(mb.pasta_do_projeto(r"S:\p\Bounty Hunter\evidence\261009_a"), "Bounty Hunter")


if __name__ == "__main__":
    unittest.main()
