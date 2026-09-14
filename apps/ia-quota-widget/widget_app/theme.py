from dataclasses import dataclass

BORDER = (255, 255, 255, 35)
TRACK_BG = (255, 255, 255, 19)
FOOT_RULE = (255, 255, 255, 18)

DEFAULT_BG_OPACITY_PERCENT = 76

CORNER_RADIUS = 14
FONT_FAMILY = "Segoe UI"

PROVIDER_DOT_COLORS = {
    "codex": "#d7dde5",
    "spark": "#79c7e8",
    "claude": "#c39782",
    "zai": "#e28fb4",
    "gemini_cli": "#9eb4da",
    "gemini_web": "#7fd0c9",
    "antigravity": "#b98fe0",
}
PROVIDER_LABELS = {
    "codex": "Codex",
    "spark": "Spark",
    "claude": "Claude",
    "zai": "Z.ai",
    "gemini_cli": "Gemini CLI",
    "gemini_web": "Gemini (app)",
    "antigravity": "Antigravity",
}
PROVIDER_SOURCE_HINT = {
    "codex": "Cota da assinatura",
    "spark": "Cota própria do Codex Spark",
    "claude": "Sessão · semana · modelos",
    "zai": "GLM Coding Plan · 5 h · semana",
    "gemini_cli": "CLI local",
    "gemini_web": "Conta web",
    "antigravity": "Fonte identificada à parte",
}

# --------------------------------------------------------------------------
# Presets de superfície — pedido do <USUARIO> 260908 ("nao só cinza ou preto").
# Carvão é o padrão. Todos translúcidos, o alpha vem do controle de opacidade
# que já existe (DEFAULT_BG_OPACITY_PERCENT), não é parte do preset.
# Valores travados por tests/test_contrast.py: texto principal >= 4,5:1 contra
# o preset composto sobre branco puro E sobre preto puro (o widget nao
# controla o que fica atras, entao os dois extremos tem que passar).
# --------------------------------------------------------------------------

SURFACE_PRESETS = {
    "carvao": {
        "label": "Carvão",
        "bg": "#171A1D",
        "text": "#F1F2F4",
        "text_secondary": "#AEB5BF",
        "light": False,
    },
    "meia_noite": {
        "label": "Meia-noite",
        "bg": "#141B2E",
        "text": "#EEF1F7",
        "text_secondary": "#A7B0C4",
        "light": False,
    },
    "ameixa": {
        "label": "Ameixa",
        "bg": "#221A2E",
        "text": "#F2EEF7",
        "text_secondary": "#B6ABC4",
        "light": False,
    },
    "musgo": {
        "label": "Musgo",
        "bg": "#16231C",
        "text": "#EDF3EE",
        "text_secondary": "#A8BCAE",
        "light": False,
    },
    "telha": {
        "label": "Telha",
        "bg": "#2A1B18",
        "text": "#F7EFEC",
        "text_secondary": "#C4ADA6",
        "light": False,
    },
    # Secundário mais escuro que a proposta original (#5A616B -> #383D45):
    # a original passava nos 4,5:1 do texto principal mas o secundário caía a
    # ~2,9:1 contra o extremo escuro. Escurecido até >=4,5:1 nos dois extremos
    # (medido, não estimado — ver tests/test_contrast.py).
    "nevoa": {
        "label": "Névoa",
        "bg": "#E8EAEE",
        "text": "#1A1D21",
        "text_secondary": "#383D45",
        "light": True,
    },
    "papel": {
        "label": "Papel",
        "bg": "#F0EAE0",
        "text": "#231F1A",
        "text_secondary": "#463F34",
        "light": True,
    },
}
DEFAULT_SURFACE_PRESET = "carvao"
SURFACE_PRESET_ORDER = ["carvao", "meia_noite", "ameixa", "musgo", "telha", "nevoa", "papel"]


def surface_preset(preset_id: str) -> dict:
    return SURFACE_PRESETS.get(preset_id, SURFACE_PRESETS[DEFAULT_SURFACE_PRESET])


# Cor de identidade do provider (o pontinho) e cor de estado da barra NAO
# mudam com o preset — é o que dá pra "quanto sobrou" continuar legível na
# troca de tema. O que muda é só a variante clara/escura da PALETA de status,
# porque o verde/âmbar pastel pensado pro carvão quase some num painel claro
# (medido: ~1,8:1 contra Névoa/Papel, bem abaixo de qualquer limiar util).
# Medido contra os 5 presets escuros (tests/test_contrast.py): o vermelho e o
# cinza/vinho originais ficavam entre 1,1:1 e 3,0:1 contra Musgo/Telha — perto
# demais do proprio painel escuro pra contar como aviso. Clareados até
# green/amber/red renderem >=3:1 nos 5 (SC 1.4.11, sao o canal primario do
# percentual). Maroon/grey sao estado "sem numero" com rotulo de texto em
# contraste pleno ao lado (erro/indisponivel) — clareados na medida do
# possivel sem virar identico ao vermelho, sem perseguir 3:1 a qualquer custo.
STATUS_GREEN = "#7cc48f"
STATUS_AMBER = "#e0b46a"
STATUS_RED = "#e89a9a"
STATUS_MAROON = "#c88080"
STATUS_GREY = "#a2a8b1"

STATUS_GREEN_LIGHT = "#1f6b42"
STATUS_AMBER_LIGHT = "#7a4a00"
STATUS_RED_LIGHT = "#9c2b2b"
STATUS_MAROON_LIGHT = "#6b2f2f"
STATUS_GREY_LIGHT = "#4d535b"

_STATUS_COLORS_DARK = {
    "green": STATUS_GREEN,
    "amber": STATUS_AMBER,
    "red": STATUS_RED,
    "maroon": STATUS_MAROON,
    "grey": STATUS_GREY,
}
_STATUS_COLORS_LIGHT = {
    "green": STATUS_GREEN_LIGHT,
    "amber": STATUS_AMBER_LIGHT,
    "red": STATUS_RED_LIGHT,
    "maroon": STATUS_MAROON_LIGHT,
    "grey": STATUS_GREY_LIGHT,
}


def status_colors_for(preset_id: str) -> dict:
    return _STATUS_COLORS_LIGHT if surface_preset(preset_id)["light"] else _STATUS_COLORS_DARK


def palette_for(preset_id: str) -> dict:
    preset = surface_preset(preset_id)
    light = preset["light"]
    return {
        "text": preset["text"],
        "text_secondary": preset["text_secondary"],
        "status": status_colors_for(preset_id),
        "light": light,
        # Branco translúcido some em Papel/Névoa: borda, trilho da barra e
        # contorno do pontinho viram escuros nos presets claros.
        "border": "rgba(0,0,0,0.14)" if light else "rgba(255,255,255,0.14)",
        "track_bg": (0, 0, 0, 30) if light else (255, 255, 255, 30),
        "dot_ring": (0, 0, 0, 110) if light else (255, 255, 255, 45),
    }


# --------------------------------------------------------------------------
# Linhas de tela x fontes consultadas (260913).
# Spark tem cota própria (decisão 260910c) mas chega na mesma leitura do
# Codex, nas janelas `codex_bengalfox:*` — mesmo prefixo que
# apps/automations usa. Vira linha própria SÓ na tela: providers.py e
# dados/orcamento_ia.json continuam com o snapshot inteiro do Codex.
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# Categoria de janela de cota (260914, pedido do <USUARIO>): cada provedor
# pode informar 5 h / dia / semana / mês; a MESMA categoria tem a MESMA cor
# em todos os provedores, pra "5 h" ser reconhecível de relance.
# --------------------------------------------------------------------------

WINDOW_CATEGORY_RULES = [
    ("monthly", ("mensal", "mês", "mes ", "month", "30 d")),
    ("weekly", ("semana", "week", "7 d", "7d", "quinzena")),
    ("daily", ("diário", "diario", "daily", "dia", "24 h")),
    ("session", ("sessão", "sessao", "session", "5 h", "5h", "hora")),
]
# Ids são estáveis entre leituras; o casamento por id vem ANTES do texto,
# que só sobra pra janela nova com nome ainda desconhecido.
WINDOW_ID_CATEGORIES = {
    "session": "session",
    "week": "weekly",
    "weekly_all": "weekly",
    "daily": "daily",
    "monthly": "monthly",
    "codex:primary": "weekly",
    "codex_bengalfox:primary": "session",
    "codex_bengalfox:secondary": "weekly",
}
WINDOW_CATEGORY_COLORS = {
    "session": "#7fd0c9",
    # Não pode ser o STATUS_AMBER: a barrinha "dia" de um vendor saudável
    # ficaria da cor do estado "atenção" da barra-resumo do lado.
    "daily": "#d9c07a",
    "weekly": "#9eb4da",
    "monthly": "#b98fe0",
}
WINDOW_CATEGORY_LABELS = {
    "session": "5 h",
    "daily": "dia",
    "weekly": "semana",
    "monthly": "mês",
}


def window_category(window: dict) -> str | None:
    exact = WINDOW_ID_CATEGORIES.get(str(window.get("id", "")))
    if exact is not None:
        return exact
    label = str(window.get("label", "")).lower()
    for category, needles in WINDOW_CATEGORY_RULES:
        if any(needle in label for needle in needles):
            return category
    return None


def window_category_color(category: str | None) -> str:
    if category is None:
        return STATUS_GREY
    return WINDOW_CATEGORY_COLORS.get(category, STATUS_GREY)


ROW_SOURCE = {"spark": "codex"}


def row_source(row_id: str) -> str:
    return ROW_SOURCE.get(row_id, row_id)


def is_spark_window(window: dict) -> bool:
    return str(window.get("id", "")).startswith("codex_bengalfox:") or "spark" in str(window.get("label", "")).lower()


def _not_spark_window(window: dict) -> bool:
    return not is_spark_window(window)


def row_window_filter(row_id: str):
    if row_id == "spark":
        return is_spark_window
    if row_id == "codex":
        return _not_spark_window
    return None


def expand_rows(provider_ids) -> list[str]:
    rows: list[str] = []
    for provider_id in provider_ids:
        rows.append(provider_id)
        if provider_id == "codex":
            rows.append("spark")
    return rows


def status_track_color(status: str, used_percent, colors: dict | None = None):
    c = colors or _STATUS_COLORS_DARK
    if status == "error":
        return c["maroon"]
    if status in ("unavailable", "auth_required", "rate_limited"):
        return c["grey"]
    if used_percent is None:
        return c["grey"]
    if used_percent >= 90:
        return c["red"]
    if used_percent >= 75:
        return c["amber"]
    return c["green"]


# Poll a cada 120s; uma falha isolada ou algumas seguidas (blip de rede, CLI
# lento) não podem fazer a cor piscar pra cinza/vinho e voltar. Só depois
# desse tempo sem sucesso o dado é velho o bastante pra a cor avisar; até lá
# o texto já mostra a idade, só a cor segura a calma.
STALE_GRACE_SECONDS = 900


def stale_aware_track_color(status: str, used_percent, stale: bool, age_seconds, colors: dict | None = None):
    c = colors or _STATUS_COLORS_DARK
    if not stale:
        return status_track_color(status, used_percent, c)
    if age_seconds is not None and age_seconds < STALE_GRACE_SECONDS:
        return status_track_color("ok", used_percent, c)
    return c["maroon"] if status == "error" else c["grey"]


STATUS_SHORT_LABEL = {
    "ok": None,
    "unavailable": "indisponível",
    "auth_required": "reautenticar",
    "error": "erro",
    "rate_limited": "limitado",
}

SCALE_STEPS = [0.8, 0.9, 1.0, 1.15, 1.3, 1.5]
OPACITY_STEPS = [40, 55, 70, 85, 100]


@dataclass(frozen=True)
class Metrics:
    scale: float = 1.0

    def px(self, base: float) -> int:
        return round(base * self.scale)
