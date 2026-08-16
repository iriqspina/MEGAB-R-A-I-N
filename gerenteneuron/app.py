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
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from config import carregar_config, raiz_app, caminho_env
from router import route
from gerente import responder_como_gerente, carregar_projetos
from connectors import testar_todos
from eval import registrar_interacao, resumo_feedback, sugerir_melhorias
from vault import Vault


_vault = Vault()


def _aplicar_credenciais_do_vault():
    """Exporta credenciais do cofre desbloqueado para variáveis de ambiente."""
    if _vault.is_desbloqueado:
        for chave, valor in _vault.exportar_env().items():
            os.environ[chave] = valor


def _limpar_credenciais_do_vault():
    """Remove credenciais do cofre das variáveis de ambiente."""
    if _vault.existe():
        try:
            v = Vault()
            # Não sabemos a senha; apenas removemos as keys conhecidas do .env example.
            for chave in [
                "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "MOONSHOT_API_KEY",
                "OPENAI_BASE_URL", "ANTHROPIC_BASE_URL", "GEMINI_BASE_URL", "MOONSHOT_BASE_URL",
                "OLLAMA_BASE_URL", "GERENTENEURON_MODO",
            ]:
                os.environ.pop(chave, None)
        except Exception:
            pass


class APIHandler(BaseHTTPRequestHandler):
    """Roteia chamadas de API e serve arquivos estáticos."""

    def log_message(self, fmt, *args):
        # Log silencioso no terminal; o app é para o usuário, não para debug.
        print(f"[{datetime.now(timezone.utc).isoformat()}] {args[0]} {args[1]}")

    def _responder_json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _ler_corpo(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw_bytes = self.rfile.read(length)
        try:
            raw = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raw = raw_bytes.decode("latin-1")
        return json.loads(raw)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
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
            self._responder_json(200, {"modo": cfg.get("modo", "auto"), "providers": provedores})
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
            })
            return

        # Qualquer outro GET é estático: serve templates/index.html ou arquivos de static/.
        if caminho == "/" or caminho == "/index.html":
            self._servir_arquivo(raiz_app / "templates" / "index.html", "text/html; charset=utf-8")
            return

        if caminho.startswith("/static/"):
            relativo = caminho[len("/static/"):]
            alvo = raiz_app / "static" / relativo
            ctype = "text/css; charset=utf-8" if relativo.endswith(".css") else "application/javascript; charset=utf-8"
            self._servir_arquivo(alvo, ctype)
            return

        self._responder_json(404, {"erro": "rota não encontrada"})

    def do_POST(self):
        global _vault
        caminho = self.path.split("?", 1)[0]

        if caminho == "/api/chat":
            body = self._ler_corpo()
            mensagem = body.get("mensagem", "").strip()
            modelo_forcado = body.get("modelo", "auto")
            historico = body.get("historico", [])

            if not mensagem:
                self._responder_json(400, {"erro": "mensagem vazia"})
                return

            # Roteamento por custo/capacidade.
            cfg = carregar_config()
            modo = body.get("modo", cfg.get("modo", "auto"))
            if modo not in ("auto", "manual"):
                modo = "auto"
            boost = bool(body.get("boost", False))
            resultado = route(mensagem, modo=modo, modelo_forcado=modelo_forcado, historico=historico, boost=boost)
            registrar_interacao(mensagem, resultado, aba="chat")
            self._responder_json(200, resultado)
            return

        if caminho == "/api/gerente":
            body = self._ler_corpo()
            mensagem = body.get("mensagem", "").strip()
            historico = body.get("historico", [])
            if not mensagem:
                self._responder_json(400, {"erro": "mensagem vazia"})
                return
            resultado = responder_como_gerente(mensagem, historico)
            registrar_interacao(mensagem, resultado, aba="gerente")
            self._responder_json(200, resultado)
            return

        if caminho == "/api/vault/unlock":
            body = self._ler_corpo()
            senha = body.get("senha", "")
            try:
                _vault.desbloquear(senha)
                _aplicar_credenciais_do_vault()
                self._responder_json(200, {"ok": True, "desbloqueado": True})
            except ValueError:
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
            body = self._ler_corpo()
            recovery = body.get("recovery", "")
            nova = body.get("nova_senha", "")
            if len(nova) < 6:
                self._responder_json(400, {"ok": False, "erro": "nova senha muito curta"})
                return
            try:
                new_key = _vault.redefinir_senha_com_recuperacao(recovery, nova)
                _aplicar_credenciais_do_vault()
                self._responder_json(200, {"ok": True, "recovery_novo": new_key[:8] + "..."})
            except ValueError as e:
                self._responder_json(401, {"ok": False, "erro": str(e)})
            except Exception as e:
                self._responder_json(500, {"ok": False, "erro": str(e)})
            return

        if caminho == "/api/feedback":
            body = self._ler_corpo()
            from eval import FEEDBACK_FILE
            try:
                registro = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "mensagem": body.get("mensagem", ""),
                    "modelo_usado": body.get("modelo_usado", ""),
                    "estrategia": body.get("estrategia", ""),
                    "feedback": body.get("feedback"),
                }
                FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
                with FEEDBACK_FILE.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(registro, ensure_ascii=False) + "\n")
                self._responder_json(200, {"ok": True})
            except Exception as e:
                self._responder_json(500, {"erro": str(e)})
            return

        if caminho == "/api/config":
            body = self._ler_corpo()
            try:
                linhas_existentes = []
                if caminho_env.exists():
                    linhas_existentes = caminho_env.read_text(encoding="utf-8").splitlines()

                chaves_permitidas = {
                    "OPENAI_API_KEY", "OPENAI_BASE_URL",
                    "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL",
                    "GEMINI_API_KEY", "GEMINI_BASE_URL",
                    "MOONSHOT_API_KEY", "MOONSHOT_BASE_URL",
                    "OLLAMA_BASE_URL", "GERENTENEURON_MODO",
                }

                novo = {}
                for linha in linhas_existentes:
                    if "=" in linha:
                        chave, valor = linha.split("=", 1)
                        chave = chave.strip()
                        if chave in chaves_permitidas:
                            novo[chave] = valor.strip()

                for chave, valor in body.items():
                    if chave in chaves_permitidas:
                        if valor:
                            novo[chave] = valor
                        elif chave in novo:
                            del novo[chave]

                saida = ["# GerenteNeuron — configuração local (não versionar)"]
                for chave in sorted(novo):
                    saida.append(f'{chave}="{novo[chave]}"')
                caminho_env.write_text("\n".join(saida) + "\n", encoding="utf-8")
                cfg = carregar_config()
                self._responder_json(200, {"ok": True, "testes": testar_todos(cfg)})
            except Exception as e:
                self._responder_json(500, {"erro": str(e)})
            return

        self._responder_json(404, {"erro": "rota não encontrada"})

    def _servir_arquivo(self, caminho: Path, ctype: str):
        try:
            # path containment simples: recusa sair de raiz_app
            caminho = caminho.resolve()
            if not str(caminho).startswith(str(raiz_app.resolve())):
                raise FileNotFoundError()
            data = caminho.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
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
