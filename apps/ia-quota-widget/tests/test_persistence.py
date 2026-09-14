import json

from widget_app import persistence


def test_default_settings_have_codex_and_claude_visible_gemini_family_off():
    settings = persistence.Settings()
    assert settings.is_visible("codex") is True
    assert settings.is_visible("claude") is True
    assert settings.is_visible("gemini_cli") is False
    assert settings.is_visible("antigravity") is False
    assert settings.is_visible("gemini_web") is False


def test_unknown_provider_defaults_visible_so_it_never_silently_disappears():
    settings = persistence.Settings()
    assert settings.is_visible("um-provider-que-nao-existe-ainda") is True


def test_set_visible_round_trips_through_disk(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence.paths, "DATA_DIR", tmp_path)
    monkeypatch.setattr(persistence.paths, "SETTINGS_PATH", tmp_path / "settings.json")

    settings = persistence.load_settings()
    settings.set_visible("gemini_cli", True)
    settings.surface_preset = "papel"
    persistence.save_settings(settings)

    reloaded = persistence.load_settings()
    assert reloaded.is_visible("gemini_cli") is True
    assert reloaded.is_visible("codex") is True
    assert reloaded.surface_preset == "papel"


def test_old_settings_file_without_new_fields_still_loads(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence.paths, "DATA_DIR", tmp_path)
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr(persistence.paths, "SETTINGS_PATH", settings_path)
    settings_path.write_text(json.dumps({"pos_x": 10, "pos_y": 20}), encoding="utf-8")

    settings = persistence.load_settings()
    assert settings.pos_x == 10
    assert settings.is_visible("codex") is True
    assert settings.surface_preset == "carvao"


def test_visible_providers_defensive_copy_not_shared_between_instances():
    a = persistence.Settings()
    b = persistence.Settings()
    a.set_visible("gemini_cli", True)
    assert b.is_visible("gemini_cli") is False
