"""Human evidence stays separate from live, automatically polled quotas."""
import json
from datetime import timezone,timedelta
from . import paths
from .formatting import parse_iso
from quota_details_data import sanitize_details


def evidence_date(value):
    parsed=parse_iso(value)
    return parsed.astimezone(timezone(timedelta(hours=-3))).strftime('%d/%m/%Y %H:%M:%S BRT') if parsed and parsed.tzinfo else 'data não informada com fuso'


def observed_resets(row_id):
    try:
        data=json.loads((paths.DATA_DIR/'account_balance_observed.json').read_text(encoding='utf-8'))
        item=data['accounts'].get(row_id) or {}
        return sanitize_details({'resets':item.get('resets')})['resets'],item.get('reset_observed_at') or item.get('observed_at') or data.get('observed_at')
    except (OSError,ValueError,TypeError,KeyError,AttributeError):return [],None


def observed_info(row_id):
    if row_id != 'claude':
        return None
    try:
        data = json.loads((paths.DATA_DIR / 'claude_observed.json').read_text(encoding='utf-8'))
        if data.get('schema_version') != 1 or data.get('source_kind') != 'user_screenshot':
            return None
        return data
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def observed_sections(data):
    """Small selectable strings, no invented capture time or live status."""
    if not data:
        return []
    used = data.get('observed_usage', {})
    cloud = data.get('cloud_credit', {})
    credits = data.get('usage_credit', {})
    offer = data.get('reset_offer', {})
    def remaining(value):
        return f'{100-value:g}%' if isinstance(value,(int,float)) and not isinstance(value,bool) and 0<=value<=100 else 'não informado'
    shares=[]
    for item in data.get('product_shares') or []:
        if isinstance(item,dict):
            percent=item.get('percent')
            shares.append(f"{item.get('name','Produto')} {percent}%" if isinstance(percent,(int,float)) and not isinstance(percent,bool) and 0<=percent<=100 else f"{item.get('name','Produto')}: percentual não informado")
    return [
        ('📷 Prints fornecidos · não atualizados automaticamente',
         'Mesma ocasião declarada por <USUARIO>; horário de captura não informado.\n'
         f"Plano: {data.get('plan', 'não informado')} · recebido: {data.get('received_at', 'não informado')}\n"
         f"Sessão: {used.get('session_used_percent')}% usado → {remaining(used.get('session_used_percent'))} restante · semana: {used.get('weekly_used_percent')}% usado → {remaining(used.get('weekly_used_percent'))} restante.\n"
         'Relatório anterior divergia 1 ponto em cada janela; causa não determinada.'),
        ('◷ Cota específica do Fable · print',
         f"{used.get('fable_used_percent')}% usado → {remaining(used.get('fable_used_percent'))} restante na janela específica.\n"
         f"Reinício: {used.get('weekly_reset_text')}. Sessão: {used.get('session_reset_text')}.\n"
         'Fable também depende das cotas gerais; este saldo não se soma ao semanal.'),
        ('◉ Uso da semana por produto · print',
         ' · '.join(shares) + '\n' + data.get('product_share_note', '')),
        ('$ Crédito para sessões na nuvem · print',
         f"US$ {cloud.get('remaining')}/{cloud.get('total')} restantes · expira {cloud.get('expires_text')}.\n"
         'Escopo mostrado: sessões na nuvem. Não é percentual da assinatura; não assumir validade em qualquer cliente.'),
        ('$ Uso extra e gastos · print',
         f"Uso extra {'ligado' if credits.get('enabled') else 'desligado'} · saldo R$ {credits.get('balance')} · gasto do mês R$ {credits.get('monthly_spent')}.\n"
         f"Teto configurado R$ {credits.get('monthly_cap')} · recarga automática {'ligada' if credits.get('auto_reload') else 'desligada'}.\n"
         'Teto é limite de gasto, não saldo. Nenhuma configuração financeira foi alterada.'),
        ('↻ Redefinição gratuita · print',
         f"Redefinição completa disponível no print · expira {offer.get('expires_text')}.\n"
         'Redefinição de 5 horas: nada disponível no print. A oferta não foi acionada.'),
    ]


def balance_evidence_sections(row_id):
    try:
        data=json.loads((paths.DATA_DIR/'account_balance_observed.json').read_text(encoding='utf-8'))
        item=data['accounts'].get(row_id)
        if not item:return []
        try:schedule=json.loads((paths.DATA_DIR/'balance_refresh.json').read_text(encoding='utf-8')) if (paths.DATA_DIR/'balance_refresh.json').exists() else {}
        except (OSError,ValueError):schedule={}
        cadence='Consulta agendada diária; depende de navegador autenticado e computador ligado.' if schedule.get('status')=='ACTIVE' else 'Consulta automática deste saldo indisponível.'
        stamp=item.get('observed_at') or data['observed_at']
        balance=item.get('balance')
        value=f"{item.get('currency','')} {balance}" if isinstance(balance,(int,float)) and not isinstance(balance,bool) else 'não informado'
        parts=[('$ Saldo · última verificação no navegador',
                 f"{value} · {item.get('scope','escopo não informado')}\n"
                 f"Consulta: {evidence_date(stamp)} · fonte: {item.get('source','não informada')}\n"+cadence)]
        if row_id=='claude':
            parts.append(('$ Controle de gasto · navegador',
                 f"Gasto mensal BRL {item.get('monthly_spent','—')} · teto BRL {item.get('monthly_cap','—')} (não é saldo).\n"
                 f"Uso extra {'ligado' if item.get('extra_enabled') else 'desligado'} · recarga automática {'ligada' if item.get('auto_reload') else 'desligada'}."))
        elif row_id=='zai':
            parts.append(('$ Composição da carteira · navegador',
                 f"Dinheiro USD {item.get('cash','—')} · bônus USD {item.get('bonus','—')}.\n"
                 f"Recarga automática {'ligada' if item.get('auto_reload') else 'desligada'} · separado da assinatura Coding Plan."))
        if item.get('verification_status')=='unavailable':parts.append(('⚠ Verificação mais recente indisponível','Saldo e data anteriores preservados; nova consulta pendente.'))
        resets,reset_stamp=observed_resets(row_id)
        for offer in resets:
            parts.append(('♻ Resets · última verificação no navegador',f"{offer['title']}: {offer['count']} restante(s) · {'disponível' if offer.get('usable') else 'indisponível'}.\n"
                 f"Consulta: {evidence_date(reset_stamp)} · validade: {evidence_date(offer.get('expires_at'))}.\n"+cadence))
        if item.get('five_hour_offer')=='none':parts.append(('♻ Reset exclusivo de 5 horas','Sem oferta na última consulta ao navegador. Renovação normal das cotas é outra informação.'))
        return parts
    except (OSError,ValueError,TypeError,KeyError,AttributeError):return []
