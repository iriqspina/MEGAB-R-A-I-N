"""Declarative contract for the always-open board (Trilho column and Legacy card).

One list of fields per provider row: id/kind/group/format. The main widget and
the Settings preview consume the SAME list, so nothing is rendered twice in two
different ways. Unknown values stay "—", never 0. Automatic data (polled) and
browser evidence (manual verification, own date) are different kinds.
"""
from dataclasses import dataclass
from datetime import timedelta, timezone
import json
from math import isfinite

from . import paths, theme
from .formatting import age_label, parse_iso, reset_label, reset_label_absolute
from .observed_info import observed_resets
from quota_details_data import resolve_resets
from .quota_focus import duration_label, duration_minutes, is_reserve

BRT = timezone(timedelta(hours=-3))
QUOTA_KINDS = ("quota", "caption")
TRACK_KINDS = ("quota", "ratio")
UNKNOWN = "—"
LEGEND = "* navegador: verificação manual, data própria"


@dataclass(frozen=True)
class Field:
    id: str
    kind: str              # quota | caption | status | reset | financial | share | browser | source | legend | note
    text: str = ""
    label: str = ""        # quota rows: window label
    group: str = ""        # quota rows: general | specific | reserve
    percent: float | None = None   # quota rows: already in number_mode, 0..100 scale
    color: str | None = None
    tooltip: str = ""


def schema(fields) -> tuple:
    return tuple((f.id, f.kind) for f in fields)


def short_date(value) -> str:
    parsed = parse_iso(value)
    return parsed.astimezone(BRT).strftime("%d/%m %H:%M") if parsed and parsed.tzinfo else UNKNOWN


def full_date(value) -> str:
    parsed = parse_iso(value)
    return parsed.astimezone(BRT).strftime("%d/%m/%Y %H:%M BRT") if parsed and parsed.tzinfo else "data não informada"


def _short(text, limit=34) -> str:
    """Long tokens (URLs, paths) cannot wrap inside a narrow column."""
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _number(value, currency="") -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        return UNKNOWN
    text = f"{value:,.2f}".replace(",", " ").replace(".", ",")
    if currency == "créditos":
        return f"{text} créditos"
    return f"{currency} {text}".strip()


def _precise(value) -> str:
    return UNKNOWN if value is None else f"{value:.1f}".rstrip("0").rstrip(".").replace(".", ",") + "%"


def row_windows(row_id, windows):
    windows = list(windows or [])
    if row_id == "spark":
        return [w for w in windows if theme.is_spark_window(w)]
    if str(row_id).startswith("codex"):
        return [w for w in windows if not theme.is_spark_window(w)]
    return windows


def window_group(window) -> str:
    if is_reserve(window):
        return "reserve"
    return "specific" if str(window.get("id", "")).startswith("weekly_scoped") else "general"


def window_label(window) -> str:
    label = theme.window_display_label(window)
    if not label:
        label = duration_label(window) if duration_minutes(window) else _short(window.get("label") or window.get("id") or "janela ?", 18)
    window_id = str(window.get("id", ""))
    if window_id.startswith("weekly_scoped:"):
        label = _short(window_id.split(':', 1)[1], 14)
    elif is_reserve(window):
        label = "reserva"
    return label


def reset_text(value, reset_mode="relative") -> str:
    text = reset_label_absolute(value) if reset_mode == "absolute" else reset_label(value)
    return "↻ ?" if text == "renovação desconhecida" else text.replace("renova ", "↻ ", 1)


NOT_STARTED_TEXT = "não iniciada"  # termo convergente dos 3 layouts cegos 261012


def window_not_started(window, fetched_at) -> bool:
    """Deprecated compatibility API: no factual start signal is available.

    The current normalized window contract exposes only id, label, used_percent,
    resets_at and duration_minutes. Keep the signature for existing callers.
    Zero use, missing reset and a reset equal to fetched time + duration are
    insufficient evidence of inactivity.
    """
    return False


def browser_account(row_id):
    """Last browser verification for this account, or None. Never invented."""
    try:
        data = json.loads((paths.DATA_DIR / "account_balance_observed.json").read_text(encoding="utf-8"))
        item = (data.get("accounts") or {}).get(row_id)
        if not isinstance(item, dict):
            return None
        resets, reset_stamp = observed_resets(row_id)
        return {**item, "balance": item.get("balance"), "currency": item.get("currency", ""),
                "observed_at": item.get("observed_at") or data.get("observed_at"),
                "scope": item.get("scope"), "source": item.get("source"),
                "unavailable": item.get("verification_status") == "unavailable",
                "resets": resets, "reset_observed_at": reset_stamp}
    except (OSError, ValueError, TypeError, AttributeError):
        return None


_RESET_KIND = {"full": "completo", "five_hour": "5 h", "account": "gratuito"}


def _reset_field(index, item, browser_stamp=None) -> Field:
    count = item.get("count")
    total = item.get("total")
    amount = UNKNOWN if count is None else (f"{count}/{total}" if total is not None else str(count))
    state = "disponível" if item.get("usable") else "indisponível"
    if item.get("kind") == "account":
        state = "estoque; sujeito à elegibilidade" if count else "sem estoque" if count == 0 else "estoque desconhecido"
    text = f"♻ {_RESET_KIND.get(item.get('kind'), _short(item.get('title') or 'reset', 16))}: {amount} · {state}"
    if item.get("expires_at"):
        text += f" · até {short_date(item['expires_at'])[:5]}"
    tooltip = f"{item.get('title') or 'Reset'} · {amount} restante(s) · {state}"
    if item.get("expires_at"):
        tooltip += f" · validade {full_date(item['expires_at'])}"
    if browser_stamp is not None:
        text += " *"
        tooltip += f" · navegador, verificado {full_date(browser_stamp)}"
    return Field(f"reset:{item.get('kind') or 'unknown'}:{index}", "reset", text, tooltip=tooltip)


def provider_fields(row_id, display, *, number_mode="used", reset_mode="relative",
                    querying=False, browser=None, name="") -> list[Field]:
    """Every piece of information the row has, in a fixed reading order."""
    fields: list[Field] = []
    if display is None:
        return [Field("status", "status", "consultando…" if querying else "aguardando consulta")]
    status = display.get("status")
    windows = row_windows(row_id, display.get("windows"))

    ordered = sorted(enumerate(windows), key=lambda pair: (
        {"general": 0, "specific": 1, "reserve": 2}[window_group(pair[1])],
        duration_minutes(pair[1]) or 10 ** 9, pair[0]))
    captions = {"specific": "◎ cota específica · também consome a geral", "reserve": "◇ reserva · separada do uso geral"}
    shown_groups = set()
    for _, window in ordered:
        group = window_group(window)
        if group in captions and group not in shown_groups:
            fields.append(Field(f"caption:{group}", "caption", captions[group]))
        shown_groups.add(group)
        used = window.get("used_percent")
        used = used if isinstance(used, (int, float)) and not isinstance(used, bool) else None
        remaining = None if used is None else max(0.0, 100.0 - used)
        shown = remaining if number_mode == "remaining" else used
        label = window_label(window)
        tooltip = (f"{name or row_id} · {window.get('label') or window.get('id')} · {duration_label(window)}\n"
                   f"{_precise(used)} usado · {_precise(remaining)} livre · renova {full_date(window.get('resets_at'))}")
        not_started = window_not_started(window, display.get("fetched_at"))
        if not_started:
            tooltip += "\nJanela não iniciada: uso zero e sem contagem real; começa a contar no primeiro uso."
        fields.append(Field(f"quota:{window.get('id') or window.get('label')}", "quota",
                            NOT_STARTED_TEXT if not_started else reset_text(window.get("resets_at"), reset_mode),
                            label=label, group=group,
                            percent=shown, color=theme.window_category_color(theme.window_category(window)),
                            tooltip=tooltip))
    if not windows:
        state = "sem janela nesta conta" if status == "ok" else f"{theme.STATUS_SHORT_LABEL.get(status) or status} · sem dado"
        fields.append(Field("status", "status", state, tooltip=display.get("message") or state))

    if row_id == "spark":
        fields.append(Field("note:spark", "note", "resets e saldo: ver Codex"))
    else:
        fields.extend(_extras(row_id, display, browser))

    source = display.get("source") or "fonte não informada"
    fetched = display.get("fetched_at")
    fields.append(Field("source", "source", f"auto · {source} · {full_date(fetched)}",
                        tooltip=f"Consulta automática · fonte: {display.get('source') or 'não informada'} · {full_date(fetched)}"))
    return fields


def _extras(row_id, display, browser) -> list[Field]:
    fields: list[Field] = []
    details = display.get("details") or {}
    reset_state=resolve_resets(details,browser,fetched_at=display.get('fetched_at'),stale=display.get('stale') or display.get('status')!='ok')
    live_resets = reset_state['current']
    browser_used=bool(live_resets and reset_state['source']=='browser')
    for index, item in enumerate(live_resets):
        fields.append(_reset_field(index, item,reset_state['observed_at'] if reset_state['source']=='browser' else None))
    if not live_resets:
        fields.append(Field("reset:none", "reset", f"♻ resets: {UNKNOWN} não confirmado",
                            tooltip="Estoque atual não confirmado; histórico não é disponibilidade. Não é zero."))

    financial = details.get("financial") or []
    for index, item in enumerate(financial):
        unit = item.get("currency", "")
        value = "sem limite" if item.get("status") == "unlimited" else _number(item.get("amount"), unit)
        total = item.get("total")
        if isinstance(total, (int, float)) and not isinstance(total, bool) and value not in (UNKNOWN, "sem limite"):
            value += f" / {_number(total)}"
        text = f"$ {_short(item.get('title') or 'Saldo', 22)}: {value}"
        if item.get("expires_at"):
            text += f" · até {short_date(item['expires_at'])[:5]}"
        tooltip = f"{item.get('title') or 'Saldo'} · {value}. {item.get('note') or ''}".strip()
        fields.append(Field(f"financial:{index}", "financial", text, tooltip=tooltip))
        amount = item.get("amount")
        if (isinstance(total, (int, float)) and not isinstance(total, bool) and isfinite(total) and total > 0
                and isinstance(amount, (int, float)) and not isinstance(amount, bool) and isfinite(amount)):
            fields.append(Field(f"financial:{index}:ratio", "ratio", "crédito", label="nuvem" if 'nuvem' in str(item.get('title')).lower() else "saldo",
                                group="credit", percent=max(0,min(100,amount/total*100)), color=theme.STATUS_GREEN,
                                tooltip=f"Crédito monetário: {value}. Não é cota da assinatura."))
        if item.get("note"):
            fields.append(Field(f"financial:{index}:note", "note", str(item["note"])))
    if not financial and row_id == "zai":
        fields.append(Field("financial:none", "financial", f"$ saldo: {UNKNOWN} não exposto pela consulta",
                            tooltip="O leitor de cotas não expõe saldo. Zero não é presumido."))

    shares = details.get("product_shares") or []
    if shares:
        fields.append(Field("share", "share", "◉ participação no uso semanal (não é cota)",
                            tooltip="Participação de cada produto no consumo semanal; não é saldo de cada produto."
                                    + (f" Dados de {full_date(details.get('product_shares_as_of'))}." if details.get("product_shares_as_of") else "")))
        for index,item in enumerate(shares):
            amount=item.get('percent')
            amount=amount if isinstance(amount,(int,float)) and not isinstance(amount,bool) and isfinite(amount) and 0<=amount<=100 else None
            fields.append(Field(f"share:{index}","ratio","do uso",label=str(item.get('name') or 'produto'),group="share",percent=amount,color=theme.STATUS_AMBER,
                                tooltip=f"{item.get('name')}: {_precise(amount)} do consumo semanal; não é cota restante."))
        if details.get("product_shares_as_of"):
            fields.append(Field("share:date","source",f"◷ Produtos: {full_date(details['product_shares_as_of'])}"))

    if browser and (browser.get("balance") is not None or browser.get("observed_at")):
        value = _number(browser.get("balance"), browser.get("currency", ""))
        text = f"$ saldo*: {value} · {short_date(browser.get('observed_at'))}"
        if browser.get("unavailable"):
            text += " · verificação recente falhou"
        fields.append(Field("browser:balance", "browser", text,
                            tooltip=f"Última verificação no navegador: {full_date(browser.get('observed_at'))} · "
                                    f"escopo {browser.get('scope') or 'não informado'} · fonte {browser.get('source') or 'não informada'}"))
        fields.append(Field("browser:source","source",f"navegador · {browser.get('source') or 'fonte não informada'} · {full_date(browser.get('observed_at'))}"))
        if browser.get('scope'):fields.append(Field('browser:scope','note',str(browser['scope'])))
        if row_id=='claude':
            fields.append(Field('browser:spending','browser',f"$ Gasto mensal: {_number(browser.get('monthly_spent'),'BRL')} · teto: {_number(browser.get('monthly_cap'),'BRL')} (teto não é saldo)"))
            if 'extra_enabled' in browser or 'auto_reload' in browser:
                fields.append(Field('browser:controls','browser',f"Uso extra: {'ligado' if browser.get('extra_enabled') else 'desligado'} · recarga automática: {'ligada' if browser.get('auto_reload') else 'desligada'}"))
        if row_id=='zai':
            fields.append(Field('browser:composition','browser',f"Dinheiro: {_number(browser.get('cash'),'USD')} · bônus: {_number(browser.get('bonus'),'USD')}"))
            if 'auto_reload' in browser:fields.append(Field('browser:controls','browser',f"Recarga automática: {'ligada' if browser['auto_reload'] else 'desligada'} · separado do Coding Plan"))
        browser_used = True
    if browser_used:
        fields.append(Field("legend", "legend", LEGEND))
    for index,note in enumerate(details.get('notes') or []):
        fields.append(Field(f'note:{index}', 'note', str(note)))
    return fields


def header_state(display, querying=False) -> tuple[str, str]:
    """(symbol, text) for the compact column header: status + freshness."""
    if querying:
        return "↻", "consultando"
    if display is None:
        return "○", "aguardando"
    status = display.get("status")
    if status == 'cached':
        return "◷", f"salvo · {age_label(display.get('fetched_at'))}"
    if status not in (None, "ok"):
        age = f" · dado {age_label(display.get('fetched_at'))}" if display.get("fetched_at") else ""
        return "!", f"{theme.STATUS_SHORT_LABEL.get(status) or status}{age}"
    if display.get("stale"):
        return "◷", f"antigo · {age_label(display.get('fetched_at'))}"
    return "●", age_label(display.get("fetched_at"))
