from datetime import datetime, timezone, timedelta
import budget_pacing
from widget_app.observed_info import observed_info, observed_sections


def test_pacing_keeps_explicit_duration_and_reset_with_invalid_pacing():
    reset=(datetime.now(timezone.utc)+timedelta(hours=2)).isoformat()
    result=budget_pacing.provider_pacing({'provider':'claude','status':'ok','windows':[
        {'id':'session','label':'Sessão','used_percent':10,'duration_minutes':300,'resets_at':reset},
        {'id':'model','label':'Fable','used_percent':None,'duration_minutes':10080,'resets_at':None},
        {'id':'unknown','used_percent':2,'duration_minutes':None,'resets_at':reset},
    ]})['windows']
    assert result['session']['duration_minutes']==300 and result['session']['resets_at']==reset
    assert result['model']['duration_minutes']==10080 and result['model']['status']=='NAO_MEDIDO'
    assert result['unknown']['duration_minutes'] is None


def test_observed_information_never_claims_to_be_automatically_polled(tmp_path):
    import json
    from pathlib import Path
    source=Path(__file__).resolve().parents[1]/'app/data/claude_observed.json'
    (tmp_path/'claude_observed.json').write_text(source.read_text(encoding='utf-8'),encoding='utf-8')
    data=observed_info('claude')
    assert data['automatic'] is False and data['captured_at'] is None
    sections=observed_sections(data)
    text='\n'.join(title+'\n'+body for title,body in sections)
    assert 'não atualizados automaticamente' in text
    assert 'participação' in text.lower() and 'não é cota' in text
    assert 'Teto é limite de gasto, não saldo' in text
    assert observed_info('codex') is None
