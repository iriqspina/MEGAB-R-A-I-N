#!/usr/bin/env python3
"""Leitura conservadora de cotas; não despacha nem compara custo entre vendors."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path

CENTRAL = Path(__file__).resolve().parent.parent
FONTE = CENTRAL / 'dados' / 'orcamento_ia.json'
MAX_AGE_SECONDS = 300  # HEURISTICA operacional, não garantia do fornecedor
PROVIDERS = ('claude', 'codex', 'codex_gpt2', 'zai', 'spark')
KNOWN_DURATIONS = {'session': 300, 'week': 10080, 'CREDIT_LIMIT:3x5': 300, 'CREDIT_LIMIT:6x1': 10080}
BAD = {'error', 'auth_required', 'rate_limited', 'unavailable', 'unknown', 'stale', 'nao_medido'}


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def age_seconds(value, now):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            return None
        age = (now - parsed).total_seconds()
        return age if age >= 0 else None
    except (ValueError, TypeError, AttributeError):
        return None


def analisar(dados, agora=None, max_age_seconds=MAX_AGE_SECONDS):
    agora = agora or datetime.now(timezone.utc)
    if not isinstance(dados, dict):
        raise ValueError('snapshot não é objeto')
    accounts = []
    for provider in PROVIDERS:
        entry = dados.get(provider, {})
        if not isinstance(entry, dict):
            entry = {}
        pacing = entry.get('pacing', {})
        if not isinstance(pacing, dict):
            pacing = {}
        age = age_seconds(entry.get('updated_at'), agora)
        fresh = age is not None and age <= max_age_seconds
        windows = []
        reasons = []
        restrictions = []
        if not fresh:
            reasons.append('amostra ausente, antiga ou sem horário confiável')
        status = str(pacing.get('status', 'unknown')).lower()
        if status in BAD:
            reasons.append('estado do provedor: ' + status)
        window_map = pacing.get('windows', {})
        if not isinstance(window_map, dict):
            window_map = {}
            reasons.append('mapa de janelas malformado')
        for ident, window in window_map.items():
            if not isinstance(ident, str):
                reasons.append('identificador de janela inválido')
                continue
            if not isinstance(window, dict):
                reasons.append('janela malformada: ' + ident)
                continue
            # Bucket de reserva não é o saldo geral de Codex/Sol/Astra.
            applicable = not ident.startswith('base_model_inference:')
            use = window.get('used_percent')
            reset = window.get('hours_to_reset')
            elapsed = window.get('elapsed_fraction')
            valid = number(use) and 0 <= use <= 100 and number(reset) and reset > 0
            duration = window.get('duration_minutes')
            basis = 'fonte explícita'
            if not number(duration) or duration <= 0:
                duration = KNOWN_DURATIONS.get(ident)
                basis = 'identificador documentado' if duration else 'não medido'
            estimate = None
            if duration is None and number(reset) and number(elapsed) and 0 <= elapsed < 1:
                estimate = round(reset * 60 / (1 - elapsed), 2)
            ratio = use / (100 * elapsed) if valid and number(elapsed) and 0 < elapsed <= 1 else None
            wstatus = str(window.get('status', 'unknown')).lower()
            if applicable and (not valid or wstatus in BAD):
                reasons.append('janela inválida/indisponível: ' + ident)
            if applicable and valid and use >= 95:
                restrictions.append('janela sem margem operacional: ' + ident)
            if applicable and wstatus in {'esgotado', 'bloqueado', 'blocked'}:
                restrictions.append('restrição do fornecedor: ' + ident + ': ' + wstatus)
            windows.append({'id': ident, 'applicable': applicable, 'used_percent': use if number(use) else None,
                            'hours_to_reset': reset if number(reset) else None, 'valid': valid,
                            'duration_minutes': duration, 'duration_basis': basis,
                            'duration_estimate_minutes': estimate, 'pace_ratio': ratio,
                            'status': wstatus})
        relevant = [w for w in windows if w['applicable']]
        if not relevant:
            reasons.append('sem janela aplicável')
        if provider == 'spark':
            restrictions.append('Spark reservado a worker leve, sem revisão/aceite')
        if status in {'esgotado', 'bloqueado', 'blocked'}:
            restrictions.append('restrição do provedor: ' + status)
        worst = max((w['used_percent'] for w in relevant if w['valid']), default=None)
        constrained = status == 'desacelerar' or any(w['status'] == 'desacelerar' for w in relevant) or (worst is not None and worst >= 70)
        accounts.append({'provider': provider, 'updated_at': entry.get('updated_at'), 'age_seconds': age,
                         'fresh': fresh, 'windows': windows, 'limiting_used_percent': worst,
                         'quota_candidate': not reasons and not restrictions and not constrained,
                         'measurement_status': 'NAO_MEDIDO' if reasons else 'válido',
                         'verdict': 'NAO_MEDIDO' if reasons else ('restrito: ' + '; '.join(restrictions) if restrictions else ('desacelerar' if constrained else 'margem medida')),
                         'reasons': reasons, 'restrictions': restrictions, 'capability': 'não verificada por este leitor'})
    comparisons = []
    for i, left in enumerate(accounts):
        for right in accounts[i+1:]:
            if left['reasons'] or right['reasons'] or left['provider'] == 'spark' or right['provider'] == 'spark':
                continue
            for a in left['windows']:
                for b in right['windows']:
                    if a['applicable'] and b['applicable'] and a['valid'] and b['valid'] and a['duration_minutes'] is not None and a['duration_minutes'] == b['duration_minutes']:
                        comparisons.append({'accounts': [left['provider'],right['provider']],
                                            'duration_minutes': a['duration_minutes'],
                                            'window_ids': [a['id'],b['id']],
                                            'used_gap_percentage_points': round(a['used_percent']-b['used_percent'],4),
                                            'pace_ratios': [a['pace_ratio'], b['pace_ratio']],
                                            'meaning': 'pressão relativa na assinatura; não equivale a tokens, dinheiro ou produtividade'})
    return {'measured_at': agora.isoformat(), 'freshness_seconds_heuristic': max_age_seconds,
            'accounts': accounts, 'comparable_windows': comparisons,
            'dispatch_authorized': False,
            'next': 'Antes de cada despacho, atualizar cotas por conta e verificar capacidade; escolher trabalho útil pelo limite mais restritivo, dependências e custo observado. Não gastar só para equalizar percentuais.'}


def ler(fonte=FONTE, agora=None):
    try:
        return analisar(json.loads(Path(fonte).read_text(encoding='utf-8-sig')), agora)
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        return {'accounts': [], 'comparable_windows': [], 'dispatch_authorized': False,
                'error': 'NAO_MEDIDO: ' + type(exc).__name__, 'next': 'Atualizar a medição; nunca tratar falha como saldo zero.'}


def formatar(data):
    lines = ['leitura de uso — snapshot local; idade máxima [HEURISTICA]: 300 s']
    for account in data['accounts']:
        lines.append(f"  {account['provider']}: {account['verdict']} · limite {account['limiting_used_percent']}% · idade {account['age_seconds']} s")
        for reason in account['reasons'] + account['restrictions']:
            lines.append('    ' + reason)
    lines.append(data.get('error', data['next']))
    lines.append('Sem rota automática: saldo não prova ferramenta, independência da revisão ou custo equivalente.')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    data = ler()
    print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else formatar(data))
    return 1 if 'error' in data else 0

if __name__ == '__main__':
    raise SystemExit(main())
