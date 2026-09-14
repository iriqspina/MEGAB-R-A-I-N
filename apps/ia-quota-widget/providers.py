"""Leitura de cota de assinatura das IAs instaladas nesta máquina.

Contrato único consumido pela UI:

    fetch_provider(provider_id) -> {
        "provider":   str,
        "label":      str,
        "status":     "ok" | "unavailable" | "auth_required" | "error" | "rate_limited",
        "source":     str,                       # de onde o número veio, legível
        "fetched_at": str ISO UTC | None,        # só quando status == "ok"
        "windows":    [{"id", "label", "used_percent", "resets_at", "duration_minutes"}],
        "message":    str,                       # curta, sem segredo
    }

Regras que o código impõe, não só documenta:

1.  Só leitura. Nenhum adaptador escreve em arquivo de credencial nem renova
    token. Token vencido vira ``auth_required`` com a instrução de destravar.
2.  ``None`` nunca vira ``0``. Ausência de dado é ausência, não cota zerada.
    (O próprio esquema do Codex diz: "clients must not infer recovery from
    percentages or reset times".)
3.  Uma fonte por produto. ``gemini_cli`` e ``antigravity`` são cotas
    diferentes e nunca são fundidas.
4.  Contagem local de token nunca vira percentual de cota.
5.  Timeout finito em toda chamada, inclusive no subprocesso.
6.  Nenhum token, e-mail ou id de conta sai daqui — nem em ``message``, nem em
    exceção propagada.

Só stdlib. Evidência das fontes: artefato ``260908-widget-fontes``.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

__all__ = ["PROVIDER_IDS", "PROVIDER_LABELS", "fetch_provider", "fetch_all"]

PROVIDER_IDS: tuple[str, ...] = (
    "codex",
    "claude",
    "zai",
    "gemini_cli",
    "antigravity",
    "gemini_web",
)

PROVIDER_LABELS: dict[str, str] = {
    "codex": "Codex",
    "claude": "Claude",
    "zai": "Z.ai",
    "gemini_cli": "Gemini CLI",
    "antigravity": "Antigravity",
    "gemini_web": "Gemini (app)",
}

DEFAULT_TIMEOUT = 12.0
_SUBPROCESS_TIMEOUT = 25.0
_MAX_BODY_BYTES = 512 * 1024

# Sob pythonw.exe (launcher sem terminal) o processo pai não tem console, então
# todo filho de console — codex, netstat, tasklist — ganharia uma janela nova
# que pisca e some a cada refresh. CREATE_NO_WINDOW suprime o console do filho;
# em não-Windows a constante não existe e o dicionário fica vazio.
_NO_WINDOW: dict[str, int] = (
    {"creationflags": subprocess.CREATE_NO_WINDOW}  # type: ignore[attr-defined]
    if hasattr(subprocess, "CREATE_NO_WINDOW")
    else {}
)

# Mensagem de erro do fornecedor pode conter identificador; nunca repassamos o
# corpo cru. Só o código HTTP e um rótulo nosso.
_STATUS_BY_HTTP = {401: "auth_required", 403: "auth_required", 429: "rate_limited"}


# --------------------------------------------------------------------------
# normalização
# --------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _result(
    provider: str,
    status: str,
    *,
    source: str,
    windows: Sequence[dict[str, Any]] | None = None,
    message: str = "",
    fetched_at: str | None = None,
) -> dict[str, Any]:
    """Monta a resposta no formato do contrato.

    ``fetched_at`` só é preenchido quando houve leitura boa: um horário em cima
    de um erro faz a UI achar que o dado é fresco.
    """
    return {
        "provider": provider,
        "label": PROVIDER_LABELS.get(provider, provider),
        "status": status,
        "source": source,
        "fetched_at": fetched_at if status == "ok" else None,
        "windows": list(windows or []),
        "message": message,
    }


def normalize_percent(value: Any) -> float | None:
    """Percentual 0–100 finito, ou ``None``.

    Aceita int/float/str numérica. Rejeita NaN, infinito, bool e qualquer coisa
    que não seja número — devolver ``None`` é sempre melhor que devolver 0.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        try:
            value = float(value.strip())
        except (ValueError, AttributeError):
            return None
    if not isinstance(value, (int, float)):
        return None
    value = float(value)
    if not math.isfinite(value):
        return None
    return min(100.0, max(0.0, value))


def percent_from_remaining_fraction(value: Any) -> float | None:
    """Gemini devolve fração RESTANTE (0–1); a UI quer percentual USADO."""
    if value is None or isinstance(value, bool) or isinstance(value, str):
        if not isinstance(value, str):
            return None
        try:
            value = float(value.strip())
        except ValueError:
            return None
    if not isinstance(value, (int, float)):
        return None
    value = float(value)
    if not math.isfinite(value):
        return None
    return min(100.0, max(0.0, (1.0 - value) * 100.0))


def normalize_epoch_seconds(value: Any) -> str | None:
    """Epoch em segundos (Codex) -> ISO UTC."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        try:
            value = float(value.strip())
        except ValueError:
            return None
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    if value <= 0:
        return None
    try:
        return datetime.fromtimestamp(float(value), timezone.utc).replace(microsecond=0).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def normalize_iso(value: Any) -> str | None:
    """ISO-8601 de qualquer fornecedor -> ISO UTC, sempre com offset explícito.

    Tolera o sufixo ``Z``, fração de segundo longa e ausência de offset (nesse
    caso assume UTC, que é o que os três fornecedores mandam na prática).
    """
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    # datetime.fromisoformat aceita no máximo 6 dígitos de fração.
    text = re.sub(r"(\.\d{6})\d+", r"\1", text)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _window(
    win_id: str,
    label: str,
    used_percent: Any,
    resets_at: str | None,
    duration_minutes: int | None = None,
) -> dict[str, Any]:
    return {
        "id": win_id,
        "label": label,
        "used_percent": used_percent,
        "resets_at": resets_at,
        "duration_minutes": duration_minutes,
    }


def normalize_duration_minutes(value: Any) -> int | None:
    """Minutos de duração de janela, inteiro positivo, ou ``None``."""
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    return int(value)


def _duration_label(minutes: Any) -> str:
    """10080 -> "7 d"; 300 -> "5 h". Devolve "" quando não dá para saber."""
    minutes = normalize_duration_minutes(minutes)
    if minutes is None:
        return ""
    if minutes % 1440 == 0:
        return f"{minutes // 1440} d"
    if minutes % 60 == 0:
        return f"{minutes // 60} h"
    return f"{minutes} min"


# Duração nominal das janelas nomeadas do Claude — o payload não manda a
# duração explícita para esses buckets, então mapeamos pelo ``kind``/chave.
_CLAUDE_KIND_MINUTES = {
    "session": 300,
    "weekly_all": 10080,
    "weekly_scoped": 10080,
}
_CLAUDE_FALLBACK_MINUTES = {"five_hour": 300, "seven_day": 10080}


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------


class HttpResponse:
    __slots__ = ("status", "body")

    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self.body = body

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8", "replace"))


def _http(
    url: str,
    *,
    headers: dict[str, str],
    data: bytes | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> HttpResponse:
    """GET/POST que devolve status mesmo em erro HTTP, em vez de levantar.

    Erro de rede vira ``OSError`` — quem chama traduz para ``status="error"``.
    """
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return HttpResponse(int(resp.status), resp.read(_MAX_BODY_BYTES))
    except urllib.error.HTTPError as exc:  # 4xx/5xx ainda são resposta
        try:
            body = exc.read(_MAX_BODY_BYTES)
        except Exception:  # pragma: no cover - depende do socket
            body = b""
        return HttpResponse(int(exc.code), body)


def _home() -> Path:
    override = os.environ.get("IA_QUOTA_HOME")
    return Path(override) if override else Path.home()


def _read_json_file(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# --------------------------------------------------------------------------
# Codex — `codex app-server`, JSON-RPC por stdio
# --------------------------------------------------------------------------

CODEX_SOURCE = "codex app-server · account/rateLimits/read"


def find_codex_binary() -> str | None:
    override = os.environ.get("IA_QUOTA_CODEX_BIN")
    if override and Path(override).exists():
        return override
    return shutil.which("codex")


#: Handshake + as duas leituras read-only, na ordem em que vão para o servidor.
#: ``account/rateLimits/read`` recusa objeto vazio (``invalid type: map,
#: expected unit``): tem que ser ``params: null``. ``refreshToken: false``
#: garante que a leitura não dispara renovação de token.
CODEX_STEPS: tuple[tuple[int | None, dict[str, Any]], ...] = (
    (
        0,
        {
            "method": "initialize",
            "id": 0,
            "params": {"clientInfo": {"name": "ia-quota-widget", "version": "0.1.0"}},
        },
    ),
    (None, {"method": "initialized", "params": {}}),
    (1, {"method": "account/read", "id": 1, "params": {"refreshToken": False}}),
    (2, {"method": "account/rateLimits/read", "id": 2, "params": None}),
)


def run_codex_app_server(binary: str, timeout: float = _SUBPROCESS_TIMEOUT) -> str:
    """Sobe o app-server, conversa por stdio e devolve o stdout bruto.

    Tem que ser **pergunta e resposta, uma de cada vez**. Escrever as quatro
    linhas de uma vez e fechar o stdin faz o servidor sair logo depois de
    responder ao ``initialize`` — medido: 1,2 s, só a resposta de id 0. Por
    isso o stdin fica aberto até a última resposta chegar.

    Encerramento: fecha o stdin (saída normal) e só então, se o processo
    insistir, encerra o filho que este adaptador criou. Nenhum processo
    pré-existente é tocado.
    """
    deadline = time.monotonic() + timeout
    proc = subprocess.Popen(  # noqa: S603 - binário resolvido por which/override
        [binary, "app-server", "--listen", "stdio://"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        **_NO_WINDOW,
    )
    # Mata o filho se ele travar: readline() volta vazio e o laço termina.
    watchdog = threading.Timer(timeout, proc.kill)
    watchdog.daemon = True
    watchdog.start()

    received: list[str] = []
    try:
        assert proc.stdin is not None and proc.stdout is not None
        for expect_id, request in CODEX_STEPS:
            if time.monotonic() >= deadline:
                break
            try:
                proc.stdin.write((json.dumps(request) + "\n").encode("utf-8"))
                proc.stdin.flush()
            except (BrokenPipeError, OSError, ValueError):
                break
            if expect_id is None:  # notificação, não tem resposta
                continue
            while time.monotonic() < deadline:
                raw = proc.stdout.readline()
                if not raw:  # EOF: processo saiu ou foi encerrado
                    break
                line = raw.decode("utf-8", "replace").strip()
                if not line:
                    continue
                received.append(line)
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if isinstance(msg, dict) and msg.get("id") == expect_id:
                    break
            else:
                break
    finally:
        watchdog.cancel()
        _close_child(proc)
    return "\n".join(received)


def _close_child(proc: subprocess.Popen[bytes]) -> None:
    """Encerra o processo filho pelo caminho educado antes do bruto."""
    try:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
    except OSError:
        pass
    try:
        proc.wait(timeout=3)
        return
    except subprocess.TimeoutExpired:
        pass
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


def _rpc_responses(stdout: str) -> dict[int, dict[str, Any]]:
    found: dict[int, dict[str, Any]] = {}
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if isinstance(msg, dict) and isinstance(msg.get("id"), int):
            found[msg["id"]] = msg
    return found


def parse_codex_rate_limits(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """``GetAccountRateLimitsResponse`` -> janelas do contrato.

    Prefere ``rateLimitsByLimitId`` (visão multi-bucket, uma entrada por modelo
    metrificado); cai para ``rateLimits`` quando o mapa não veio.
    """
    if not isinstance(payload, dict):
        return []
    by_id = payload.get("rateLimitsByLimitId")
    snapshots: list[tuple[str, dict[str, Any]]] = []
    if isinstance(by_id, dict) and by_id:
        for key, snap in sorted(by_id.items()):
            if isinstance(snap, dict):
                snapshots.append((str(key), snap))
    elif isinstance(payload.get("rateLimits"), dict):
        snap = payload["rateLimits"]
        snapshots.append((str(snap.get("limitId") or "codex"), snap))

    windows: list[dict[str, Any]] = []
    for limit_id, snap in snapshots:
        name = snap.get("limitName") or snap.get("normalModelSlug") or limit_id
        for slot in ("primary", "secondary"):
            win = snap.get(slot)
            if not isinstance(win, dict):
                continue
            duration_minutes = normalize_duration_minutes(win.get("windowDurationMins"))
            duration = _duration_label(duration_minutes)
            label = f"{name} · {duration}" if duration else str(name)
            windows.append(
                _window(
                    f"{limit_id}:{slot}",
                    label,
                    normalize_percent(win.get("usedPercent")),
                    normalize_epoch_seconds(win.get("resetsAt")),
                    duration_minutes,
                )
            )
    return windows


def _fetch_codex(timeout: float) -> dict[str, Any]:
    binary = find_codex_binary()
    if not binary:
        return _result(
            "codex",
            "unavailable",
            source=CODEX_SOURCE,
            message="CLI do Codex não encontrado no PATH.",
        )
    try:
        # O prazo é o que o chamador pediu. Subir um piso fixo aqui deixaria a
        # UI presa 25 s num app-server travado — medido, a leitura boa custa ~1 s.
        stdout = run_codex_app_server(binary, timeout=timeout)
    except OSError as exc:
        return _result("codex", "error", source=CODEX_SOURCE, message=f"Falha ao executar o CLI ({type(exc).__name__}).")

    responses = _rpc_responses(stdout)
    rate = responses.get(2)
    if rate is None:
        return _result(
            "codex",
            "error",
            source=CODEX_SOURCE,
            message="app-server não respondeu a account/rateLimits/read.",
        )
    if "error" in rate:
        # Sem login o app-server responde erro nesta chamada.
        return _result(
            "codex",
            "auth_required",
            source=CODEX_SOURCE,
            message="Sessão do Codex indisponível. Rode `codex login`.",
        )

    account = responses.get(1, {}).get("result") or {}
    plan = None
    if isinstance(account.get("account"), dict):
        plan = account["account"].get("planType")

    windows = parse_codex_rate_limits(rate.get("result") or {})
    if not windows:
        return _result(
            "codex",
            "unavailable",
            source=CODEX_SOURCE,
            message="Conta autenticada, mas sem janela de cota exposta.",
        )
    return _result(
        "codex",
        "ok",
        source=CODEX_SOURCE,
        windows=windows,
        fetched_at=_now_iso(),
        message=f"Plano {plan}." if plan else "",
    )


# --------------------------------------------------------------------------
# Claude — OAuth usage do Claude Code
# --------------------------------------------------------------------------

CLAUDE_URL = "https://api.anthropic.com/api/oauth/usage"
CLAUDE_SOURCE = "api.anthropic.com/api/oauth/usage"

_CLAUDE_KIND_LABELS = {
    "session": "Sessão",
    "weekly_all": "Semana",
    "weekly_scoped": "Semana",
    "monthly": "Mês",
}


def claude_credentials_path() -> Path:
    return _home() / ".claude" / ".credentials.json"


def read_claude_oauth(path: Path | None = None) -> dict[str, Any] | None:
    data = _read_json_file(path or claude_credentials_path())
    if isinstance(data, dict) and isinstance(data.get("claudeAiOauth"), dict):
        return data["claudeAiOauth"]
    return None


def _expired_ms(expires_at: Any, *, skew_ms: int = 60_000) -> bool:
    """Vencido? Sem valor legível tratamos como vencido — melhor pedir login do
    que mandar um Bearer inválido e tomar 401."""
    if isinstance(expires_at, bool) or not isinstance(expires_at, (int, float)):
        return True
    if not math.isfinite(expires_at):
        return True
    return (expires_at - skew_ms) <= datetime.now(timezone.utc).timestamp() * 1000


def parse_claude_usage(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Payload do ``/oauth/usage`` -> janelas.

    ``limits[]`` é a fonte primária (é onde sai a cota POR MODELO, em
    ``weekly_scoped`` com ``scope.model.display_name``). Os campos nomeados
    ``five_hour``/``seven_day`` são fallback para payload antigo. Bucket
    desconhecido é ignorado em vez de quebrar: os nomes internos mudam sem
    aviso.
    """
    if not isinstance(payload, dict):
        return []

    windows: list[dict[str, Any]] = []
    seen: set[str] = set()

    limits = payload.get("limits")
    if isinstance(limits, list):
        for entry in limits:
            if not isinstance(entry, dict):
                continue
            kind = str(entry.get("kind") or "limite")
            label = _CLAUDE_KIND_LABELS.get(kind, kind.replace("_", " "))
            win_id = kind
            scope = entry.get("scope")
            if isinstance(scope, dict) and isinstance(scope.get("model"), dict):
                model = scope["model"].get("display_name") or scope["model"].get("id")
                if model:
                    label = f"{label} · {model}"
                    win_id = f"{kind}:{model}"
            if win_id in seen:
                continue
            seen.add(win_id)
            windows.append(
                _window(
                    win_id,
                    label,
                    normalize_percent(entry.get("percent")),
                    normalize_iso(entry.get("resets_at")),
                    _CLAUDE_KIND_MINUTES.get(kind),
                )
            )

    if windows:
        return windows

    for key, label in (("five_hour", "Sessão · 5 h"), ("seven_day", "Semana · 7 d")):
        entry = payload.get(key)
        if isinstance(entry, dict):
            windows.append(
                _window(
                    key,
                    label,
                    normalize_percent(entry.get("utilization")),
                    normalize_iso(entry.get("resets_at")),
                    _CLAUDE_FALLBACK_MINUTES.get(key),
                )
            )
    return windows


def _fetch_claude(timeout: float) -> dict[str, Any]:
    oauth = read_claude_oauth()
    if not oauth or not oauth.get("accessToken"):
        return _result(
            "claude",
            "auth_required",
            source=CLAUDE_SOURCE,
            message="Credencial do Claude Code não encontrada. Rode `claude` e autentique.",
        )
    if _expired_ms(oauth.get("expiresAt")):
        return _result(
            "claude",
            "auth_required",
            source=CLAUDE_SOURCE,
            message="Token do Claude Code vencido. Abra o `claude` uma vez para renovar.",
        )

    try:
        resp = _http(
            CLAUDE_URL,
            headers={
                "Authorization": f"Bearer {oauth['accessToken']}",
                "anthropic-beta": "oauth-2025-04-20",
                "Accept": "application/json",
                "User-Agent": "ia-quota-widget/0.1.0",
            },
            timeout=timeout,
        )
    except OSError as exc:
        return _result("claude", "error", source=CLAUDE_SOURCE, message=f"Rede indisponível ({type(exc).__name__}).")

    mapped = _STATUS_BY_HTTP.get(resp.status)
    if mapped == "auth_required":
        return _result("claude", "auth_required", source=CLAUDE_SOURCE, message="Sessão recusada (HTTP %d)." % resp.status)
    if mapped == "rate_limited":
        return _result("claude", "rate_limited", source=CLAUDE_SOURCE, message="Consultas demais (HTTP 429).")
    if resp.status >= 400:
        return _result("claude", "error", source=CLAUDE_SOURCE, message=f"Resposta HTTP {resp.status}.")

    try:
        payload = resp.json()
    except ValueError:
        return _result("claude", "error", source=CLAUDE_SOURCE, message="Resposta não é JSON.")

    plan = None
    if isinstance(oauth.get("subscriptionType"), str):
        plan = oauth["subscriptionType"]

    windows = parse_claude_usage(payload)
    if not windows:
        return _result("claude", "unavailable", source=CLAUDE_SOURCE, message="Nenhuma janela de cota na resposta.")
    return _result(
        "claude",
        "ok",
        source=CLAUDE_SOURCE,
        windows=windows,
        fetched_at=_now_iso(),
        message=f"Plano {plan}." if plan else "",
    )


# --------------------------------------------------------------------------
# Gemini CLI — Code Assist
# --------------------------------------------------------------------------

GEMINI_BASE = "https://cloudcode-pa.googleapis.com/v1internal"
GEMINI_SOURCE = "cloudcode-pa.googleapis.com · retrieveUserQuota"


def gemini_credentials_path() -> Path:
    return _home() / ".gemini" / "oauth_creds.json"


def read_gemini_oauth(path: Path | None = None) -> dict[str, Any] | None:
    data = _read_json_file(path or gemini_credentials_path())
    return data if isinstance(data, dict) and data.get("access_token") else None


def parse_gemini_quota(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """``retrieveUserQuota`` -> janelas.

    ``remainingFraction`` é fração RESTANTE; convertemos para percentual usado.
    Bucket sem ``modelId`` ou sem fração é descartado — mesma guarda do Gemini
    CLI, e evita inventar barra a partir de bucket vazio.
    """
    if not isinstance(payload, dict):
        return []
    buckets = payload.get("buckets")
    if not isinstance(buckets, list):
        return []

    windows: list[dict[str, Any]] = []
    for bucket in buckets:
        if not isinstance(bucket, dict):
            continue
        model = bucket.get("modelId")
        used = percent_from_remaining_fraction(bucket.get("remainingFraction"))
        if not model or used is None:
            continue
        token_type = bucket.get("tokenType")
        win_id = f"{model}:{token_type}" if token_type else str(model)
        label = f"{model} · {token_type}" if token_type else str(model)
        windows.append(_window(win_id, label, used, normalize_iso(bucket.get("resetTime"))))
    return windows


def _fetch_gemini_cli(timeout: float) -> dict[str, Any]:
    creds = read_gemini_oauth()
    if not creds:
        return _result(
            "gemini_cli",
            "auth_required",
            source=GEMINI_SOURCE,
            message="Credencial do Gemini CLI não encontrada. Rode `gemini` e autentique.",
        )
    if _expired_ms(creds.get("expiry_date")):
        # Renovar reescreveria ~/.gemini/oauth_creds.json; nesta versão o widget
        # não escreve em credencial de CLI.
        return _result(
            "gemini_cli",
            "auth_required",
            source=GEMINI_SOURCE,
            message="Token do Gemini CLI vencido. Abra o `gemini` uma vez para renovar.",
        )

    headers = {
        "Authorization": f"Bearer {creds['access_token']}",
        "Content-Type": "application/json",
        "User-Agent": "ia-quota-widget/0.1.0",
    }
    load_body = json.dumps(
        {
            "metadata": {
                "ideType": "IDE_UNSPECIFIED",
                "platform": "PLATFORM_UNSPECIFIED",
                "pluginType": "GEMINI",
            }
        }
    ).encode("utf-8")

    try:
        load = _http(f"{GEMINI_BASE}:loadCodeAssist", headers=headers, data=load_body, timeout=timeout)
    except OSError as exc:
        return _result("gemini_cli", "error", source=GEMINI_SOURCE, message=f"Rede indisponível ({type(exc).__name__}).")

    bad = _classify_http(load.status)
    if bad:
        return _result("gemini_cli", bad, source=GEMINI_SOURCE, message=f"loadCodeAssist devolveu HTTP {load.status}.")

    try:
        loaded = load.json()
    except ValueError:
        return _result("gemini_cli", "error", source=GEMINI_SOURCE, message="loadCodeAssist não devolveu JSON.")

    project = loaded.get("cloudaicompanionProject") if isinstance(loaded, dict) else None
    if not project:
        return _result(
            "gemini_cli",
            "unavailable",
            source=GEMINI_SOURCE,
            message="Conta sem projeto Code Assist associado.",
        )

    try:
        quota = _http(
            f"{GEMINI_BASE}:retrieveUserQuota",
            headers=headers,
            data=json.dumps({"project": project}).encode("utf-8"),
            timeout=timeout,
        )
    except OSError as exc:
        return _result("gemini_cli", "error", source=GEMINI_SOURCE, message=f"Rede indisponível ({type(exc).__name__}).")

    bad = _classify_http(quota.status)
    if bad:
        return _result("gemini_cli", bad, source=GEMINI_SOURCE, message=f"retrieveUserQuota devolveu HTTP {quota.status}.")

    try:
        payload = quota.json()
    except ValueError:
        return _result("gemini_cli", "error", source=GEMINI_SOURCE, message="retrieveUserQuota não devolveu JSON.")

    tier = ""
    if isinstance(loaded.get("currentTier"), dict):
        tier = loaded["currentTier"].get("name") or loaded["currentTier"].get("id") or ""

    windows = parse_gemini_quota(payload)
    if not windows:
        return _result("gemini_cli", "unavailable", source=GEMINI_SOURCE, message="Nenhum bucket de cota na resposta.")
    return _result(
        "gemini_cli",
        "ok",
        source=GEMINI_SOURCE,
        windows=windows,
        fetched_at=_now_iso(),
        message=f"Tier {tier}." if tier else "",
    )


def _classify_http(status: int) -> str | None:
    """``None`` quando a resposta serve; senão o status do contrato."""
    mapped = _STATUS_BY_HTTP.get(status)
    if mapped:
        return mapped
    return "error" if status >= 400 else None


# --------------------------------------------------------------------------
# Antigravity — language server local, porta dinâmica em loopback
# --------------------------------------------------------------------------

ANTIGRAVITY_SOURCE = "language server local · RetrieveUserQuotaSummary"
_ANTIGRAVITY_QUOTA_RPC = "exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary"
_ANTIGRAVITY_PROCESS_HINTS = ("antigravity", "language_server", "agy")
_CSRF_PREFIX = 'csrfToken":"'


def _listening_pids() -> list[tuple[int, int]]:
    """(porta, pid) escutando em loopback, via ``netstat -ano``. Só Windows."""
    try:
        out = subprocess.run(  # noqa: S603,S607 - utilitário do sistema, sem entrada do usuário
            ["netstat", "-ano", "-p", "TCP"],
            capture_output=True,
            text=True,
            timeout=8,
            **_NO_WINDOW,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    found: list[tuple[int, int]] = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[3].upper() != "LISTENING":
            continue
        local, pid = parts[1], parts[4]
        if not local.startswith(("127.0.0.1:", "[::1]:")):
            continue
        try:
            found.append((int(local.rsplit(":", 1)[1]), int(pid)))
        except ValueError:
            continue
    return found


def _process_names() -> dict[int, str]:
    try:
        out = subprocess.run(  # noqa: S603,S607
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=8,
            **_NO_WINDOW,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    names: dict[int, str] = {}
    for line in out.splitlines():
        fields = [f.strip('" ') for f in line.split('","')]
        if len(fields) < 2:
            continue
        try:
            names[int(fields[1])] = fields[0].lower()
        except ValueError:
            continue
    return names


def discover_antigravity_bases(
    *,
    env: dict[str, str] | None = None,
    listeners: Iterable[tuple[int, int]] | None = None,
    names: dict[int, str] | None = None,
) -> list[str]:
    """URLs base candidatas, mais específica primeiro.

    Parâmetros injetáveis para o teste não depender de netstat/tasklist reais.
    """
    env = os.environ if env is None else env
    bases: list[str] = []
    override = (env.get("ANTIGRAVITY_LS_ADDRESS") or "").strip()
    if override:
        if "://" not in override:
            override = "http://" + override
        bases.append(override.rstrip("/"))

    pairs = list(_listening_pids() if listeners is None else listeners)
    proc_names = _process_names() if names is None else names
    for port, pid in pairs:
        name = proc_names.get(pid, "")
        if not any(hint in name for hint in _ANTIGRAVITY_PROCESS_HINTS):
            continue
        candidate = f"http://127.0.0.1:{port}"
        if candidate not in bases:
            bases.append(candidate)
    return bases


def extract_csrf(html: str) -> str | None:
    idx = html.find(_CSRF_PREFIX)
    if idx < 0:
        return None
    rest = html[idx + len(_CSRF_PREFIX) :]
    end = rest.find('"')
    return rest[:end] if end > 0 else None


def parse_antigravity_quota(payload: Any) -> list[dict[str, Any]]:
    """Varredura defensiva do ``RetrieveUserQuotaSummary``.

    O formato exato não foi verificado com o language server em execução (ver
    artefato de fontes), então em vez de fixar um caminho procuramos entradas
    que tragam um identificador e uma medida — fração restante ou percentual
    usado. Entrada sem medida legível é descartada, nunca vira 0.
    """
    entries: list[dict[str, Any]] = []

    def collect(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                collect(item)
            return
        if not isinstance(node, dict):
            return
        name = node.get("modelId") or node.get("model") or node.get("name") or node.get("quotaId")
        used = normalize_percent(node.get("usedPercent"))
        if used is None:
            used = percent_from_remaining_fraction(node.get("remainingFraction"))
        if name and used is not None:
            entries.append(
                _window(
                    str(name),
                    str(node.get("label") or name),
                    used,
                    normalize_iso(node.get("resetTime") or node.get("resetsAt")),
                )
            )
            return
        for value in node.values():
            collect(value)

    collect(payload)
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for entry in entries:
        if entry["id"] in seen:
            continue
        seen.add(entry["id"])
        unique.append(entry)
    return unique


def _fetch_antigravity(timeout: float) -> dict[str, Any]:
    bases = discover_antigravity_bases()
    if not bases:
        return _result(
            "antigravity",
            "unavailable",
            source=ANTIGRAVITY_SOURCE,
            message="Antigravity não está em execução; a porta local só existe com o IDE aberto.",
        )

    last = "Sem resposta do language server."
    for base in bases:
        try:
            root = _http(base, headers={"User-Agent": "ia-quota-widget/0.1.0"}, timeout=timeout)
            csrf = extract_csrf(root.body.decode("utf-8", "replace")) if root.status < 400 else None
            headers = {"Content-Type": "application/json", "User-Agent": "ia-quota-widget/0.1.0"}
            if csrf:
                headers["x-codeium-csrf-token"] = csrf
            resp = _http(f"{base}/{_ANTIGRAVITY_QUOTA_RPC}", headers=headers, data=b"{}", timeout=timeout)
        except OSError:
            last = "Porta local encontrada, mas sem resposta."
            continue

        bad = _classify_http(resp.status)
        if bad:
            last = f"Language server devolveu HTTP {resp.status}."
            continue
        try:
            windows = parse_antigravity_quota(resp.json())
        except ValueError:
            last = "Resposta do language server não é JSON."
            continue
        if windows:
            return _result(
                "antigravity",
                "ok",
                source=ANTIGRAVITY_SOURCE,
                windows=windows,
                fetched_at=_now_iso(),
            )
        last = "Language server respondeu sem cota reconhecível."
    return _result("antigravity", "unavailable", source=ANTIGRAVITY_SOURCE, message=last)


# --------------------------------------------------------------------------
# Z.ai — GLM Coding Plan, endpoint de monitor
# --------------------------------------------------------------------------

ZAI_URL = "https://api.z.ai/api/monitor/usage/quota/limit"
ZAI_SOURCE = "api.z.ai/api/monitor/usage/quota/limit"

# `unit` + `number` descrevem a janela. Só os dois pares vistos com dado real
# (260913, plano pro) estão mapeados: unit 3 × 5 renovava em 3,8 h (janela de
# 5 h) e unit 6 × 1 em 5,8 d (semana). Unidade desconhecida fica sem duração
# em vez de ganhar um palpite — o ritmo vira NAO_MEDIDO, não número inventado.
_ZAI_UNIT_MINUTES = {3: 60, 6: 10080}
_ZAI_TYPE_LABELS = {"TIME_LIMIT": "Ferramentas"}


def zai_dpapi_path() -> Path:
    return _home() / ".config" / "zai" / "cli-key.dpapi"


def zcode_config_path() -> Path:
    return _home() / ".zcode" / "v2" / "config.json"


def _dpapi_unprotect(blob: bytes) -> bytes | None:
    """CryptUnprotectData do usuário atual. Fora do Windows, ``None``."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class _Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    buffer = ctypes.create_string_buffer(blob, len(blob))
    source = _Blob(len(blob), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    target = _Blob()
    if not crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(target)):
        return None
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(target.pbData, ctypes.c_void_p))


def read_zai_keys() -> list[str]:
    """Chaves locais já autenticadas, na ordem de preferência, sem repetição.

    1. ``ZAI_API_KEY`` do ambiente;
    2. ``~/.config/zai/cli-key.dpapi`` (``ConvertFrom-SecureString``: hex de um
       blob DPAPI com o texto em UTF-16LE), a chave fixa dos launchers GLM;
    3. provider ``builtin:zai-coding-plan`` do ZCode desktop, se ligado.
    """
    keys: list[str] = []
    env_key = os.environ.get("ZAI_API_KEY", "").strip()
    if env_key:
        keys.append(env_key)
    try:
        text = zai_dpapi_path().read_text(encoding="ascii").strip()
        plain = _dpapi_unprotect(bytes.fromhex(text)) if text else None
        if plain:
            keys.append(plain.decode("utf-16-le").strip())
    except (OSError, ValueError, UnicodeDecodeError):
        pass
    config = _read_json_file(zcode_config_path())
    if isinstance(config, dict):
        entry = (config.get("provider") or {}).get("builtin:zai-coding-plan")
        if isinstance(entry, dict) and entry.get("enabled") is not False:
            api_key = (entry.get("options") or {}).get("apiKey")
            if isinstance(api_key, str) and api_key.strip():
                keys.append(api_key.strip())
    return list(dict.fromkeys(k for k in keys if k))


def parse_zai_quota(payload: Any) -> list[dict[str, Any]]:
    """Envelope ``{code, success, data: {limits[], level}}`` -> janelas.

    ``percentage`` vem arredondado para inteiro (1 com 144 de 12 000), então o
    percentual sai de ``currentValue / usage`` quando os dois existem.
    ``nextResetTime`` é epoch em **milissegundos**.
    """
    data = payload.get("data") if isinstance(payload, dict) else None
    limits = data.get("limits") if isinstance(data, dict) else None
    if not isinstance(limits, list):
        return []
    windows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in limits:
        if not isinstance(entry, dict):
            continue
        kind = str(entry.get("type") or "LIMIT")
        unit, number = entry.get("unit"), entry.get("number")
        minutes = None
        if isinstance(unit, int) and not isinstance(unit, bool) and unit in _ZAI_UNIT_MINUTES:
            minutes = normalize_duration_minutes(number * _ZAI_UNIT_MINUTES[unit]) if isinstance(number, (int, float)) else None
        win_id = f"{kind}:{unit}x{number}"
        if win_id in seen:
            continue
        seen.add(win_id)

        used = None
        total, current = entry.get("usage"), entry.get("currentValue")
        if (
            isinstance(total, (int, float)) and not isinstance(total, bool) and total > 0
            and isinstance(current, (int, float)) and not isinstance(current, bool)
        ):
            used = normalize_percent(current / total * 100.0)
        if used is None:
            used = normalize_percent(entry.get("percentage"))

        reset_ms = entry.get("nextResetTime")
        resets_at = (
            normalize_epoch_seconds(reset_ms / 1000.0)
            if isinstance(reset_ms, (int, float)) and not isinstance(reset_ms, bool)
            else None
        )
        if minutes == 10080:
            label = "Semana"
        elif minutes == 300:
            label = "Sessão"
        else:
            label = _ZAI_TYPE_LABELS.get(kind, "Limite")
            duration = _duration_label(minutes)
            label = f"{label} · {duration}" if duration else label
        windows.append(_window(win_id, label, used, resets_at, minutes))
    return windows


def _fetch_zai(timeout: float) -> dict[str, Any]:
    keys = read_zai_keys()
    if not keys:
        return _result(
            "zai",
            "auth_required",
            source=ZAI_SOURCE,
            message="Chave do GLM Coding Plan não encontrada (DPAPI, ZAI_API_KEY ou ZCode).",
        )

    resp = None
    for key in keys:
        try:
            resp = _http(
                ZAI_URL,
                headers={
                    "Authorization": key,
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en",
                    "User-Agent": "ia-quota-widget/0.1.0",
                },
                timeout=timeout,
            )
        except OSError as exc:
            return _result("zai", "error", source=ZAI_SOURCE, message=f"Rede indisponível ({type(exc).__name__}).")
        # Chave revogada numa fonte não impede a seguinte de servir.
        if resp.status not in (401, 403):
            break

    mapped = _STATUS_BY_HTTP.get(resp.status)
    if mapped == "auth_required":
        return _result("zai", "auth_required", source=ZAI_SOURCE, message="Chave recusada (HTTP %d)." % resp.status)
    if mapped == "rate_limited":
        return _result("zai", "rate_limited", source=ZAI_SOURCE, message="Consultas demais (HTTP 429).")
    if resp.status >= 400:
        return _result("zai", "error", source=ZAI_SOURCE, message=f"Resposta HTTP {resp.status}.")

    try:
        payload = resp.json()
    except ValueError:
        return _result("zai", "error", source=ZAI_SOURCE, message="Resposta não é JSON.")
    if isinstance(payload, dict) and payload.get("code") in (401, 403):
        return _result("zai", "auth_required", source=ZAI_SOURCE, message=f"Chave recusada (código {payload['code']}).")

    windows = parse_zai_quota(payload)
    if not windows:
        return _result("zai", "unavailable", source=ZAI_SOURCE, message="Nenhuma janela de cota na resposta.")
    level = (payload.get("data") or {}).get("level")
    return _result(
        "zai",
        "ok",
        source=ZAI_SOURCE,
        windows=windows,
        fetched_at=_now_iso(),
        message=f"Plano {level}." if isinstance(level, str) and level else "",
    )


# --------------------------------------------------------------------------
# Gemini web/app — sem fonte autorizada
# --------------------------------------------------------------------------

GEMINI_WEB_SOURCE = "sem fonte autorizada"


def _fetch_gemini_web(_timeout: float) -> dict[str, Any]:
    """Permanentemente indisponível, e isso é uma decisão, não uma falha.

    A cota do app do Gemini só é legível por cookie de sessão do navegador, que
    está fora do escopo autorizado. Nada de inferir a partir do Code Assist: é
    outro produto e outra cota.
    """
    return _result(
        "gemini_web",
        "unavailable",
        source=GEMINI_WEB_SOURCE,
        message="O app do Gemini não expõe cota por API; leitura exigiria cookie do navegador.",
    )


# --------------------------------------------------------------------------
# fachada
# --------------------------------------------------------------------------

_FETCHERS: dict[str, Callable[[float], dict[str, Any]]] = {
    "codex": _fetch_codex,
    "claude": _fetch_claude,
    "zai": _fetch_zai,
    "gemini_cli": _fetch_gemini_cli,
    "antigravity": _fetch_antigravity,
    "gemini_web": _fetch_gemini_web,
}


def fetch_provider(provider_id: str, *, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
    """Lê a cota de um provedor. Nunca levanta: falha vira ``status``.

    A UI faz poll por provedor, então uma exceção escapando aqui derrubaria o
    ciclo dos outros quatro.
    """
    fetcher = _FETCHERS.get(provider_id)
    if fetcher is None:
        return _result(provider_id, "error", source="desconhecido", message="Provedor não reconhecido.")
    try:
        return fetcher(timeout)
    except Exception as exc:  # noqa: BLE001 - fronteira do contrato
        return _result(
            provider_id,
            "error",
            source=_FETCHER_SOURCES.get(provider_id, ""),
            message=f"Falha inesperada ({type(exc).__name__}).",
        )


_FETCHER_SOURCES = {
    "codex": CODEX_SOURCE,
    "claude": CLAUDE_SOURCE,
    "zai": ZAI_SOURCE,
    "gemini_cli": GEMINI_SOURCE,
    "antigravity": ANTIGRAVITY_SOURCE,
    "gemini_web": GEMINI_WEB_SOURCE,
}


def fetch_all(*, timeout: float = DEFAULT_TIMEOUT) -> list[dict[str, Any]]:
    return [fetch_provider(pid, timeout=timeout) for pid in PROVIDER_IDS]


def _sanitized(result: dict[str, Any]) -> dict[str, Any]:
    """Cópia segura para log/CLI: só cota, sem plano, e-mail, id ou token."""
    return {
        "provider": result["provider"],
        "status": result["status"],
        "source": result["source"],
        "fetched_at": result["fetched_at"],
        "windows": result["windows"],
    }


if __name__ == "__main__":  # leitura manual read-only
    for item in fetch_all():
        print(json.dumps(_sanitized(item), ensure_ascii=False))
