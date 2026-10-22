"""261020 · A1/A2/A3/A8: estado de conta, detalhes Z.ai, plano canônico e
botão universal de recarregar. Nada aqui pode tocar rede ou dado real
(conftest isola paths e bloqueia socket)."""

import json

import pytest

from test_main_window import window  # noqa: F401  (fixture reutilizada)

from widget_app import account_state
from widget_app.providers_bridge import normalize_snapshot


def _escrever_orcamento(tmp_path, dados):
    caminho = tmp_path / "orcamento.json"
    caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return caminho


def test_estado_de_le_estados_conta_e_legado(tmp_path):
    caminho = _escrever_orcamento(
        tmp_path,
        {
            "estados_conta": {
                "zai": {"estado": "ativo"},
            },
            "outro_cancelado": {"observacao": "cancelado ontem"},
        },
    )
    account_state._cache.update({"lido_em": 0.0, "dados": {}})
    assert account_state.estado_de("zai", caminho)["estado"] == "ativo"
    legado = account_state.estado_de("outro", caminho)
    assert legado["estado"] == "cancelado"
    assert legado["observacao"] == "cancelado ontem"
    assert account_state.estado_de("desconhecido", caminho) is None


def test_texto_curto_TRAZ_selto_e_data(tmp_path):
    texto = account_state.texto_curto(
        {"estado": "cancelado", "acesso_ate": "2026-10-16T21:00:00-03:00"}
    )
    assert texto == "CANCELADO · até 16/10"
    assert account_state.texto_curto({"estado": "encerrado"}) == "ENCERRADO"


def test_normalize_snapshot_anexa_estado_de_conta(tmp_path, monkeypatch):
    from widget_app import paths

    caminho = _escrever_orcamento(
        tmp_path,
        {"estados_conta": {"codex_gpt2": {"estado": "cancelado"}}},
    )
    monkeypatch.setattr(paths, "BUDGET_STATUS_PATH", caminho)
    account_state._cache.update({"lido_em": 0.0, "dados": {}})
    snapshot = normalize_snapshot(
        "codex_gpt2",
        {"status": "ok", "windows": [], "message": "Plano Plus.", "fetched_at": "2026-10-20T18:00:00+00:00"},
    )
    assert snapshot["account_state"]["estado"] == "cancelado"
    sem_estado = normalize_snapshot("claude", {"status": "ok", "windows": []})
    assert "account_state" not in sem_estado


def test_zai_details_notas_por_janela_e_nada_inventado():
    from quota_details_data import sanitize_details, zai_details

    payload = {"data": {"level": "pro", "limits": [{"type": "CREDIT_LIMIT"}]}}
    windows = [
        {"id": "CREDIT_LIMIT:3x5", "label": "Sessão", "used_percent": 25.0},
        {"id": "CREDIT_LIMIT:6x1", "label": "Semana", "used_percent": None},
    ]
    notas = sanitize_details(zai_details(payload, windows))["notes"]
    assert any("Plano pro" in n for n in notas)
    assert any("Sessão: 75.0% livre" in n for n in notas)
    # Janela sem percentual não ganha linha — nada inventado.
    assert not any("Semana:" in n for n in notas)
    assert any("não são dólares" in n for n in notas)


def test_plan_display_usa_linguagem_do_vendor():
    from providers import plan_display

    assert plan_display("prolite") == "Pro Lite"
    assert plan_display("plus") == "Plus"
    assert plan_display("max") == "Max"
    assert plan_display("pro") == "Pro"
    assert plan_display("NovoPlano") == "NovoPlano"


def test_codex_effort_notes_le_config_local(tmp_path):
    from providers import codex_effort_notes

    config = tmp_path / "config.toml"
    config.write_text(
        'model = "gpt-6.1-sol"\nmodel_reasoning_effort = "high"\n'
        'enabled-reasoning-efforts = ["low", "medium", "high", "xhigh"]\n',
        encoding="utf-8",
    )
    notas = codex_effort_notes({"CODEX_HOME": str(tmp_path)})
    assert notas[0] == "Esforços disponíveis: low, medium, high, xhigh."
    assert "esforço configurado: high" in notas[1]
    assert "modelo: gpt-6.1-sol" in notas[1]
    assert codex_effort_notes({"CODEX_HOME": str(tmp_path / "vazio")}) == []


def test_popup_translate_label_cru_do_vendor():
    from widget_app.formatting import friendly_window_label

    assert friendly_window_label("codex · 7 d") == "Semana"
    assert friendly_window_label("codex · 5 h") == "Sessão"


def test_manual_refresh_forca_todas_as_fontes(window, monkeypatch):
    capturado = {}
    monkeypatch.setattr(window, "poll_now", lambda force=False: capturado.update(force=force))
    window.manual_refresh()
    assert capturado["force"] is True


def test_poll_now_force_ignora_backoff(window, monkeypatch):
    window.demo = False

    class BackoffMorto:
        @staticmethod
        def ready(_pid):
            return False  # tudo em pausa: sem force, nada seria consultado

    consultados = {}
    monkeypatch.setattr(window, "_backoff", BackoffMorto())
    monkeypatch.setattr(window, "_visible_sources", lambda: ["codex", "zai"])
    monkeypatch.setattr(window, "_querying", set())
    monkeypatch.setattr(window, "poller", type("P", (), {"poll": staticmethod(lambda ids: consultados.update(ids=ids))})())
    for nome in ("_refresh_all_segments", "_update_refresh_feedback", "_schedule_fit"):
        monkeypatch.setattr(window, nome, lambda: None)

    window.poll_now(force=True)
    assert sorted(consultados["ids"]) == ["codex", "zai"]

    consultados.clear()
    window.poll_now(force=False)
    assert "ids" not in consultados  # backoff segurou tudo, como antes


def test_card_mostra_selto_cancelado_no_hint(window):
    window.store.update(
        "codex_gpt2",
        {
            "provider": "codex_gpt2",
            "label": "Codex GPT2",
            "status": "ok",
            "windows": [{"id": "codex:primary", "label": "Semana", "used_percent": 0.0, "resets_at": "2026-10-27T00:00:00+00:00"}],
            "message": "Plano Plus.",
            "fetched_at": "2026-10-20T18:37:46+00:00",
            "account_state": {"estado": "cancelado", "acesso_ate": "2026-10-16T21:00:00-03:00", "api_respondeu_em": "2026-10-20T18:37:46+00:00"},
        },
    )
    segmento = window._segments["codex_gpt2"]
    segmento.update_from_store(window.store, expanded=False)
    hint = segmento._hint.text()
    assert "CANCELADO" in hint
    assert "API respondeu" in hint
    tooltip = segmento._name_wrap.toolTip()
    assert "contradição" in tooltip
