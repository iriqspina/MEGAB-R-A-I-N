import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = APP_DIR / "app" / "data"
SETTINGS_PATH = DATA_DIR / "settings.json"
CACHE_PATH = DATA_DIR / "last_snapshot.json"
SINGLETON_KEY = "ia-quota-widget-260908-singleton"

# Raiz do MEGABRAIN — apps/ia-quota-widget fica duas pastas abaixo dela. O
# mesmo arquivo em dados/orcamento_ia.json também é escrito pelo motor de
# orquestração (apps/automations), por isso o caminho precisa bater com
# `config["central"]` de lá — ver apps/automations/automations.py::load_config.
CENTRAL_DIR = Path(os.environ.get("MEGABRAIN_CENTRAL") or os.environ.get("MEGABRAIN_HOME") or APP_DIR.parent.parent)
BUDGET_STATUS_PATH = CENTRAL_DIR / "dados" / "orcamento_ia.json"
MCP_HEALTH_PATH = CENTRAL_DIR / "dados" / "saude_mcp.json"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
