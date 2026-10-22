"""Typed, compact account overview. Expenses and ceilings are never balances."""
from dataclasses import dataclass
from math import isfinite
from .inline_contract import provider_fields, short_date, full_date, _number
from quota_details_data import resolve_resets

@dataclass(frozen=True)
class GlanceEntry:
    id: str
    label: str
    value: str
    tooltip: str
    kind: str = 'balance'
    percent: float | None = None
    color: str | None = None
    manual_date: str = ''

def money(amount, currency=''):
    text=_number(amount,currency)
    return text.replace(',00 créditos',' cr Codex').replace(',00','') if text!='—' else text

def compact_renewal(text):
    return text.replace('↻ ?','↻ —').replace('↻ em ','↻').replace(' min','m').replace(' h','h').replace(' d','d')

def overview(row_id,display,*,number_mode='used',reset_mode='relative',browser=None,name=''):
    """Return (quotas, stock/wallet). Keep the original field tooltip/source."""
    if display is not None:
        display={**display,'windows':[{**window,'used_percent':p if isinstance((p:=window.get('used_percent')),(int,float)) and not isinstance(p,bool) and isfinite(p) and 0<=p<=100 else None} for window in display.get('windows') or []]}
    fields=provider_fields(row_id,display,number_mode=number_mode,reset_mode=reset_mode,browser=browser,name=name)
    quotas=[GlanceEntry(f.id,f.label,compact_renewal(f.text),f.tooltip,'quota',f.percent,f.color) for f in fields if f.kind=='quota']
    details=(display or {}).get('details') or {}
    items=[]
    resolved=resolve_resets(details,browser,fetched_at=(display or {}).get('fetched_at'),stale=(display or {}).get('stale') or (display or {}).get('status')!='ok')
    resets=resolved['current']
    reset_date=resolved['observed_at'] if resolved['source']=='browser' else ''
    for index,reset in enumerate(resets):
        kind=reset.get('kind');label={'account':'♻ Estoque','full':'♻ Completo','five_hour':'♻ 5 h'}.get(kind,'♻ Reset')
        count=reset.get('count');total=reset.get('total')
        value='—' if count is None else f'{count}/{total}' if total is not None else str(count)
        if kind!='account' and count is not None and count>0 and not reset.get('usable'):value+=' retido'
        if reset_date:label+='*'
        tooltip=('Estoque gratuito sujeito à elegibilidade; não significa uso imediato.' if kind=='account' else
                 ('Disponível agora.' if reset.get('usable') else 'Indisponível agora.'))
        if reset.get('expires_at'):tooltip+=' Validade: '+full_date(reset['expires_at'])
        if reset_date:tooltip+=' Navegador, verificado '+full_date(reset_date)
        items.append(GlanceEntry(f'reset:{index}',label,value,tooltip,'reset',manual_date=reset_date))
    if not resets:items.append(GlanceEntry('reset:unknown','♻ Resets','—','Estoque atual não confirmado; histórico não é disponibilidade. Não é zero.','reset'))
    if row_id=='spark':
        items.append(GlanceEntry('balance:spark','Saldo','ver Codex','Saldo/reset pertencem à conta Codex.'))
        return quotas,items
    browser_balance=bool(browser and (browser.get('balance') is not None or browser.get('observed_at')))
    shared_extra=bool(row_id=='claude' and browser_balance and browser.get('scope')=='créditos de uso')
    automatic_extra_known=shared_extra and any(str(item.get('title') or '').lower()=='créditos de uso' and (item.get('status')=='unlimited' or money(item.get('amount'),item.get('currency',''))!='—') for item in details.get('financial') or [])
    for index,item in enumerate(details.get('financial') or []):
        title=str(item.get('title') or 'Saldo');low=title.lower()
        if any(word in low for word in ('gasto','teto','spent','spending','ceiling')):continue
        # Browser's "créditos de uso" is the same extra wallet: dated browser
        # observation fills the unavailable automatic field; it is never freshened.
        if shared_extra and low=='créditos de uso' and not automatic_extra_known:continue
        label='Nuvem' if 'nuvem' in low else 'Extra' if 'extra' in low or low=='créditos de uso' else title
        value='sem limite' if item.get('status')=='unlimited' else money(item.get('amount'),item.get('currency',''))
        if item.get('currency')=='créditos':value=value.replace(' cr Codex',' cr')
        tooltip=title+': '+_number(item.get('amount'),item.get('currency',''))+'. '+str(item.get('note') or '')
        if item.get('total') is not None:tooltip+=' Total: '+_number(item['total'],item.get('currency',''))+'.'
        if item.get('expires_at'):tooltip+=' Validade: '+full_date(item['expires_at'])+'.'
        items.append(GlanceEntry(f'balance:{index}',label,value,tooltip))
    if row_id=='zai':items.append(GlanceEntry('balance:plan','Plano','—','O leitor de cotas não expõe saldo do Coding Plan; separado do saldo da API.'))
    if browser_balance and not automatic_extra_known:
        stamp=browser.get('observed_at') or ''
        scope=browser.get('scope') or 'escopo não informado'
        label='API*' if row_id=='zai' else 'Extra*' if row_id=='claude' and scope=='créditos de uso' else 'Saldo*'
        tooltip=f'{scope}. Navegador: {full_date(stamp)}. Fonte: {browser.get("source") or "não informada"}.'
        if browser.get('unavailable'):tooltip+=' A última tentativa falhou; esta é a leitura anterior.'
        items.append(GlanceEntry('browser:balance',label,money(browser.get('balance'),browser.get('currency','')),tooltip,manual_date=stamp))
        if row_id=='zai' and ('cash' in browser or 'bonus' in browser):
            # Components remain individually named and in the same measured currency.
            value=money(browser.get('cash'),'')+' + '+money(browser.get('bonus'),'')
            currency=browser.get('currency') or 'USD'
            items.append(GlanceEntry('browser:parts','Caixa+bônus',currency+' '+value,
                'Respectivamente dinheiro e bônus; composição da API, não do Coding Plan. '+tooltip,manual_date=stamp))
    if not any(i.kind=='balance' for i in items):items.append(GlanceEntry('balance:unknown','Saldo','—','Saldo não informado; não é zero.'))
    return quotas,items
