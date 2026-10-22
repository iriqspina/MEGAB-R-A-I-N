import json
import os
import uuid
from dataclasses import asdict, dataclass, field

from . import paths

# "por enquanto" do <USUARIO> (260908): so Codex e Claude visiveis de saida.
# Provider novo que Opus adicionar e nao estiver aqui nasce visivel, pra nao
# sumir em silencio.
DEFAULT_PROVIDER_VISIBILITY = {
    "codex": True,
    "spark": True,
    "claude": True,
    "zai": True,
    "gemini_cli": False,
    "antigravity": False,
    "gemini_web": False,
}

DEFAULT_SETTINGS = {
    "schema_version": 2,
    # Opt-in until activation by the coordinator; old profiles stay legacy.
    "visual_mode": "legacy",
    "strip_height": 72,
    "strip_width": 800,
    "pos_x": None,
    "pos_y": None,
    "bg_opacity_percent": 76,
    "scale": 1.0,
    "layout": "horizontal",
    "always_on_top": True,
    "expanded": False,
    "visible_providers": dict(DEFAULT_PROVIDER_VISIBILITY),
    "surface_preset": "carvao",
    # 260913 — tamanho escolhido com o mouse (None = ajusta ao conteúdo)
    "window_width": None,
    "window_height": None,
    # 260913 — Configurações: texto
    "font_family": "Segoe UI",
    "size_name": 12,
    "size_value": 19,
    "size_hint": 11,
    "size_detail": 12,
    # 260913 — Configurações: números e exibição
    "number_mode": "used",
    "reset_mode": "relative",
    "show_pacing": True,
    "show_footer": True,
    # 260913 — Configurações: comportamento
    "lock_position": False,
    "click_through": False,
    "snap_edges": True,
    "poll_minutes": 2,
    "alert_percent": 0,
    "provider_order": [],
    "hover_mode": "none",
}


@dataclass
class Settings:
    schema_version: int = 2
    visual_mode: str = "legacy"
    strip_height: int = 72
    strip_width: int = 800
    _extra: dict = field(default_factory=dict, repr=False)
    pos_x: int | None = None
    pos_y: int | None = None
    bg_opacity_percent: int = 76
    scale: float = 1.0
    layout: str = "horizontal"
    always_on_top: bool = True
    expanded: bool = False
    visible_providers: dict = field(default_factory=lambda: dict(DEFAULT_PROVIDER_VISIBILITY))
    surface_preset: str = "carvao"
    window_width: int | None = None
    window_height: int | None = None
    font_family: str = "Segoe UI"
    size_name: int = 12
    size_value: int = 19
    size_hint: int = 11
    size_detail: int = 12
    number_mode: str = "used"
    reset_mode: str = "relative"
    show_pacing: bool = True
    show_footer: bool = True
    lock_position: bool = False
    click_through: bool = False
    snap_edges: bool = True
    poll_minutes: int = 2
    alert_percent: int = 0
    provider_order: list = field(default_factory=list)
    hover_mode: str = "none"

    def is_visible(self, provider_id: str) -> bool:
        return self.visible_providers.get(provider_id, True)

    def set_visible(self, provider_id: str, visible: bool) -> None:
        self.visible_providers[provider_id] = visible

    def to_dict(self) -> dict:
        values = asdict(self)
        extra = values.pop("_extra")
        return {**extra, **values}


def migrate_settings(raw: dict) -> dict:
    """Add missing keys in memory; retain unknown keys and user preferences."""
    merged = {**DEFAULT_SETTINGS, **raw}
    version = raw.get("schema_version", 1)
    merged["schema_version"] = max(2, version) if isinstance(version, int) else 2
    return merged


def load_settings() -> Settings:
    paths.ensure_data_dir()
    if not paths.SETTINGS_PATH.exists():
        return Settings()
    try:
        raw = json.loads(paths.SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return Settings()
    if not isinstance(raw, dict):
        return Settings()
    merged = migrate_settings(raw)
    known = {f for f in DEFAULT_SETTINGS}
    return Settings(**{k: v for k, v in merged.items() if k in known},
                    _extra={k: v for k, v in raw.items() if k not in known})


def save_settings(settings: Settings) -> None:
    paths.ensure_data_dir()
    temp = paths.SETTINGS_PATH.with_name(paths.SETTINGS_PATH.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temp.write_text(json.dumps(settings.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, paths.SETTINGS_PATH)
    finally:
        if temp.exists():
            temp.unlink()
