"""No network/models: validate native response and exclusive-output contracts."""
import datetime as dt
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('report_producer', ROOT / 'bin/mb-produzir-relatorio-glm.py')
producer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(producer)


class ProducerTests(unittest.TestCase):
    def test_explicit_zero_without_schedule_keeps_unknown_timestamp(self):
        now=dt.datetime.now(dt.timezone.utc)
        quota={'provider':'zai','status':'ok','source':'official-quota','fetched_at':now.isoformat(),
               'windows':[{'duration_minutes':300,'used_percent':0,'resets_at':None}]}
        self.assertIs(producer.validate_quota(quota),quota)
        self.assertIsNone(quota['windows'][0]['resets_at'])
        quota['windows'][0]['used_percent']=1
        with self.assertRaises(producer.ProductionError):producer.validate_quota(quota)
        quota['windows'][0]['used_percent']=None
        with self.assertRaises(producer.ProductionError):producer.validate_quota(quota)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ev = self.root / 'evidence'
        self.ev.mkdir()
        self.prompt = self.ev / 'brief.txt'
        self.prompt.write_text('Fato observado: 1 tarefa. Exemplo: comparação antes e depois.', encoding='utf-8')
        self.global_config = self.root / 'existing-global.json'
        self.global_config.write_text('{"existing":"preserve"}', encoding='utf-8')
        self.before = self.global_config.read_bytes()
        self.html = '<style>.report{display:block}</style><main class="report"><h1>Resultado</h1><p>Uma tarefa verificada.</p></main>'
        now = dt.datetime.now(dt.timezone.utc)
        self.quota = {'provider': 'zai', 'status': 'ok', 'source': 'official-quota', 'fetched_at': now.isoformat(),
                      'windows': [{'id': 'session', 'duration_minutes': 300, 'used_percent': 20,
                                   'resets_at': (now + dt.timedelta(hours=1)).isoformat()}]}
        self.rows = [{'model': {'modelId': 'GLM-5.3'}, 'body_model': 'GLM-5.3', 'response_model': 'GLM-5.3',
                      'body_effort': 'max', 'provider_effort': 'max', 'finishReason': 'stop',
                      'tool_calls': [], 'tool_names_requested': []}]
        def configure(run, env, secrets):
            secrets.append('test-secret-never-on-disk')
            env['ZAI_API_KEY'] = secrets[0]
            env['ZCODE_MODEL_RETRY_MAX_RETRIES'] = '0'
            config = {'permission': {'mode': 'plan', 'disallowedTools': ['Bash', 'Read']},
                      'features': {'skill': False, 'memory': False}, 'provider': {'apiKeyRequired': True}}
            (run / 'zcode.json').write_text(json.dumps(config), encoding='utf-8')
            return {'runtime_sha256': 'certified-fixture'}
        def redact(text, secrets):
            for secret in secrets:
                text = text.replace(secret, '[REDACTED]')
            return text
        self.clients = SimpleNamespace(ZCODE=self.root / 'official-zcode.cjs', ZCODE_CONFIG=self.global_config,
                    DENY_TOOLS=('Bash', 'Read'), _glm_config=configure, _redact=redact,
                    _rate_limit_failure=lambda out, err: 'HTTP 429' in err,
                    _glm_evidence=Mock(side_effect=lambda run, sid: self.rows))
        self.providers = SimpleNamespace(fetch_provider=Mock(side_effect=lambda vendor: self.quota), _sanitized=lambda value: value)
        self.runner = Mock(side_effect=self.run_fake)

    def run_fake(self, argv, **kwargs):
        run = kwargs['cwd']
        config = json.loads((run / 'zcode.json').read_text(encoding='utf-8'))
        self.assertEqual(config['permission']['mode'], 'build')
        self.assertEqual(config['permission']['disallowedTools'], ['Bash', 'Read'])
        self.assertIs(config['features']['skill'], False)
        args = json.loads((run / 'argv.json').read_text(encoding='utf-8'))
        self.assertNotIn('--settings', args)
        self.assertEqual(args[args.index('--mode') + 1], 'build')
        self.assertEqual(kwargs['stdin'], subprocess.DEVNULL)
        self.assertEqual(kwargs['env']['ZCODE_MODEL_RETRY_MAX_RETRIES'], '0')
        self.assertEqual(argv[-1], str(run / 'launch.cjs'))
        self.assertIn('CONTRATO CANÔNICO', args[args.index('--prompt') + 1])
        return SimpleNamespace(returncode=0, stdout=json.dumps({'sessionId': 'native-session', 'response': self.html}, indent=2),
                               stderr='test-secret-never-on-disk')

    def produce(self):
        with patch.object(producer.shutil, 'which', return_value='node-fixture'):
            return producer.produce(self.root, self.prompt, 'evidence/run', 'evidence/generated.html',
                    deps=(self.clients, self.providers, lambda vendor: {}), runner=self.runner)

    def test_pretty_json_success_preserves_global_and_redacts_every_wrapper_log(self):
        result = self.produce()
        self.assertEqual(result['status'], 'completed')
        self.assertTrue(result['effort_verified'])
        self.assertFalse(result['delivery_ready'])
        self.assertEqual(self.global_config.read_bytes(), self.before)
        self.assertEqual((self.ev / 'generated.html').read_text(encoding='utf-8'), self.html)
        self.assertEqual(self.runner.call_count, 1)
        self.providers.fetch_provider.assert_called_once_with('zai')
        for path in (self.ev / 'run').rglob('*'):
            if path.is_file():
                self.assertNotIn(b'test-secret-never-on-disk', path.read_bytes())

    def test_jsonl_fallback_and_fenced_html(self):
        sid, text = producer.parse_result('native banner\n' + json.dumps({'type': 'result', 'session_id': 's-1', 'result': self.html}))
        self.assertEqual(sid, 's-1')
        self.assertEqual(producer.validate_html('```html\n' + text + '\n```'), self.html)
        self.assertEqual(producer.validate_html('<!doctype html><html><body><p>Resultado</p></body></html>'),
                         '<!doctype html><html><body><p>Resultado</p></body></html>')

    def test_missing_effort_and_truncated_or_plain_outputs_are_not_completed(self):
        self.rows[0]['provider_effort'] = None
        result = self.produce()
        self.assertEqual(result['status'], 'failed')
        self.assertFalse((self.ev / 'generated.html').exists())
        self.assertFalse(result['effort_verified'])
        for text in ('Vou planejar o relatório.', '<main><p>Truncado', '<main>ok</main>trailing prose'):
            with self.subTest(text=text), self.assertRaises(producer.ProductionError):
                producer.validate_html(text)

    def test_token_limit_or_tool_request_blocks_html_even_if_well_formed(self):
        for key, value in (('finishReason', 'length'), ('tool_calls', ['Bash'])):
            row = {**self.rows[0], key: value}
            with self.subTest(key=key), self.assertRaises(producer.ProductionError):
                producer.validate_evidence([row])

    def test_existing_run_and_output_are_never_overwritten_or_dispatched(self):
        (self.ev / 'run').mkdir()
        with self.assertRaises(producer.ProductionError):
            self.produce()
        self.runner.assert_not_called()
        self.providers.fetch_provider.assert_not_called()
        (self.ev / 'run').rmdir()
        (self.ev / 'generated.html').write_text('human edit', encoding='utf-8')
        with self.assertRaises(producer.ProductionError):
            self.produce()
        self.assertEqual((self.ev / 'generated.html').read_text(encoding='utf-8'), 'human edit')

    def test_human_delivery_and_traversal_paths_are_rejected_before_dependencies(self):
        for path in ('00_PARA-VOCE/report.html', '../report.html', '.git/report.html'):
            with self.subTest(path=path), self.assertRaises(producer.ProductionError):
                producer.safe_path(self.root, path, technical=True)

    def test_unknown_stale_or_exhausted_quota_prevents_dispatch(self):
        for mutation in ('unknown', 'duration', 'expired', 'exhausted'):
            q = json.loads(json.dumps(self.quota))
            if mutation == 'unknown':
                q['status'] = 'unavailable'
            elif mutation == 'duration':
                q['windows'][0]['duration_minutes'] = None
            elif mutation == 'expired':
                q['windows'][0]['resets_at'] = '2020-01-01T00:00:00Z'
            else:
                q['windows'][0]['used_percent'] = 100
            with self.subTest(mutation=mutation), self.assertRaises(producer.ProductionError):
                producer.validate_quota(q)
        self.quota['status'] = 'rate_limited'
        result = self.produce()
        self.assertEqual(result['status'], 'failed')
        self.runner.assert_not_called()

    def test_rate_limit_is_persisted_without_retry(self):
        self.runner.side_effect = lambda *a, **k: SimpleNamespace(returncode=1, stdout='', stderr='HTTP 429')
        result = self.produce()
        self.assertEqual(result['status'], 'rate_limited')
        self.assertEqual(self.runner.call_count, 1)
        self.assertFalse((self.ev / 'generated.html').exists())

    def test_config_change_withholds_output(self):
        def changed(*args, **kwargs):
            self.global_config.write_text('changed by another actor', encoding='utf-8')
            return SimpleNamespace(returncode=0, stdout=json.dumps({'sessionId': 'native-session', 'response': self.html}), stderr='')
        self.runner.side_effect = changed
        result = self.produce()
        self.assertFalse(result['global_config_unchanged'])
        self.assertEqual(result['status'], 'failed')
        self.assertFalse((self.ev / 'generated.html').exists())

    def test_timeout_is_persisted_and_not_retried(self):
        self.runner.side_effect = subprocess.TimeoutExpired('native-fixture', 420, output=b'partial', stderr=b'test-secret-never-on-disk')
        result = self.produce()
        self.assertEqual(result['status'], 'timeout')
        self.assertEqual(self.runner.call_count, 1)
        self.assertFalse((self.ev / 'generated.html').exists())
        self.assertNotIn('test-secret-never-on-disk', (self.ev / 'run/stderr.log').read_text())


if __name__ == '__main__':
    unittest.main()
