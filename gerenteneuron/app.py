#!/usr/bin/env python3
"""GerenteNeuron — app local unificado de chat multi-IA.

Roda só com stdlib. Não depende de Flask, Node ou runtime externo.
Uso:
    python gerenteneuron/app.py
    python gerenteneuron/app.py --port 8787
"""

import json
import os
import socketserver
import threading
import time
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

import precos
from config import carregar_config, raiz_app, caminho_env, CHAVES_CONHECIDAS
from router import route
from gerente import responder_como_gerente, carregar_projetos
from connectors import testar_todos
from eval import registrar_interacao, resumo_feedback, sugerir_melhorias, registrar_feedback
from vault import Vault, aviso_recuperacao_exposta


HOSTS_ACEITOS = {"127.0.0.1", "localhost", "::1", "[::1]"}

# Brute force local no cofre: PBKDF2 de 600k iterações já é lento, mas travar
# depois de N erros é barato e transforma tentativa em falha ruidosa.
MAX_TENTATIVAS_UNLOCK = 5
JANELA_BLOQUEIO_S = 300

_vault = Vault()
_chaves_exportadas: set[str] = set()
_tentativas_unlock: list[float] = []
_lock = threading.Lock()


def _aplicar_credenciais_do_vault():
    """Exporta credenciais do cofre desbloqueado para variáveis de ambiente."""
    global _chaves_exportadas
    if not _vault.is_desbloqueado:
        return
    exportadas = _vault.exportar_env()
    for chave, valor in exportadas.items():
        os.environ[chave] = valor
    _chaves_exportadas = set(exportadas)


def _limpar_credenciais_do_vault():
    """Remove do ambiente exatamente o que o cofre exportou."""
    global _chaves_exportadas
    for chave in _chaves_exportadas | set(CHAVES_CONHECIDAS):
        os.environ.pop(chave, None)
    _chaves_exportadas = set()


def _unlock_bloqueado() -> int:
    """Segundos restantes de bloqueio, ou 0 se liberado."""
    with _lock:
        agora = time.time()
        _tentativas_unlock[:] = [t for t in _tentativas_unlock if agora - t < JANELA_BLOQUEIO_S]
        if len(_tentativas_unlock) < MAX_TENTATIVAS_UNLOCK:
            return 0
        return int(JANELA_BLOQUEIO_S - (agora - _tentativas_unlock[0]))


def _registrar_falha_unlock():
    with _lock:
        _tentativas_unlock.append(time.time())


def _zerar_falhas_unlock():
    with _lock:
        _tentativas_unlock.clear()


class APIHandler(BaseHTTPRequestHandler):
    """Roteia chamadas de API e serve arquivos estáticos."""

    server_version = "GerenteNeuron"
    sys_version = ""

    def log_message(self, fmt, *args):
        # Sem indexar args: BaseHTTPRequestHandler chama isso com aridade
        # variável, e o acesso posicional derrubava o handler em log de erro.
        try:
            texto = fmt % args
        except Exception:
            texto = str(args)
        print(f"[{datetime.now(timezone.utc).isoformat()}] {texto}")

    # ---------- origem ----------

    def _origem_confiavel(self) -> bool:
        """Recusa chamada vinda de outro site.

        O app carrega API keys reais em memória e escuta em 127.0.0.1. Sem esta
        checagem (e com Allow-Origin '*'), qualquer página aberta no navegador
        conseguia POSTar em /api/chat e queimar crédito, ou tentar senha no
        cofre. Origin ausente é chamada não-navegador (curl, o próprio app).
        """
        host = (self.headers.get("Host") or "").split(":")[0].strip("[]")
        if host and host not in {h.strip("[]") for h in HOSTS_ACEITOS}:
            return False

        origem = self.headers.get("Origin")
        if not origem:
            return True
        nome = urlparse(origem).hostname or ""
        return nome in {h.strip("[]") for h in HOSTS_ACEITOS}

    def _cabecalhos_cors(self):
        origem = self.headers.get("Origin")
        if origem and self._origem_confiavel():
            self.send_header("Access-Control-Allow-Origin", origem)
            self.send_header("Vary", "Origin")

    def _responder_json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self._cabecalhos_cors()
        self.end_headers()
        self.wfile.write(body)

    def _ler_corpo(self, limite: int = 2_000_000) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        if length > limite:
            raise ValueError("corpo grande demais")
        raw_bytes = self.rfile.read(length)
        try:
            raw = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raw = raw_bytes.decode("latin-1")
        dados = json.loads(raw)
        return dados if isinstance(dados, dict) else {}

    def do_OPTIONS(self):
        if not self._origem_confiavel():
            self._responder_json(403, {"erro": "origem não permitida"})
            return
        self.send_response(204)
        self._cabecalhos_cors()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ---------- GET ----------

    def do_GET(self):
        if not self._origem_confiavel():
            self._responder_json(403, {"erro": "origem não permitida"})
            return

        caminho = self.path.split("?", 1)[0]

        if caminho == "/api/health":
            self._responder_json(200, {"ok": True, "hora": datetime.now(timezone.utc).isoformat()})
            return

        if caminho == "/api/models":
            cfg = carregar_config()
            provedores = []
            for nome, info in cfg["providers"].items():
                provedores.append({
                    "id": nome,
                    "nome": info["nome"],
                    "disponivel": info.get("key") is not None or info.get("local", False),
                    "modelos": info["modelos"],
                })
            self._responder_json(200, {
                "modo": cfg.get("modo", "auto"),
                "providers": provedores,
                "precos_verificado_em": cfg.get("precos_verificado_em"),
                "precos_aviso": cfg.get("precos_aviso"),
            })
            return

        if caminho == "/api/precos":
            self._responder_json(200, {
                "verificado_em": precos.carregar().get("verificado_em"),
                "idade_dias": precos.idade_em_dias(),
                "vencida": precos.esta_vencida(),
                "aviso": precos.aviso_validade(),
                "notas": precos.carregar().get("notas", []),
                "fontes": precos.carregar().get("fontes", {}),
                "modelos": sorted(precos.modelos(), key=precos.custo_ponderado),
            })
            return

        if caminho == "/api/projetos":
            self._responder_json(200, {"projetos": carregar_projetos()})
            return

        if caminho == "/api/testar":
            cfg = carregar_config()
            self._responder_json(200, {"resultados": testar_todos(cfg)})
            return

        if caminho == "/api/eval":
            self._responder_json(200, {
                "resumo": resumo_feedback(),
                "sugestoes": sugerir_melhorias(),
            })
            return

        if caminho == "/api/vault/status":
            self._responder_json(200, {
                "existe": _vault.existe(),
                "desbloqueado": _vault.is_desbloqueado,
                "bloqueado_por_s": _unlock_bloqueado(),
                "aviso": aviso_recuperacao_exposta(),
            })
            return

        if caminho in ("/", "/index.html"):
            self._servir_arquivo(raiz_app / "templates" / "index.html", "text/html; charset=utf-8")
            return

        if caminho.startswith("/static/"):
            relativo = caminho[len("/static/"):]
            alvo = raiz_app / "static" / relativo
            ctype = "text/css; charset=utf-8" if relativo.endswith(".css") else "application/javascript; charset=utf-8"
            self._servir_arquivo(alvo, ctype)
            return

        self._responder_json(404, {"erro": "rota não encontrada"})

    # ---------- POST ----------

    def do_POST(self):
        global _vault

        if not self._origem_confiavel():
            self._responder_json(403, {"erro": "origem não permitida"})
            return

        caminho = self.path.split("?", 1)[0]

        try:
            body = self._ler_corpo()
        except (ValueError, json.JSONDecodeError) as e:
            self._responder_json(400, {"erro": f"corpo inválido: {e}"})
            return

        if caminho == "/api/chat":
            mensagem = str(body.get("mensagem", "")).strip()
            if not mensagem:
                self._responder_json(400, {"erro": "mensagem vazia"})
                return

            cfg = carregar_config()
            modo = body.get("modo", cfg.get("modo", "auto"))
            if modo not in ("auto", "manual"):
                modo = "auto"

            resultado = route(
                mensagem,
                modo=modo,
                modelo_forcado=body.get("modelo", "auto"),
                historico=body.get("historico", []),
                boost=bool(body.get("boost", False)),
            )
            registrar_interacao(mensagem, resultado, aba="chat")
            self._responder_json(200, resultado)
            return

        if caminho == "/api/gerente":
            mensagem = str(body.get("mensagem", "")).strip()
            if not mensagem:
                self._responder_json(400, {"erro": "mensagem vazia"})
                return
            resultado = responder_como_gerente(mensagem, body.get("historico", []))
            registrar_interacao(mensagem, resultado, aba="gerente")
            self._responder_json(200, resultado)
            return

        if caminho == "/api/vault/unlock":
            restante = _unlock_bloqueado()
            if restante:
                self._responder_json(429, {
                    "ok": False,
                    "erro": f"muitas tentativas; espere {restante}s",
                    "bloqueado_por_s": restante,
                })
                return
            try:
                _vault.desbloquear(str(body.get("senha", "")))
                _aplicar_credenciais_do_vault()
                _zerar_falhas_unlock()
                self._responder_json(200, {"ok": True, "desbloqueado": True})
            except ValueError:
                _registrar_falha_unlock()
                self._responder_json(401, {"ok": False, "erro": "senha incorreta"})
            except Exception as e:
                self._responder_json(500, {"ok": False, "erro": str(e)})
            return

        if caminho == "/api/vault/lock":
            _vault = Vault()
            _limpar_credenciais_do_vault()
            self._responder_json(200, {"ok": True, "desbloqueado": False})
            return

        if caminho == "/api/vault/forgot":
            restante = _unlock_bloqueado()
            if restante:
                self._responder_json(429, {"ok": False, "erro": f"muitas tentativas; espere {restante}s"})
                return
            nova = str(body.get("nova_senha", ""))
            if len(nova) < 6:
                self._responder_json(400, {"ok": False, "erro": "nova senha muito curta"})
                return
            try:
                nova_recuperacao = _vault.redefinir_senha_com_recuperacao(str(body.get("recovery", "")), nova)
                _aplicar_credenciais_do_vault()
                _zerar_falhas_unlock()
                self._responder_json(200, {"ok": True, "recovery_novo": nova_recuperacao[:8] + "..."})
            except ValueError as e:
                _registrar_falha_unlock()
                self._responder_json(401, {"ok": False, "erro": str(e)})
            except Exception as e:
                self._responder_json(500, {"ok": False, "erro": str(e)})
            return

        if caminho == "/api/feedback":
            try:
                registrar_feedback(
                    mensagem=str(body.get("mensagem", "")),
                    modelo_usado=str(body.get("modelo_usado", "")),
                    estrategia=str(body.get("estrategia", "")),
                    feedback=body.get("feedback"),
                )
                self._responder_json(200, {"ok": True})
            except Exception as e:
                self._responder_json(500, {"erro": str(e)})
            return

        if caminho == "/api/config":
            try:
                self._responder_json(200, self._gravar_env(body))
            except Exception as e:
                self._responder_json(500, {"erro": str(e)})
            return

        self._responder_json(404, {"erro": "rota não encontrada"})

    # ---------- auxiliares ----------

    def _gravar_env(self, body: dict) -> dict:
        """Grava .env em texto puro. Caminho legado: o cofre é o recomendado."""
        atual = {}
        if caminho_env.exists():
            for linha in caminho_env.read_text(encoding="utf-8").splitlines():
                if "=" in linha and not linha.strip().startswith("#"):
                    chave, valor = linha.split("=", 1)
                    if chave.strip() in CHAVES_CONHECIDAS:
                        atual[chave.strip()] = valor.strip()

        for chave, valor in body.items():
            if chave not in CHAVES_CONHECIDAS:
                continue
            if valor:
                atual[chave] = str(valor)
            else:
                atual.pop(chave, None)

        saida = ["# GerenteNeuron — configuração local (não versionar)"]
        saida += [f'{c}="{atual[c]}"' for c in sorted(atual)]
        caminho_env.write_text("\n".join(saida) + "\n", encoding="utf-8")
        try:
            os.chmod(caminho_env, 0o600)
        except OSError:
            pass

        cfg = carregar_config()
        return {
            "ok": True,
            "aviso": ".env guarda a chave em texto puro. Prefira o cofre: mb-vault.py add <CHAVE> <valor>",
            "testes": testar_todos(cfg),
        }

    def _servir_arquivo(self, caminho: Path, ctype: str):
        try:
            alvo = caminho.resolve()
            base = raiz_app.resolve()
            if base not in alvo.parents and alvo != base:
                raise FileNotFoundError()
            data = alvo.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)
        except (FileNotFoundError, IsADirectoryError, PermissionError, OSError):
            self._responder_json(404, {"erro": "arquivo não encontrado"})


class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="GerenteNeuron — chat multi-IA local")
    parser.add_argument("--port", type=int, default=8787, help="porta do servidor (padrão: 8787)")
    parser.add_argument("--no-open", action="store_true", help="não abrir o navegador automaticamente")
    args = parser.parse_args()

    endereco = ("127.0.0.1", args.port)
    url = f"http://{endereco[0]}:{endereco[1]}/"

    for aviso in (precos.aviso_validade(), aviso_recuperacao_exposta()):
        if aviso:
            print(f"AVISO: {aviso}")

    with ThreadedHTTPServer(endereco, APIHandler) as servidor:
        print(f"GerenteNeuron rodando em {url}")
        print("Pressione Ctrl+C para parar.")
        if not args.no_open:
            webbrowser.open(url)
        try:
            servidor.serve_forever()
        except KeyboardInterrupt:
            print("\nGerenteNeuron encerrado.")


if __name__ == "__main__":
    main()
