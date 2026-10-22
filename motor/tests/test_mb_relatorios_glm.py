"""Gate contract tests. PNG fixtures are synthetic and never delivery evidence."""
import datetime as dt
import copy
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bin"))
import mb_relatorios_glm as glm
import mb_trava


def png(width, height=2):
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress((b"\0" + b"\xff" * (width * 3)) * height)) + chunk(b"IEND", b""))


class ReportGate(unittest.TestCase):
    def test_late_task_boundary_preserves_required_new_session(self):
        self.start();self.finish()
        for index in range(2,4):
            self.report.write_text(f'<html><body>Follow-up attempt {index}</body></html>',encoding='utf-8')
            glm.refresh(self.root,self.manifest,self.write_json(f'production-{index}.json',self.production()))
            glm.revise(self.root,self.manifest,self.write_json(f'review-{index}.json',self.review([self.finding()])))
        self.assertTrue(self.load()['requires_new_session'])
        request=self.write_json('human-request.json',{'kind':'human_followup','id':'late-task','human_request':'Atualizar cotas duas vezes por dia','session_id':'human-thread','at':glm.stamp()})
        glm.begin_task(self.root,self.manifest,request)
        self.assertTrue(self.load()['requires_new_session'])
        self.report.write_text('<html><body>Next follow-up attempt</body></html>',encoding='utf-8')
        with self.assertRaisesRegex(glm.GateError,'nova sessao GLM'):
            glm.refresh(self.root,self.manifest,self.write_json('production-next.json',self.production()))
        glm.refresh(self.root,self.manifest,self.write_json('production-new-session.json',self.production('new-session')))

    def test_distinct_human_task_keeps_history_and_new_limits(self):
        self.start();self.finish()
        request=self.write_json('human-request.json',{'kind':'human_followup','id':'next-task','human_request':'Atualizar cotas duas vezes todos os dias sem IA','session_id':'human-thread','at':glm.stamp()})
        glm.begin_task(self.root,self.manifest,request)
        self.assertEqual(self.load()['executions'][0]['start_cycle'],2)
        with self.assertRaisesRegex(glm.GateError,'registrado'):glm.begin_task(self.root,self.manifest,request)
        for index in range(2,6):
            if index>2:glm.revise(self.root,self.manifest,self.write_json(f'review-{index}.json',self.review()))
            self.report.write_text(f'<html><body>New task version {index}</body></html>',encoding='utf-8')
            prod=self.write_json(f'production-{index}.json',self.production('new-task-session'))
            if index<6:glm.refresh(self.root,self.manifest,prod)
        self.assertEqual(len(self.load()['history']),4)
        glm.revise(self.root,self.manifest,self.write_json('review-final.json',self.review()))
        self.report.write_text('<html><body>Extra attempt</body></html>',encoding='utf-8')
        prod=self.write_json('extra.json',self.production('new-task-session'))
        with self.assertRaisesRegex(glm.GateError,'tres correcoes'):glm.refresh(self.root,self.manifest,prod)

    def test_new_task_cannot_reset_failed_task_or_mutate_request(self):
        self.start()
        request=self.write_json('human-request.json',{'kind':'human_followup','id':'next-task','human_request':'Outra tarefa nova solicitada pelo usuario','session_id':'human-thread','at':glm.stamp()})
        with self.assertRaisesRegex(glm.GateError,'anterior entregue'):glm.begin_task(self.root,self.manifest,request)
        self.finish();glm.begin_task(self.root,self.manifest,request)
        other=self.write_json('other-request.json',{'kind':'human_followup','id':'another','human_request':'Outra tentativa sem entrega','session_id':'human-thread','at':glm.stamp()})
        with self.assertRaisesRegex(glm.GateError,'anterior entregue'):glm.begin_task(self.root,self.manifest,other)
        request.write_text('{}')
        with self.assertRaisesRegex(glm.GateError,'Evidencia alterada'):glm.current(self.root,self.load())

    def reach_session_limit(self):
        self.start()
        for index in range(1, 4):
            glm.revise(self.root, self.manifest, self.write_json(f"review{index}.json", self.review([self.finding()])))
            self.report.write_text(f"<html><body>Attempt {index+1}</body></html>", encoding="utf-8")
            prod = self.write_json(f"production{index+1}.json", self.production(f"glm-session-{index+1}"))
            if index < 3:
                glm.refresh(self.root, self.manifest, prod)
            else:
                with self.assertRaisesRegex(glm.GateError, "tres sessoes"):
                    glm.refresh(self.root, self.manifest, prod)

    def human_event(self, text, name="evento", event_uuid="evt-1", session="human-thread", content=None, kind="user",
                    timestamp=None, extra=None, crlf=False):
        record = {"type": kind, "uuid": event_uuid, "sessionId": session, "timestamp": timestamp or glm.stamp(),
                  "message": {"role": "user", "content": text if content is None else content}, **(extra or {})}
        line = json.dumps(record)
        end = "\r\n" if crlf else "\n"
        transcript = self.transcripts / f"{name}.jsonl"
        with transcript.open("a", encoding="utf-8", newline="") as handle:
            handle.write('{"type":"assistant"}' + end + line + end)
        excerpt = self.ev / f"{name.replace('/', '-')}-trecho.jsonl"
        excerpt.write_bytes((line + end).encode("utf-8"))
        return {"kind": "claude_transcript", "transcript": str(transcript), "event_uuid": event_uuid, "excerpt": str(excerpt)}

    def reframe(self, name, event, request_id=None, text="Destrave o REPORT com uma sessao GLM nova"):
        return self.write_json(f"{name}.json", {"kind": "human_reframe", "id": request_id or name, "human_request": text,
                                                "reason": "Limite de sessoes com candidato revogado",
                                                "session_id": "human-thread", "at": glm.stamp(), "human_event": event})

    def begin(self, request, manifest=None):
        return glm.begin_task(self.root, manifest or self.manifest, request, central=self.central)

    def revoke_current(self, name="limit", manifest=None):
        proof = self.ev / f"{name}.txt"
        proof.write_text("Gate stopped at the limit with an open finding.", encoding="utf-8")
        glm.revoke(self.root, manifest or self.manifest, "Limite de sessoes", [proof], central=self.central)

    def registry(self):
        path = self.central / ".automations/relatorios-glm/autorizacoes-humanas.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def test_human_reframe_requires_real_unconsumed_human_event(self):
        self.reach_session_limit()
        text = "Destrave o REPORT com uma sessao GLM nova"
        with mock.patch.object(glm, "TRANSCRIPT_ROOT", self.transcripts):
            # Slightly ahead (still within the 5 min tolerance) so the later reuse passes the time check
            # and must be stopped by consumption itself.
            soon = (glm.now() + dt.timedelta(minutes=2)).isoformat()
            event = self.human_event(text, crlf=True, timestamp=soon)
            stale_reuse = self.human_event(text, "reuso-antigo", "evt-13")
            missing =self.write_json("no-reason.json", {"kind": "human_reframe", "id": "x", "human_request": text,
                                                         "session_id": "human-thread", "at": glm.stamp(), "human_event": event})
            with self.assertRaisesRegex(glm.GateError, "origem e data"):
                self.begin(missing)
            with self.assertRaisesRegex(glm.GateError, "revogado"):
                self.begin(self.reframe("before-revoke", event))
            self.revoke_current()
            before = self.manifest.read_bytes()
            unnamed = "Destrave com uma sessao GLM nova"
            contained = "Destrave o REPORT-OUTRO com uma sessao GLM nova"
            bad = [
                ("evento humano real", {**event, "kind": "declared"}, text),
                ("nao nomeia", self.human_event(unnamed, "sem-nome", "evt-2"), unnamed),
                ("nao nomeia", self.human_event(contained, "nome-contido", "evt-12"), contained),
                ("nao nomeia", self.human_event("Destrave o REPORT.OUTRO.html com uma sessao GLM nova", "nome-ponto", "evt-14"),
                 "Destrave o REPORT.OUTRO.html com uma sessao GLM nova"),
                ("futura", self.human_event(text, "futuro", "evt-15", timestamp=(glm.now() + dt.timedelta(minutes=10)).isoformat()), text),
                ("difere", self.human_event("Destrave o REPORT depois", "outro-texto", "evt-3"), text),
                ("digitada", self.human_event(text, "ferramenta", "evt-4", content=[{"type": "tool_result", "content": text}]), text),
                ("digitada", self.human_event(text, "meta", "evt-7", extra={"isMeta": True}), text),
                ("digitada", self.human_event(text, "lateral", "evt-8", extra={"isSidechain": True}), text),
                ("digitada", {**self.human_event(text, "uuid-trocado", "evt-11"), "event_uuid": "evt-outro"}, text),
                ("sessao declarada", self.human_event(text, "outra-sessao", "evt-5", session="other-thread"), text),
                ("anterior ao candidato", self.human_event(text, "antigo", "evt-10", timestamp="2026-01-01T00:00:00+00:00"), text),
            ]
            for index, (message, value, request_text) in enumerate(bad):
                with self.assertRaisesRegex(glm.GateError, message):
                    self.begin(self.reframe(f"bad-{index}", value, text=request_text))
            forged = self.ev / "forjado-trecho.jsonl"
            forged.write_text(json.dumps({"type": "user", "uuid": "evt-9", "sessionId": "human-thread", "timestamp": glm.stamp(),
                                          "message": {"role": "user", "content": text}}), encoding="utf-8")
            with self.assertRaisesRegex(glm.GateError, "nao existe no transcript"):
                self.begin(self.reframe("forged", {**event, "event_uuid": "evt-9", "excerpt": str(forged)}))
            outside = self.root / "fora.jsonl"
            outside.write_bytes(Path(event["excerpt"]).read_bytes())
            with self.assertRaisesRegex(glm.GateError, "fora da pasta"):
                self.begin(self.reframe("outside", {**event, "transcript": str(outside)}))
            self.assertEqual(self.manifest.read_bytes(), before)
            self.assertIsNone(self.registry())
            self.begin(self.reframe("reframe-1", event))
            execution = self.load()["executions"][0]
            self.assertEqual(execution["start_cycle"], 4)
            self.assertEqual(execution["human_event"]["event_uuid"], "evt-1")
            self.assertEqual(set(execution["excluded_sessions"]), {"glm-session-1", "glm-session-2", "glm-session-3"})
            self.assertEqual(self.registry()["events"]["evt-1"]["revoked_cycle"], 3)
            with self.assertRaisesRegex(glm.GateError, "pendente"):
                self.begin(self.reframe("reframe-dup", self.human_event(text, "dup", "evt-6")))
            with self.assertRaisesRegex(glm.GateError, "inedita"):
                glm.refresh(self.root, self.manifest, self.write_json("production-reused.json", self.production("glm-session-3")))
            glm.refresh(self.root, self.manifest, self.write_json("production-new.json", self.production("glm-session-new")))
            self.assertIsNotNone(self.load()["history"][-1]["revocation"])
            glm.revise(self.root, self.manifest, self.write_json("review-new.json", self.review([self.finding()])))
            self.revoke_current("limit-2")
            with self.assertRaisesRegex(glm.GateError, "consumida neste manifesto"):
                self.begin(self.reframe("reframe-reuse", event, "reframe-reuse"))
            with self.assertRaisesRegex(glm.GateError, "anterior ao candidato"):
                self.begin(self.reframe("reframe-stale", stale_reuse))
            Path(event["excerpt"]).write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(glm.GateError, "Evidencia alterada"):
                glm.current(self.root, self.load())

    def test_one_human_event_cannot_reframe_another_report(self):
        self.reach_session_limit()
        other = self.root / "00_PARA-VOCE/outra/REPORT.html"
        other.parent.mkdir(parents=True)
        other.write_text("<html><body>Outro relatorio com o mesmo nome</body></html>", encoding="utf-8")
        manifest_b = self.ev / "manifest-b.json"
        glm.init(self.root, manifest_b, other,
                 self.write_json("production-b.json", {**self.production("glm-b"), "text": other.read_text(encoding="utf-8")}))
        with mock.patch.object(glm, "TRANSCRIPT_ROOT", self.transcripts):
            self.revoke_current()
            self.revoke_current("limit-b", manifest_b)
            text = "Destrave o REPORT.html, com uma sessao GLM nova."
            event = self.human_event(text)
            self.begin(self.reframe("reframe-a", event, text=text))
            before = manifest_b.read_bytes()
            with self.assertRaisesRegex(glm.GateError, "outro relatorio"):
                self.begin(self.reframe("reframe-b", event, "reframe-b", text=text), manifest_b)
            self.assertEqual(manifest_b.read_bytes(), before)
            self.assertEqual(list(self.registry()["events"]), ["evt-1"])

    def test_human_reframe_after_delivery_is_refused(self):
        self.start()
        self.finish()
        before = self.manifest.read_bytes()
        with mock.patch.object(glm, "TRANSCRIPT_ROOT", self.transcripts):
            with self.assertRaisesRegex(glm.GateError, "human_followup"):
                self.begin(self.reframe("late", self.human_event("Destrave o REPORT com uma sessao GLM nova")))
        self.assertIsNone(self.registry())
        self.assertEqual(self.manifest.read_bytes(), before)

    def test_transcript_through_linked_folder_is_refused(self):
        self.reach_session_limit()
        real = self.transcripts / "real"
        real.mkdir()
        link = self.transcripts / "atalho"
        try:
            if os.name == "nt":
                import _winapi
                _winapi.CreateJunction(str(real), str(link))
            else:
                os.symlink(real, link, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"link indisponivel neste sistema: {exc}")
        text = "Destrave o REPORT com uma sessao GLM nova"
        with mock.patch.object(glm, "TRANSCRIPT_ROOT", self.transcripts):
            self.revoke_current()
            event = self.human_event(text, "real/evento")
            before = self.manifest.read_bytes()
            with self.assertRaisesRegex(glm.GateError, "Link proibido"):
                self.begin(self.reframe("via-link", {**event, "transcript": str(link / "evento.jsonl")}))
            self.assertEqual(self.manifest.read_bytes(), before)
            self.assertIsNone(self.registry())
            self.begin(self.reframe("direto", event))

    def test_two_processes_compete_for_one_human_event(self):
        child = (
            "import sys, time\n"
            "from pathlib import Path\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "import mb_relatorios_glm as glm\n"
            "glm.TRANSCRIPT_ROOT = Path(sys.argv[2])\n"
            "go = Path(sys.argv[6])\n"
            "while not go.exists():\n"
            "    time.sleep(0.005)\n"
            "try:\n"
            "    glm.begin_task(sys.argv[3], sys.argv[4], sys.argv[5], central=sys.argv[7])\n"
            "    print('OK')\n"
            "except Exception as exc:\n"
            "    print('RECUSADO', type(exc).__name__, exc)\n")
        projects = []
        for label in ("a", "b"):
            root = Path(tempfile.mkdtemp(prefix=f"proj-{label}-")).resolve()
            self.addCleanup(shutil.rmtree, root, True)
            report = root / "00_PARA-VOCE/t/REPORT.html"
            report.parent.mkdir(parents=True)
            report.write_text(f"<html><body>Projeto {label}</body></html>", encoding="utf-8")
            ev = root / "evidence/t"
            ev.mkdir(parents=True)
            prod = ev / "production.json"
            prod.write_text(json.dumps({**self.production(f"glm-{label}"), "text": report.read_text(encoding="utf-8")}), encoding="utf-8")
            manifest = ev / "manifest.json"
            glm.init(root, manifest, report, prod)
            proof = ev / "limit.txt"
            proof.write_text("Gate stopped at the limit.", encoding="utf-8")
            glm.revoke(root, manifest, "Limite de sessoes", [proof], central=self.central)
            projects.append((root, manifest, ev))
        text = "Destrave o REPORT com uma sessao GLM nova"
        event = self.human_event(text)
        go = self.root / "go.flag"
        processes, before = [], {}
        for root, manifest, ev in projects:
            excerpt = ev / "evento.jsonl"
            excerpt.write_bytes(Path(event["excerpt"]).read_bytes())
            request = ev / "pedido.json"
            request.write_text(json.dumps({"kind": "human_reframe", "id": "reframe", "human_request": text,
                                           "reason": "Limite de sessoes", "session_id": "human-thread", "at": glm.stamp(),
                                           "human_event": {**event, "excerpt": str(excerpt)}}), encoding="utf-8")
            before[manifest] = manifest.read_bytes()
            processes.append(subprocess.Popen(
                [sys.executable, "-c", child, str(ROOT / "bin"), str(self.transcripts), str(root), str(manifest),
                 str(request), str(go), str(self.central)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
        go.write_text("go", encoding="utf-8")
        outputs = [p.communicate(timeout=60)[0].strip() for p in processes]
        self.assertEqual(sum(line == "OK" for line in outputs), 1, outputs)
        self.assertEqual(len(self.registry()["events"]), 1)
        loser = projects[[line == "OK" for line in outputs].index(False)][1]
        self.assertEqual(loser.read_bytes(), before[loser])

    def test_registry_lock_and_write_failures_are_conservative(self):
        self.reach_session_limit()
        registry_path = self.central / ".automations/relatorios-glm/autorizacoes-humanas.json"
        real_atomic = glm._atomic
        def fail_on(name):
            def write(path, data):
                if Path(path).name == name:
                    raise OSError("disk unavailable")
                return real_atomic(path, data)
            return write
        with mock.patch.object(glm, "TRANSCRIPT_ROOT", self.transcripts):
            self.revoke_current()
            request = self.reframe("reframe-1", self.human_event("Destrave o REPORT com uma sessao GLM nova"))
            before = self.manifest.read_bytes()
            registry_path.parent.mkdir(parents=True)
            with mb_trava.travado(registry_path, "outro-projeto-real", raiz=self.central):
                with self.assertRaises(mb_trava.TravaOcupada):
                    self.begin(request)
            self.assertEqual(self.manifest.read_bytes(), before)
            self.assertIsNone(self.registry())
            with mock.patch.object(glm, "_atomic", side_effect=fail_on(registry_path.name)):
                with self.assertRaises(OSError):
                    self.begin(request)
            self.assertEqual(self.manifest.read_bytes(), before)
            self.assertIsNone(self.registry())
            with mock.patch.object(glm, "_atomic", side_effect=fail_on(self.manifest.name)):
                with self.assertRaises(OSError):
                    self.begin(request)
            self.assertEqual(self.manifest.read_bytes(), before)
            self.assertIn("evt-1", self.registry()["events"])
            with self.assertRaisesRegex(glm.GateError, "outro relatorio ou manifesto"):
                self.begin(request)
            self.assertEqual(self.manifest.read_bytes(), before)

    def test_human_reframe_restarts_limits_and_keeps_revoked_findings(self):
        self.reach_session_limit()
        with mock.patch.object(glm, "TRANSCRIPT_ROOT", self.transcripts):
            self.revoke_current()
            self.begin(self.reframe("reframe-1", self.human_event("Destrave o REPORT com uma sessao GLM nova")))
        for number, session in ((4, "new-1"), (5, "new-2"), (6, "new-3")):
            self.report.write_text(f"<html><body>Reframe {number}</body></html>", encoding="utf-8")
            glm.refresh(self.root, self.manifest, self.write_json(f"production-r{number}.json", self.production(session)))
            if number == 4:
                with self.assertRaisesRegex(glm.GateError, "omitidos"):
                    glm.revise(self.root, self.manifest, self.write_json("review-r4-omit.json", self.review()))
            glm.revise(self.root, self.manifest, self.write_json(f"review-r{number}.json", self.review([self.finding()])))
        self.report.write_text("<html><body>Reframe 7</body></html>", encoding="utf-8")
        with self.assertRaisesRegex(glm.GateError, "tres sessoes"):
            glm.refresh(self.root, self.manifest, self.write_json("production-r7-new.json", self.production("new-4")))
        glm.refresh(self.root, self.manifest, self.write_json("production-r7.json", self.production("new-3")))
        glm.revise(self.root, self.manifest, self.write_json("review-r7.json", self.review([self.finding()])))
        self.report.write_text("<html><body>Reframe 8</body></html>", encoding="utf-8")
        with self.assertRaisesRegex(glm.GateError, "tres correcoes"):
            glm.refresh(self.root, self.manifest, self.write_json("production-r8.json", self.production("new-3")))
        self.assertEqual(self.load()["current"]["number"], 7)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.report = self.root / "00_PARA-VOCE/task/REPORT.html"
        self.report.parent.mkdir(parents=True)
        self.report.write_text("<!doctype html><html><body><main>GLM output 1</main></body></html>", encoding="utf-8")
        self.ev = self.root / "evidence/task"
        self.ev.mkdir(parents=True)
        self.manifest = self.ev / "manifest.json"
        self.prod = self.write_json("production1.json", self.production())
        (self.ev / "functional.log").write_text("links, cursor, responsive: verified in test fixture", encoding="utf-8")
        for width in (1440, 390):
            (self.ev / f"view-{width}.png").write_bytes(png(width))
        self.transcripts = self.root / "transcripts"
        self.transcripts.mkdir()
        self.central = self.root / "central-registry"
        self.central.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def production(self, session="glm-session-1"):
        return {"vendor": "glm", "session_id": session, "status": "completed", "exit_code": 0,
                "actual_model": "GLM-5.3", "effort_requested": "max", "effort_verified": True,
                "model_io_metadata": [{"model": {"modelId": "GLM-5.3"}, "body_effort": "max", "provider_effort": "max"}],
                "text": self.report.read_text(encoding="utf-8")}

    def write_json(self, name, value):
        path = self.ev / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def start(self, **kwargs):
        return glm.init(self.root, self.manifest, self.report, self.prod, **kwargs)

    def load(self):
        return json.loads(self.manifest.read_text(encoding="utf-8"))

    def review(self, findings=None, reviewer=None):
        return {"artifact_sha256": self.load()["current"]["artifact"]["sha256"],
                "reviewer": reviewer or {"vendor": "codex", "session_id": "codex-review-real"},
                "criteria": [{"id": key, "verdict": "pass", "observation": f"Observed {key} in fixture",
                              "evidence": [str(self.ev / "view-1440.png")]} for key in sorted(glm.CRITERIA)],
                "findings": findings or []}

    def inspection(self):
        return {"artifact_sha256": self.load()["current"]["artifact"]["sha256"],
                "inspector": {"vendor": "codex", "session_id": "codex-visual-real"}, "actually_viewed": True,
                "captures": [{"viewport_width": w, "path": str(self.ev / f"view-{w}.png"),
                              "observation": "No clipping in synthetic test fixture", "verdict": "pass"} for w in (1440, 390)],
                "tests": [{"command": "fixture-functional-check", "exit_code": 0,
                           "observation": "fixture links work", "log": str(self.ev / "functional.log")}]}

    def finish(self):
        glm.revise(self.root, self.manifest, self.write_json("review.json", self.review()))
        glm.verify(self.root, self.manifest, self.write_json("inspection.json", self.inspection()))
        glm.deliver(self.root, self.manifest)

    def finding(self):
        return {"id": "F1", "criterion": "hierarchy", "status": "open", "observation": "Two headings compete",
                "evidence": [str(self.ev / "view-1440.png")]}

    def test_closed_gate_and_promotion(self):
        self.start()
        with self.assertRaises(glm.GateError):
            glm.deliver(self.root, self.manifest)
        self.finish()
        self.assertEqual(glm.status(self.root, self.manifest)["state"], "ready")
        dest = self.root / "central"
        dest.mkdir()
        index_path = dest / "motor/modelos/relatorios/glm/indice.json"
        index_path.parent.mkdir(parents=True)
        index_path.write_text(json.dumps({"schema_version": 1, "master": "master-untouched.html",
            "references": [{"id": "master", "path": "original.html"}], "candidates": [], "promoted": []}), encoding="utf-8")
        glm.promote(self.root, self.manifest, "fixture-example", central=dest)
        promoted = self.load()["current"]["promoted"][0]["path"]
        self.assertTrue((Path(promoted) / "provenance.json").is_file())
        self.assertEqual((Path(promoted) / self.report.relative_to(self.root)).read_bytes(), self.report.read_bytes())
        self.assertIn("glm/promovidos", Path(promoted).as_posix())
        index = json.loads(index_path.read_text(encoding="utf-8"))
        self.assertEqual(index["master"], "master-untouched.html")
        self.assertEqual(index["references"], [{"id": "master", "path": "original.html"}])
        self.assertEqual(index["promoted"][0]["human_approval"], "NAO_MEDIDO")
        self.assertEqual(index["promoted"][0]["technical_approval"], "VERIFICADO_TECNICAMENTE")
        self.assertTrue((Path(promoted) / self.ev.relative_to(self.root) / "view-390.png").is_file())

    def test_glm_main_real_effort_and_text_are_required(self):
        for change in ({"actual_model": "GLM-5.3-Flash"}, {"effort_verified": False},
                       {"model_io_metadata": []}, {"status": "effort_unverified"},
                       {"text": "unrelated generation"}, {"exit_code": False}):
            with self.subTest(change=change):
                self.prod.write_text(json.dumps({**self.production(), **change}), encoding="utf-8")
                with self.assertRaises(glm.GateError):
                    self.start()
        self.assertFalse(self.manifest.exists())

    def test_literal_fragment_mechanical_compose(self):
        fragment = "<style>.glm-report{color:#111}</style><main class=\"wrap glm-report\">Done</main>"
        self.prod.write_text(json.dumps({**self.production(), "text": "```html\n" + fragment + "\n```"}), encoding="utf-8")
        source = self.ev / "fragment.html"
        source.write_text(fragment, encoding="utf-8")
        self.report.write_text("<!doctype html><html><head></head><body>" + fragment + "<details>History</details></body></html>", encoding="utf-8")
        self.start(fragment=source)
        self.assertEqual(self.load()["current"]["mechanical_integration"]["method"], "compose-pop-cursor-history")
        source.write_text("human edited", encoding="utf-8")
        with self.assertRaisesRegex(glm.GateError, "Evidencia alterada"):
            glm.current(self.root, self.load())

    def test_self_review_and_trivial_pass_are_rejected(self):
        self.start()
        for review in ({"passed": True}, self.review(reviewer={"vendor": "codex", "session_id": "glm-session-1"})):
            with self.assertRaises(glm.GateError):
                glm.revise(self.root, self.manifest, self.write_json("review.json", review))
        self.assertIsNone(self.load()["current"]["review"])

    def test_actual_visual_width_observation_and_hash(self):
        self.start()
        inspection = self.inspection()
        inspection["actually_viewed"] = False
        with self.assertRaises(glm.GateError):
            glm.verify(self.root, self.manifest, self.write_json("inspection.json", inspection))
        (self.ev / "view-390.png").write_bytes(png(391))
        with self.assertRaisesRegex(glm.GateError, "Largura real"):
            glm.verify(self.root, self.manifest, self.write_json("inspection.json", self.inspection()))
        (self.ev / "view-390.png").write_bytes(png(390))
        self.finish()
        (self.ev / "view-390.png").write_bytes(png(390, 3))
        self.assertEqual(glm.status(self.root, self.manifest)["state"], "blocked")

    def test_corrupt_png_rejected(self):
        self.start()
        path = self.ev / "view-390.png"
        path.write_bytes(path.read_bytes()[:-8])
        with self.assertRaises(glm.GateError):
            glm.verify(self.root, self.manifest, self.write_json("inspection.json", self.inspection()))

    def test_resource_mutation_invalidates_delivery(self):
        image = self.report.parent / "image.png"
        image.write_bytes(png(60))
        self.report.write_text('<html><body><img src="image.png"></body></html>', encoding="utf-8")
        self.prod.write_text(json.dumps(self.production()), encoding="utf-8")
        self.start()
        self.finish()
        image.write_bytes(png(70))
        self.assertIn("Artefato alterado", glm.status(self.root, self.manifest)["reason"])
        self.assertIsNone(glm.status(self.root, self.manifest)["delivered_at"])

    def test_source_and_log_mutations_invalidate(self):
        self.start()
        self.finish()
        (self.ev / "functional.log").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(glm.GateError, "Evidencia alterada"):
            glm.deliver(self.root, self.manifest)

    def test_new_cycle_preserves_history_and_open_findings_cannot_disappear(self):
        self.start()
        glm.revise(self.root, self.manifest, self.write_json("review1.json", self.review([self.finding()])))
        self.report.write_text("<html><body>GLM revised hierarchy</body></html>", encoding="utf-8")
        next_prod = self.write_json("production2.json", self.production())
        glm.refresh(self.root, self.manifest, next_prod)
        self.assertEqual(len(self.load()["history"]), 1)
        with self.assertRaisesRegex(glm.GateError, "omitidos"):
            glm.revise(self.root, self.manifest, self.write_json("review2.json", self.review()))
        resolved = {**self.finding(), "status": "resolved", "resolution": "Single heading priority", "acceptance_test": "Compare heading sizes"}
        glm.revise(self.root, self.manifest, self.write_json("review2.json", self.review([resolved])))
        glm.verify(self.root, self.manifest, self.write_json("inspection.json", self.inspection()))
        glm.deliver(self.root, self.manifest)

    def test_two_corrections_without_progress_require_new_session(self):
        self.start()
        for index in range(1, 4):
            glm.revise(self.root, self.manifest, self.write_json(f"review{index}.json", self.review([self.finding()])))
            if index < 3:
                self.report.write_text(f"<html><body>Attempt {index}</body></html>", encoding="utf-8")
                glm.refresh(self.root, self.manifest, self.write_json(f"production{index+1}.json", self.production()))
        self.assertTrue(self.load()["requires_new_session"])
        self.report.write_text("<html><body>Attempt 4</body></html>", encoding="utf-8")
        with self.assertRaisesRegex(glm.GateError, "nova sessao GLM"):
            glm.refresh(self.root, self.manifest, self.write_json("production4.json", self.production()))
        glm.refresh(self.root, self.manifest, self.write_json("production4.json", self.production("glm-new-session")))

    def test_credit_fallback_unknown_stale_and_helpful_reset_rejected(self):
        self.prod.write_text(json.dumps({**self.production("codex-fallback"), "vendor": "codex", "actual_model": "gpt-6-astra"}), encoding="utf-8")
        deadline = (glm.now() + dt.timedelta(hours=1)).isoformat()
        base = {"vendor": "glm", "status": "observed", "account": "subscription-real",
                "observed_at": glm.stamp(), "all_applicable_windows_confirmed": True,
                "windows": [{"name": "subscription", "remaining_percent": 4, "reset_at": (glm.now() + dt.timedelta(hours=3)).isoformat()}]}
        cases = [{**base, "status": "tool_error"}, {**base, "all_applicable_windows_confirmed": False},
                 {**base, "observed_at": (glm.now() - dt.timedelta(hours=1)).isoformat()},
                 {**base, "windows": [{"name": "subscription", "remaining_percent": None}]},
                 {**base, "windows": [{"name": "subscription", "remaining_percent": 4, "reset_at": (glm.now() + dt.timedelta(minutes=30)).isoformat()}]}]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(glm.GateError):
                self.start(exception=self.write_json("credit.json", case), deadline=deadline)
        self.start(exception=self.write_json("credit.json", base), deadline=deadline)
        self.assertIsNotNone(self.load()["current"]["production"]["exception"])

    def test_path_escape_and_held_lock_leave_no_manifest(self):
        with self.assertRaises(glm.GateError):
            glm.init(self.root, "../escape.json", self.report, self.prod)
        with mb_trava.travado(self.manifest, "another-real-session", raiz=self.root):
            with self.assertRaises(mb_trava.TravaOcupada):
                self.start()
        self.assertFalse(self.manifest.exists())

    def test_remote_render_resource_blocks_final_gate(self):
        self.report.write_text('<html><body><img src="https://example.test/render.png"></body></html>', encoding="utf-8")
        self.prod.write_text(json.dumps(self.production()), encoding="utf-8")
        self.start()
        with self.assertRaisesRegex(glm.GateError, "Recursos remotos"):
            self.finish()

    def test_failed_transaction_does_not_change_manifest(self):
        self.start()
        before = self.manifest.read_bytes()
        with mock.patch.object(glm, "_atomic", side_effect=OSError("disk unavailable")):
            with self.assertRaises(OSError):
                glm.revise(self.root, self.manifest, self.write_json("review.json", self.review()))
        self.assertEqual(before, self.manifest.read_bytes())
        self.assertIsNone(mb_trava.ler(self.manifest, raiz=self.root))

    def test_index_missing_corrupt_and_missing_manifest_are_distinct(self):
        self.assertIsNone(glm.find_manifest(self.root, self.report))
        self.start()
        self.assertEqual(glm.find_manifest(self.root, self.report), self.manifest)
        self.manifest.unlink()
        with self.assertRaisesRegex(glm.GateError, "associado ausente"):
            glm.find_manifest(self.root, self.report)
        index = self.root / ".automations/relatorios-glm/index.json"
        index.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(glm.GateError, "corrompido"):
            glm.find_manifest(self.root, self.report)

    def test_cannot_reassign_report_to_another_manifest(self):
        self.start()
        alternate = self.ev / "another-manifest.json"
        with self.assertRaisesRegex(glm.GateError, "canonico"):
            glm.init(self.root, alternate, self.report, self.prod)
        self.assertFalse(alternate.exists())

    def test_limit_three_sessions_is_enforced(self):
        self.start()
        for index in range(1, 4):
            glm.revise(self.root, self.manifest, self.write_json(f"review{index}.json", self.review([self.finding()])))
            self.report.write_text(f"<html><body>New session {index}</body></html>", encoding="utf-8")
            prod = self.write_json(f"production{index+1}.json", self.production(f"glm-session-{index+1}"))
            if index < 3:
                glm.refresh(self.root, self.manifest, prod)
            else:
                with self.assertRaisesRegex(glm.GateError, "tres sessoes"):
                    glm.refresh(self.root, self.manifest, prod)

    def test_self_observation_and_empty_functional_log_rejected(self):
        self.start()
        inspection = self.inspection()
        inspection["inspector"]["session_id"] = "glm-session-1"
        with self.assertRaisesRegex(glm.GateError, "outra sessao"):
            glm.verify(self.root, self.manifest, self.write_json("inspection.json", inspection))
        (self.ev / "functional.log").write_text("", encoding="utf-8")
        with self.assertRaisesRegex(glm.GateError, "vazio"):
            glm.verify(self.root, self.manifest, self.write_json("inspection.json", self.inspection()))

    def test_path_escape_in_report_resource_rejected(self):
        self.report.write_text('<html><body><img src="../../../../outside.png"></body></html>', encoding="utf-8")
        self.prod.write_text(json.dumps(self.production()), encoding="utf-8")
        with self.assertRaises((glm.GateError, FileNotFoundError)):
            self.start()

    def test_normalized_review_cannot_hide_open_findings_or_criteria(self):
        self.start()
        glm.revise(self.root, self.manifest, self.write_json("review.json", self.review([self.finding()])))
        glm.verify(self.root, self.manifest, self.write_json("inspection.json", self.inspection()))
        original = self.load()
        for field, replacement in (("findings", []), ("criteria", []),
                                   ("reviewer", {"vendor": "human", "session_id": "fiction"})):
            data = copy.deepcopy(original)
            data["current"]["review"][field] = replacement
            with self.subTest(field=field), self.assertRaisesRegex(glm.GateError, "diverge"):
                glm.gate(self.root, data)

    def test_normalized_inspection_cannot_drop_verdict_or_rewrite_command(self):
        self.start()
        self.finish()
        original = self.load()
        data = copy.deepcopy(original)
        data["current"]["visual"][0].pop("verdict")
        with self.assertRaisesRegex(glm.GateError, "diverge"):
            glm.gate(self.root, data)
        data = copy.deepcopy(original)
        data["current"]["tests"][0]["command"] = "invented"
        with self.assertRaisesRegex(glm.GateError, "diverge"):
            glm.gate(self.root, data)

    def test_svg_href_and_xlink_resources_are_hash_bound(self):
        image = self.report.parent / "photo.png"
        image.write_bytes(png(60))
        svg = self.report.parent / "render.svg"
        svg.write_text('<svg><image href="photo.png"/><feImage xlink:href="photo.png"/></svg>', encoding="utf-8")
        self.report.write_text('<html><body><img src="render.svg"></body></html>', encoding="utf-8")
        self.prod.write_text(json.dumps(self.production()), encoding="utf-8")
        self.start()
        self.assertIn(str(image.relative_to(self.root)), self.load()["current"]["artifact"]["files"])
        image.write_bytes(png(61))
        self.assertIn("Artefato alterado", glm.status(self.root, self.manifest)["reason"])

    def test_revoke_removes_active_reference_and_keeps_provenance(self):
        self.start()
        self.finish()
        central = self.root / "central"
        central.mkdir()
        glm.promote(self.root, self.manifest, "accepted-before", central=central)
        target = Path(self.load()["current"]["promoted"][0]["path"])
        before = (target / "provenance.json").read_bytes()
        rejection = self.ev / "human-rejection.txt"
        rejection.write_text("This composition was rejected; retain evidence.", encoding="utf-8")
        glm.revoke(self.root, self.manifest, "Hierarchy failed user expectation", [rejection], central=central)
        index = json.loads((central / "motor/modelos/relatorios/glm/indice.json").read_text(encoding="utf-8"))
        self.assertEqual(index["promoted"], [])
        self.assertEqual(index["candidates"][0]["status"], "rejected")
        self.assertEqual(len(index["revocations"]), 1)
        self.assertEqual((target / "provenance.json").read_bytes(), before)
        self.assertIn("revogado", glm.status(self.root, self.manifest)["reason"])
        # Even dropping the local marker cannot reactivate a revoked library hash.
        data = self.load()
        data["current"]["revocation"] = None
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(glm.GateError, "revogado"):
            glm.promote(self.root, self.manifest, "different-slug", central=central)

    def test_revoke_candidate_without_final_gate_and_without_deleting(self):
        self.start()
        central = self.root / "central"
        central.mkdir()
        proof = self.ev / "rejection.txt"
        proof.write_text("Observed wrong visual hierarchy in candidate.", encoding="utf-8")
        glm.revoke(self.root, self.manifest, "Observed visual defect", [proof], central=central)
        self.assertTrue(self.report.exists())
        self.assertTrue(self.prod.exists())
        self.assertIsNotNone(self.load()["current"]["revocation"])

    def test_three_corrections_cap_applies_even_with_progress_same_session(self):
        self.start()
        for number in range(1, 5):
            review = self.review([self.finding()])
            for criterion in review["criteria"][:4-number]:
                criterion["verdict"] = "fail"
            glm.revise(self.root, self.manifest, self.write_json(f"review{number}.json", review))
            self.assertFalse(self.load()["requires_new_session"])
            self.report.write_text(f"<html><body>Progress version {number+1}</body></html>", encoding="utf-8")
            prod = self.write_json(f"production{number+1}.json", self.production())
            if number < 4:
                glm.refresh(self.root, self.manifest, prod)
            else:
                with self.assertRaisesRegex(glm.GateError, "tres correcoes"):
                    glm.refresh(self.root, self.manifest, prod)

    def test_fallback_exception_cannot_be_removed_and_stays_valid_at_original_time(self):
        self.prod.write_text(json.dumps({**self.production("codex-fallback"), "vendor": "codex", "actual_model": "gpt-6-astra"}), encoding="utf-8")
        deadline = (glm.now() + dt.timedelta(hours=1)).isoformat()
        credit = {"vendor": "glm", "status": "observed", "account": "subscription-real",
                  "observed_at": glm.stamp(), "all_applicable_windows_confirmed": True,
                  "windows": [{"name": "subscription", "remaining_percent": 4, "reset_at": None, "reset_absence_confirmed": True}]}
        self.start(exception=self.write_json("credit.json", credit), deadline=deadline)
        original = self.load()
        data = copy.deepcopy(original)
        data["current"]["production"]["exception"] = None
        with self.assertRaisesRegex(glm.GateError, "excecao de credito"):
            glm.current(self.root, data)
        later = glm.now() + dt.timedelta(days=1)
        with mock.patch.object(glm, "now", return_value=later):
            glm.current(self.root, original)


if __name__ == "__main__":
    unittest.main()
