"""Allowlisted supplementary usage data. Never copy a raw account response."""
import math
from datetime import datetime,timezone


def timestamp(value):
    try:
        if isinstance(value,bool):return None
        parsed=datetime.fromtimestamp(value,timezone.utc) if isinstance(value,(int,float)) else datetime.fromisoformat(value.replace('Z','+00:00')) if isinstance(value,str) else None
        return parsed.astimezone(timezone.utc).isoformat() if parsed and parsed.tzinfo else None
    except (ValueError,OverflowError,OSError):return None


def number(value):
    if isinstance(value, bool):
        return None
    try:
        result=float(value)
    except (ValueError, TypeError):
        return None
    return result if math.isfinite(result) and result >= 0 else None


def money(value):
    if not isinstance(value, dict):
        return None
    value=value.get('money') if 'money' in value else value
    if not isinstance(value, dict):
        return None
    minor=number(value.get('amount_minor')); exponent=value.get('exponent')
    currency=value.get('currency')
    if minor is None or isinstance(exponent,bool) or not isinstance(exponent,int) or not 0 <= exponent <= 6 or currency not in ('USD','BRL','CNY','EUR','GBP'):
        return None
    return minor/(10**exponent), currency


def financial(title, amount=None, currency='', note='', **extra):
    return dict(title=title,amount=number(amount),currency=currency,status='measured' if number(amount) is not None else 'unavailable',note=note,**extra)


def codex_details(payload):
    if not isinstance(payload,dict):
        return {}
    rates=payload.get('rateLimitsByLimitId')
    general=rates.get('codex') if isinstance(rates,dict) else payload.get('rateLimits')
    general=general if isinstance(general,dict) else {}
    credits=general.get('credits') or {}
    row=financial('Saldo extra Codex',credits.get('balance'), 'créditos',
                  'Unidade retornada pelo Codex; não converter em dólares nem somar à assinatura.')
    if credits.get('unlimited') is True:
        row.update(amount=None,status='unlimited',note='Créditos sem limite informado pelo fornecedor.')
    resets=payload.get('rateLimitResetCredits')
    notes=[]; reset_rows=[]
    if isinstance(resets,dict) and number(resets.get('availableCount')) is not None:
        reset_rows.append({'title':'Resets gratuitos Codex','count':int(number(resets['availableCount'])),'kind':'account','usable':number(resets['availableCount'])>0})
    return {'financial':[row],'notes':notes,'product_shares':[],'resets':reset_rows,
            'resets_status':'reported' if reset_rows else 'unknown'}


def claude_details(payload):
    if not isinstance(payload,dict):
        return {}
    shares=[]
    breakdown=payload.get('seven_day_breakdown')
    if isinstance(breakdown,dict):
        for row in breakdown.get('rows') or []:
            if not isinstance(row,dict):continue
            pct=number(row.get('percent'))
            if pct is not None and pct<=100:
                shares.append({'name':str(row.get('display_name') or row.get('key') or 'Produto')[:80], 'percent':pct})
    rows=[]
    # This field was matched to the official web UI in the current audit:
    # 250/250 USD, expiry 05 Nov 04:59 BRT. No inferred opaque mappings.
    cloud=payload.get('iguana_necktie')
    if isinstance(cloud,dict) and number(cloud.get('remaining_dollars')) is not None:
        rows.append(financial('Sessões na nuvem',cloud['remaining_dollars'],'USD',
                              'Crédito para sessões na nuvem, separado da assinatura.',total=number(cloud.get('limit_dollars')),expires_at=timestamp(cloud.get('resets_at'))))
    spend=payload.get('spend') or {}
    extra=payload.get('extra_usage') or {}
    balance=money(spend.get('balance'))
    rows.append(financial('Créditos de uso',*(balance or (None,'')),
                          note='Uso extra '+('ligado' if extra.get('is_enabled') is True else 'desligado' if extra.get('is_enabled') is False else 'não informado')+'. '+('Saldo não exposto por esta consulta.' if balance is None else 'Saldo disponível retornado pelo fornecedor.')))
    for title,key in [('Gasto neste período','used'),('Teto de gasto','cap')]:
        item=money(spend.get(key))
        if item:rows.append(financial(title,*item,note='Teto é limite configurado, não saldo.' if key=='cap' else 'Gasto informado pela consulta de uso.'))
    reset_rows=[]
    offers=payload.get('cedar_ember')
    if isinstance(offers,dict):
        for grant in offers.get('grants') or []:
            if not isinstance(grant,dict):continue
            count=number(grant.get('resets_left')); total=number(grant.get('resets_total'))
            if count is not None and count.is_integer():
                kind=grant.get('type')
                reset_rows.append({'title':'Reset completo' if kind=='full' else 'Reset de 5 horas' if kind=='five_hour' else 'Oferta de reset',
                     'count':int(count),'total':int(total) if total is not None and total.is_integer() else None,'kind':str(kind or 'unknown'),
                     'expires_at':timestamp(grant.get('ends_at')),'usable':grant.get('usable_now') is True and grant.get('paused') is not True})
    grants=offers.get('grants') if isinstance(offers,dict) else None
    reset_status='reported' if reset_rows else 'none' if isinstance(grants,list) and not grants else 'unknown'
    if isinstance(grants,list) and len(reset_rows)!=len(grants):reset_status='unknown'
    return {'financial':rows,'product_shares':shares,'resets':reset_rows,'resets_status':reset_status,'product_shares_as_of':breakdown.get('as_of') if isinstance(breakdown,dict) else None,
            'notes':['Participação por produto divide o consumo semanal; não é saldo individual de cada produto.']}


def zai_details(payload, windows=None):
    """Envelope ``{data: {limits[], level}}`` + janelas parseadas -> notas.

    Sem dinheiro: os valores da API são créditos de uso por janela, não saldo
    em moeda. Reusa ``parse_zai_quota`` (mesma fonte) para não re-derivar
    duração; campo que a API não dá não aparece.
    """
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    level = data.get("level")
    notes = [f"Plano {level}." if isinstance(level, str) and level else "Plano não informado pela API."]
    for window in windows or []:
        if not isinstance(window, dict):
            continue
        nome = str(window.get("label") or window.get("id") or "Limite")
        usado = number(window.get("used_percent"))
        if usado is not None:
            notes.append(f"{nome}: {100.0 - usado:.1f}% livre.")
    notes.append("Valores em créditos de uso da API Z.ai; não são dólares nem assinatura.")
    return {'financial': [], 'product_shares': [], 'notes': notes[:10], 'resets': []}


def sanitize_details(raw):
    """Normalize only documented UI fields, including zero; null stays missing."""
    if not isinstance(raw,dict):return {}
    out={'financial':[],'product_shares':[],'notes':[],'resets':[]}
    if raw.get('resets_status') in ('reported','none','unknown'):
        out['resets_status']=raw['resets_status']
    for item in raw.get('financial') or []:
        if not isinstance(item,dict):continue
        row={k:str(item[k])[:300] for k in ('title','currency','status','note','expires_at') if isinstance(item.get(k),str)}
        for key in ('amount','total'):
            if key in item:row[key]=number(item[key])
        out['financial'].append(row)
    for item in raw.get('product_shares') or []:
        if isinstance(item,dict) and number(item.get('percent')) is not None and number(item['percent'])<=100:
            out['product_shares'].append({'name':str(item.get('name','Produto'))[:80],'percent':number(item['percent'])})
    out['notes']=[str(v)[:300] for v in raw.get('notes') or [] if isinstance(v,str) and not v.startswith('Redefinições gratuitas')][:10]
    for item in raw.get('resets') or []:
        if not isinstance(item,dict):continue
        count=number(item.get('count'))
        if count is None or not count.is_integer():continue
        row={'title':str(item.get('title') or 'Reset')[:80],'count':int(count),'kind':str(item.get('kind') or 'unknown')[:30],'usable':item.get('usable') is True}
        total=number(item.get('total'))
        if total is not None and total.is_integer():row['total']=int(total)
        if timestamp(item.get('expires_at')):row['expires_at']=timestamp(item['expires_at'])
        out['resets'].append(row)
    if isinstance(raw.get('product_shares_as_of'),str):out['product_shares_as_of']=raw['product_shares_as_of']
    return out


def resolve_resets(details, browser=None, *, fetched_at=None, now=None, stale=False):
    """Keep historical stock out of current totals. Time limits are heuristics.

    A poll without reset fields is unknown, never proof of zero. Browser
    observations retain their own clock; a new usage poll cannot renew them.
    """
    from datetime import datetime, timezone
    clock=now or datetime.now(timezone.utc)
    def date(value):
        try:
            parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
            return parsed if parsed.tzinfo else None
        except (AttributeError,TypeError,ValueError):return None
    def fresh(value,seconds):
        stamp=date(value)
        return stamp is not None and 0 <= (clock-stamp).total_seconds() < seconds
    details=details if isinstance(details,dict) else {}
    rows=details.get('resets') or []
    status=details.get('resets_status') or ('reported' if rows else 'unknown')
    browser=browser if isinstance(browser,dict) else {}
    observed=browser.get('resets') or []
    stamp=browser.get('reset_observed_at')  # wallet timestamps cannot freshen reset stock
    history=[{**row,'observed_at':stamp,'source':'browser'} for row in observed]
    source='automatic';current=[]
    if not stale and fresh(fetched_at,900) and status in ('reported','none'):
        current=list(rows)
        if status=='none':
            current=[{'title':'Resets','kind':'offers','count':0,'usable':False}]
    elif (not stale and fresh(stamp,86400) and not browser.get('unavailable')
          and browser.get('verification_status')!='unavailable'
          and observed and all(date(r.get('expires_at')) and date(r['expires_at'])>clock for r in observed)
          and (date(fetched_at) is None or date(stamp)>date(fetched_at))):
        current=list(observed);status='reported';source='browser'
    else:status='unknown'
    valid=[]
    for row in current:
        expiry=date(row.get('expires_at'))
        if expiry is not None and expiry<=clock:
            history.append({**row,'observed_at':stamp if source=='browser' else fetched_at,'source':source,'expired':True})
        else:valid.append(dict(row))
    if current and not valid:status='expired'
    if source=='automatic' and not current and rows:
        history.extend({**r,'observed_at':fetched_at,'source':'automatic'} for r in rows)
    return {'current':valid,'history':history,'status':status,'source':source,
            'observed_at':stamp if source=='browser' else fetched_at}


def reset_summary(details):
    rows=details.get('resets') if isinstance(details,dict) else None
    if not rows:return '—'
    kinds={item.get('kind') for item in rows if item.get('count',0)>0}
    usable=sum(item['count'] for item in rows if item.get('usable') is True)
    total=sum(item['count'] for item in rows)
    if len(kinds)>1:
        labels={'full':'C','five_hour':'H','account':'R'}
        return '·'.join(str(sum(item['count'] for item in rows if item.get('kind')==kind and item.get('usable') is True))+labels.get(kind,'?') for kind in sorted(kinds))
    return f'{usable}/{total}' if usable!=total else str(usable)
