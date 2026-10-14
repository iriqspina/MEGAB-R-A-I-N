import json
from widget_app.snapshot_store import SnapshotStore


def reading():
    return {"status": "ok", "windows": [{"id": "session", "used_percent": 10, "duration_minutes": 300}],
            "fetched_at": "2026-10-12T00:49:23+00:00", "source": "official", "details": {"financial": [{"amount": 250, "currency": "USD"}]}}


def test_restart_retains_dated_reading_and_extra(tmp_path):
    path = tmp_path / "cache.json"
    SnapshotStore(path).update("claude", reading())
    store = SnapshotStore(path)
    saved = store.display("claude")
    assert saved["stale"] and saved["status"] == "cached"
    assert saved["windows"][0]["duration_minutes"] == 300
    assert saved["fetched_at"] == reading()["fetched_at"]
    assert saved["details"]["financial"][0]["amount"] == 250


def test_rate_limit_after_restart_does_not_erase_cache(tmp_path):
    path = tmp_path / "cache.json"
    SnapshotStore(path).update("claude", reading())
    store = SnapshotStore(path)
    store.update("claude", {"status": "rate_limited", "message": "429"})
    assert store.display("claude")["status"] == "rate_limited"
    assert store.display("claude")["windows"][0]["used_percent"] == 10
    assert json.loads(path.read_text())["providers"]["claude"]["status"] == "ok"


def test_new_reading_replaces_saved_values(tmp_path):
    path = tmp_path / "cache.json"
    SnapshotStore(path).update("claude", reading())
    store = SnapshotStore(path)
    current = reading(); current["windows"][0]["used_percent"] = 12
    store.update("claude", current)
    assert SnapshotStore(path).display("claude")["windows"][0]["used_percent"] == 12


def test_broken_cache_has_no_fabricated_quotas(tmp_path):
    path = tmp_path / "cache.json"; path.write_text("broken")
    store = SnapshotStore(path)
    store.update("claude", {"status": "rate_limited"})
    assert store.display("claude")["windows"] == []


def test_session_only_does_not_load_or_write_production_cache(qt_app, tmp_path, monkeypatch):
    from widget_app import paths
    from widget_app.main_window import MainWindow
    monkeypatch.setattr(paths, 'CACHE_PATH', tmp_path / 'isolated-cache.json')
    SnapshotStore(paths.CACHE_PATH).update("claude", reading())
    previous = paths.CACHE_PATH.read_bytes()
    window = MainWindow(session_only=True)
    assert window.store.display("claude") is None
    window.store.update("codex", reading())
    assert paths.CACHE_PATH.read_bytes() == previous


def test_unwritable_cache_keeps_in_memory_reading(tmp_path):
    path = tmp_path / "blocked"; path.mkdir()
    store = SnapshotStore(path); store.update("claude", reading())
    assert store.display("claude")["windows"][0]["used_percent"] == 10


def test_malformed_window_values_are_sanitized_on_restart(tmp_path):
    path = tmp_path / 'cache.json'; raw = reading()
    raw['windows'] = ['x', {'id': 'bad', 'used_percent': '92'}, {'id': 'nan', 'used_percent': float('nan')}, {'id': 'valid', 'used_percent': 10}]
    path.write_text(json.dumps({'schema_version': 1, 'providers': {'claude': raw}}))
    store = SnapshotStore(path)
    assert store.worst_window('claude')['id'] == 'valid'
    assert store.display('claude')['windows'][0]['used_percent'] is None


def test_empty_ok_keeps_last_useful_disk_reading_but_current_is_empty(tmp_path):
    path = tmp_path / 'cache.json'; store = SnapshotStore(path)
    store.update('claude', reading())
    store.update('claude', {'status': 'ok', 'windows': [], 'fetched_at': reading()['fetched_at']})
    store.update('codex', reading())
    assert store.display('claude')['windows'] == []
    assert SnapshotStore(path).display('claude')['windows'][0]['used_percent'] == 10


def test_no_date_does_not_replace_dated_disk_reading(tmp_path):
    path = tmp_path / 'cache.json'; store = SnapshotStore(path)
    store.update('claude', reading())
    store.update('claude', {'status': 'ok', 'windows': [{'used_percent': 80}]})
    assert SnapshotStore(path).display('claude')['fetched_at'] == reading()['fetched_at']
