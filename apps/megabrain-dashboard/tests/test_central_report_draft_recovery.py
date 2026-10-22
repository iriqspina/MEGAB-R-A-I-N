"""Rascunho de relatório não se perde entre versões (261014, pedido do <USUARIO>).

1. A view de uma versão nova sem rascunho recupera o rascunho mais recente do
   mesmo relatório (notas da versão anterior voltam com posição e rótulo).
2. Rascunho da versão atual continua na frente; outros relatórios não vazam.
3. No boot do relatório, chaves versionadas (mb-*:hash) migram para o hash
   atual, preservando id, posição e rótulo (onde estava e o que significava).
"""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(APP), str(APP / "runtime-packages")]

from central_store import Store  # noqa: E402
from central_sources import Sources  # noqa: E402
from central_server import build_app, secret_file  # noqa: E402
from central_reports import BOOTSTRAP  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

PROJETOS = Path(r"<PROJETOS_ROOT>")
TICKET = "synthetic_draft_recovery_261014"


class RascunhoEntreVersoes(unittest.TestCase):
    def _abrir(self, tmp):
        store = Store(Path(tmp) / "t.sqlite3")
        sources = Sources(store, parent=PROJETOS)
        projeto = Path(tmp) / "proj"
        (projeto / "00_PARA-VOCE").mkdir(parents=True)
        return store, sources, projeto

    def _par(self, client):
        r = client.post("/api/pair", json={"code": secret_file("native.key")})
        self.assertEqual(200, r.status_code, r.text)
        return {"X-MB-CSRF": r.json()["csrf"]}

    def test_view_recupera_rascunho_da_versao_anterior(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, sources, projeto = self._abrir(tmp)
            alvo = projeto / "00_PARA-VOCE" / "r.html"
            alvo.write_text("<!doctype html><p>v1</p>", encoding="utf-8")
            fid = sources.index_file(alvo, projeto)["id"]
            with TestClient(build_app(store=store, sources=sources)) as client:
                csrf = self._par(client)
                h1 = hashlib.sha256(alvo.read_bytes()).hexdigest()
                nota = json.dumps([{"id": "n1", "texto": "aperta aqui", "onde": "perto de: botão salvar", "px": 300, "py": 500}], ensure_ascii=False)
                r = client.post(f"/api/reports/{fid}/draft", json={"hash": h1, "storage": {"mb-report-notas:%s:%s" % (fid, h1): nota}}, headers=csrf)
                self.assertEqual(200, r.status_code, r.text)
                # versão nova do mesmo arquivo, ainda sem rascunho próprio
                alvo.write_text("<!doctype html><p>v2 — outra cara</p>", encoding="utf-8")
                html = client.get(f"/api/reports/{fid}/view?ticket={TICKET}").text
                self.assertIn("aperta aqui", html)
                self.assertIn("perto de: botão salvar", html)
                # rascunho da versão atual continua na frente do antigo
                h2 = hashlib.sha256(alvo.read_bytes()).hexdigest()
                client.post(f"/api/reports/{fid}/draft", json={"hash": h2, "storage": {"atual": "sim"}}, headers=csrf)
                html = client.get(f"/api/reports/{fid}/view?ticket={TICKET}").text
                self.assertIn("atual", html)
                self.assertNotIn("aperta aqui", html)

    def test_rascunho_vazio_de_proposito_nao_revive_notas(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, sources, projeto = self._abrir(tmp)
            alvo = projeto / "00_PARA-VOCE" / "r.html"
            alvo.write_text("<!doctype html><p>v1</p>", encoding="utf-8")
            fid = sources.index_file(alvo, projeto)["id"]
            with TestClient(build_app(store=store, sources=sources)) as client:
                csrf = self._par(client)
                h1 = hashlib.sha256(alvo.read_bytes()).hexdigest()
                nota = json.dumps([{"id": "n1", "texto": "apagar depois"}], ensure_ascii=False)
                client.post(f"/api/reports/{fid}/draft", json={"hash": h1, "storage": {"mb-report-notas:%s:%s" % (fid, h1): nota}}, headers=csrf)
                # versão nova e o usuário LIMPO as notas de propósito (storage vazio gravado)
                alvo.write_text("<!doctype html><p>v2</p>", encoding="utf-8")
                h2 = hashlib.sha256(alvo.read_bytes()).hexdigest()
                client.post(f"/api/reports/{fid}/draft", json={"hash": h2, "storage": {}}, headers=csrf)
                html = client.get(f"/api/reports/{fid}/view?ticket={TICKET}").text
                self.assertNotIn("apagar depois", html)

    def test_rascunho_nao_vaza_entre_relatorios(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, sources, projeto = self._abrir(tmp)
            a = projeto / "00_PARA-VOCE" / "a.html"
            b = projeto / "00_PARA-VOCE" / "b.html"
            a.write_text("<!doctype html><p>a</p>", encoding="utf-8")
            b.write_text("<!doctype html><p>b</p>", encoding="utf-8")
            fid_a = sources.index_file(a, projeto)["id"]
            fid_b = sources.index_file(b, projeto)["id"]
            with TestClient(build_app(store=store, sources=sources)) as client:
                csrf = self._par(client)
                h = hashlib.sha256(a.read_bytes()).hexdigest()
                client.post(f"/api/reports/{fid_a}/draft", json={"hash": h, "storage": {"segredo-do-a": "1"}}, headers=csrf)
                html_b = client.get(f"/api/reports/{fid_b}/view?ticket={TICKET}").text
                self.assertNotIn("segredo-do-a", html_b)


class MigracaoDeChavesNoBoot(unittest.TestCase):
    def test_boot_migra_chaves_de_versao_antiga(self):
        fonte = re.search(r"function migrarVersoesAntigas\(\)\{[\s\S]*?\n\}", BOOTSTRAP).group(0)
        prova = subprocess.run(["node", "-e", fonte + r"""
const enviados=[];
const fid='abc123';
const h1='f'.repeat(64), h2='e'.repeat(64);
const memory={};
memory['mb-report-notas:'+fid+':'+h1]=JSON.stringify([{id:'n1',texto:'x',onde:'perto de: card',px:10,py:20},{id:'n2',texto:'y'}]);
memory['mb-report-notas:'+fid+':'+h2]=JSON.stringify([{id:'n2',texto:'y'},{id:'n3',texto:'z'}]);
memory['mb-cursor-receipts:'+fid+':'+h1]=JSON.stringify({n1:{saved:true}});
memory['mb-report-desenhos:'+fid+':'+h1]=JSON.stringify({v:1,tracos:[1,2]});
memory['cf-notas:estavel']='[{"id":"k"}]';
global.META={fid:fid,hash:h2};
global.send=(kind,payload)=>enviados.push({kind,payload});
global.state=()=>{const out={};for(const k of Object.keys(memory))out[k]=memory[k];return out;};
migrarVersoesAntigas();
const notas=JSON.parse(memory['mb-report-notas:'+fid+':'+h2]);
const recibos=JSON.parse(memory['mb-cursor-receipts:'+fid+':'+h2]);
console.log(JSON.stringify({
 ids:notas.map(n=>n.id).sort(),
 migradas:notas.filter(n=>n.migrada_de===h1.slice(0,8)).map(n=>n.id).sort(),
 desenhos:JSON.parse(memory['mb-report-desenhos:'+fid+':'+h2]).tracos,
 recibos:recibos.n1&&recibos.n1.saved===true,
 antigas_removidas:memory['mb-report-notas:'+fid+':'+h1]===undefined&&memory['mb-cursor-receipts:'+fid+':'+h1]===undefined,
 estavel:memory['cf-notas:estavel'],
 reenviou:enviados.some(e=>e.kind==='draft'&&e.payload.storage['mb-report-notas:'+fid+':'+h2])
}));
"""], capture_output=True, text=True, check=True)
        out = json.loads(prova.stdout)
        self.assertEqual(["n1", "n2", "n3"], out["ids"], out)
        self.assertEqual(["n1"], out["migradas"], out)
        self.assertEqual([1, 2], out["desenhos"], out)
        self.assertTrue(out["recibos"], out)
        self.assertTrue(out["antigas_removidas"], out)
        self.assertEqual('[{"id":"k"}]', out["estavel"], out)
        self.assertTrue(out["reenviou"], out)


if __name__ == "__main__":
    unittest.main()
