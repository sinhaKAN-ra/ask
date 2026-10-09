"""Offline regression tests: python -m unittest discover -s tests -v."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from aolbeam_ask import ask


def reply(text='A grounded answer [1].'):
    return {'choices': [{'message': {'content': text}, 'finish_reason': 'stop'}]}, 0.1


class CLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name) / 'config'
        self.cfg = dict(ask.DEFAULT_CONFIG, api_key='test-model-key', show_metrics=False)
        self.context = contextlib.ExitStack()
        self.addCleanup(self.context.close)
        for key, value in {
            'BASE_DIR': str(self.base), 'CONFIG_PATH': str(self.base / 'config.json'),
            'SESSIONS_DIR': str(self.base / 'sessions'),
            'ACTIVE_JSON': str(self.base / 'sessions' / 'active.json'),
            'ACTIVE_TXT': str(self.base / 'sessions' / 'active.txt'),
        }.items():
            self.context.enter_context(patch.object(ask, key, value))
        self.context.enter_context(patch.dict(os.environ, {}, clear=True))
        self.context.enter_context(patch.object(ask, '_enable_windows_vt'))

    def run_cli(self, args, responses=None, search=None, stdin=''):
        out, err = io.StringIO(), io.StringIO()
        messages = []
        def call(cfg, key, prompt):
            messages.append(copy.deepcopy(prompt))
            result = responses[len(messages)-1] if responses else reply()
            if isinstance(result, Exception):
                raise result
            return result
        with patch.object(sys, 'argv', ['ask'] + args), patch.object(sys, 'stdin', io.StringIO(stdin)), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
             patch.object(ask, 'load_config', return_value=dict(self.cfg)), \
             patch.object(ask, 'call_api', side_effect=call) as model, \
             patch.object(ask, 'web_search', return_value=search or ('[1] Reference text', [('Docs', 'https://example.org/docs')])) as web:
            ask.ensure_dirs()
            try:
                status = ask.main()
            except SystemExit as e:
                status = e.code
        return status, out.getvalue(), err.getvalue(), model, web, messages

    def test_forced_search_uses_one_model_call_and_preserves_sources_in_pipe(self):
        status, out, err, model, web, messages = self.run_cli(['-w', '--no-history', 'release notes'])
        self.assertEqual(status, 0)
        self.assertEqual(model.call_count, 1)
        self.assertEqual(web.call_count, 1)
        self.assertIn('WEB RESULTS', messages[0][-1]['content'])
        self.assertIn('https://example.org/docs', out)
        self.assertNotIn('\x1b', out)
        self.assertNotIn('Sources:', err)
        self.assertFalse(Path(ask.ACTIVE_JSON).exists())

    def test_freshness_searches_before_model(self):
        result = self.run_cli(['--no-history', 'latest Python release'])
        self.assertEqual(result[3].call_count, 1)
        self.assertIn('WEB RESULTS', result[5][0][-1]['content'])

    def test_model_self_assessment_reasks(self):
        result = self.run_cli(['--no-history', 'Who runs this company?'],
                              responses=[reply('Uncertain.\nNEEDS_WEB: yes — check leadership'), reply()])
        self.assertEqual(result[0], 0)
        self.assertEqual(result[3].call_count, 2)
        self.assertNotIn('NEEDS_WEB', result[1])

    def test_stable_question_does_not_search(self):
        result = self.run_cli(['--no-history', 'explain recursion'], responses=[reply('A function calls itself.\nNEEDS_WEB: no')])
        self.assertEqual(result[0], 0)
        result[4].assert_not_called()
        self.assertNotIn('NEEDS_WEB', result[1])

    def test_forced_search_failure_returns_nonzero_without_model_call(self):
        result = self.run_cli(['-w', '--no-history', 'question'], search=('[no results]', []))
        self.assertEqual(result[0], 4)
        self.assertEqual(result[1], '')
        result[3].assert_not_called()

    def test_failed_automatic_search_warns_and_answers(self):
        result = self.run_cli(['--no-history', 'latest release'], search=('[no results]', []), responses=[reply('Unverified answer')])
        self.assertEqual(result[0], 0)
        self.assertIn('unverified', result[2])
        self.assertNotIn('Sources:', result[1])
        self.assertEqual(result[3].call_count, 1)

    def test_failed_grounded_call_does_not_claim_sources(self):
        result = self.run_cli(['--no-history', 'question'], responses=[reply('Old answer\nNEEDS_WEB: yes'), RuntimeError('offline')])
        self.assertEqual(result[0], 0)
        self.assertIn('Old answer', result[1])
        self.assertNotIn('Sources:', result[1])
        self.assertIn('unverified', result[2])

    def test_no_web_overrides_freshness(self):
        result = self.run_cli(['--no-web', '--no-history', 'latest release'])
        result[4].assert_not_called()

    def test_forced_search_overrides_config_disabled(self):
        self.cfg['web_fallback'] = False
        result = self.run_cli(['-w', '--no-history', 'question'])
        self.assertEqual(result[4].call_count, 1)

    def test_no_history_ignores_active_session(self):
        ask.ensure_dirs()
        session = ask.new_session()
        session['messages'] = [{'role': 'user', 'content': 'private old context'}]
        ask.save_session(session)
        before = Path(ask.ACTIVE_JSON).read_bytes()
        result = self.run_cli(['--no-history', '--no-web', 'question'])
        self.assertNotIn('private old context', str(result[5]))
        self.assertEqual(before, Path(ask.ACTIVE_JSON).read_bytes())

    def test_sources_saved_without_escape_codes(self):
        result = self.run_cli(['-w', 'question'])
        stored = json.loads(Path(ask.ACTIVE_JSON).read_text())['messages'][-1]['content']
        self.assertIn('https://example.org/docs', stored)
        self.assertNotIn('\x1b', stored)

    def test_zero_history_turns_also_applies_to_grounded_prompt(self):
        ask.ensure_dirs()
        session = ask.new_session()
        session['messages'] = [{'role': 'user', 'content': 'old context'}]
        ask.save_session(session)
        self.cfg['history_turns'] = 0
        result = self.run_cli(['-w', 'new question'])
        self.assertNotIn('old context', str(result[5]))

    def test_flags_work_after_question_and_reject_conflicts(self):
        result = self.run_cli(['question', '--no-history', '--no-web', '--quiet'])
        self.assertEqual(result[0], 0)
        result = self.run_cli(['-w', '--no-web', 'question'])
        self.assertEqual(result[0], 2)
        result[3].assert_not_called()
        result = self.run_cli(['--webb', 'question'])
        self.assertEqual(result[0], 2)
        result[3].assert_not_called()

    def test_pipe_without_question_uses_context(self):
        result = self.run_cli(['--no-history', '--no-web'], stdin='Example error log')
        self.assertEqual(result[0], 0)
        self.assertIn('Example error log', result[5][0][-1]['content'])

    def test_empty_pipe_does_not_call_provider(self):
        result = self.run_cli(['--no-history'])
        self.assertNotEqual(result[0], 0)
        result[3].assert_not_called()

    def test_doctor_offline_and_live_checks(self):
        result = self.run_cli(['--doctor'])
        self.assertEqual(result[0], 0)
        result[3].assert_not_called()
        result[4].assert_not_called()
        self.assertNotIn('test-model-key', result[1])
        result = self.run_cli(['--doctor', '--check-web'])
        self.assertEqual(result[4].call_count, 1)
        result[3].assert_not_called()
        result = self.run_cli(['--doctor', '--check-web'], search=('[no results]', []))
        self.assertEqual(result[0], 4)

    def test_doctor_identifies_missing_key(self):
        self.cfg['search_provider'] = 'brave'
        result = self.run_cli(['--doctor'])
        self.assertEqual(result[0], 2)
        self.assertIn('BRAVE_API_KEY', result[1])

    def test_redacted_config(self):
        self.cfg.update(search_api_key='private-search-key')
        result = self.run_cli(['--config'])
        self.assertNotIn('private-search-key', result[1])
        self.assertNotIn('test-model-key', result[1])
        self.assertIn('GROQ_API_KEY', result[1])
        self.assertIn('1024', result[1])

    def test_setup_persists_provider_preserves_model_and_clears_old_search_key(self):
        self.cfg.update(search_api_key='old-provider-key', custom_setting='keep')
        result = self.run_cli(['--setup-search', 'tavily'])
        self.assertEqual(result[0], 0)
        cfg = json.loads(Path(ask.CONFIG_PATH).read_text())
        self.assertEqual(cfg['search_provider'], 'tavily')
        self.assertEqual(cfg['search_api_key_env'], 'TAVILY_API_KEY')
        self.assertEqual(cfg['search_api_key'], '')
        self.assertEqual(cfg['api_key'], 'test-model-key')
        self.assertEqual(cfg['custom_setting'], 'keep')
        if os.name != 'nt':
            self.assertEqual(Path(ask.CONFIG_PATH).stat().st_mode & 0o777, 0o600)

    def test_provider_override_does_not_reuse_other_provider_key(self):
        self.cfg.update(search_provider='tavily', search_api_key='tavily-secret')
        result = self.run_cli(['--search-provider', 'brave', '-w', '--no-history', 'question'])
        cfg = result[4].call_args[0][1]
        self.assertEqual(cfg['search_api_key'], '')
        self.assertEqual(cfg['search_api_key_env'], 'BRAVE_API_KEY')

    def test_provider_env_keys_and_legacy_key(self):
        for provider in ['brave', 'tavily', 'serper']:
            env = ask.SEARCH_PROVIDERS[provider][0]
            with patch.dict(os.environ, {env: 'test-secret'}):
                self.assertEqual(ask.resolve_search_key(dict(self.cfg, search_provider=provider)), 'test-secret')
        with patch.dict(os.environ, {'SEARCH_API_KEY': 'legacy-secret'}):
            self.assertEqual(ask.resolve_search_key(self.cfg), 'legacy-secret')

    def test_missing_search_key_does_not_switch_provider(self):
        with patch.object(ask, '_search_duckduckgo') as ddg:
            result, sources = ask.web_search('question', dict(self.cfg, search_provider='brave'))
        ddg.assert_not_called()
        self.assertEqual(sources, [])
        self.assertIn('BRAVE_API_KEY', result)

    def test_tavily_auth_payload_and_brave_count(self):
        with patch.object(ask, '_http_json', return_value={'results': []}) as http:
            ask._search_tavily('question', 5, 'test-key')
        self.assertEqual(http.call_args.kwargs['headers']['Authorization'], 'Bearer test-key')
        body = json.loads(http.call_args.kwargs['data'])
        self.assertEqual(body['search_depth'], 'basic')
        self.assertFalse(body['include_answer'])
        with patch.object(ask, '_http_json', return_value={}) as http:
            ask._search_brave('hello & world', 3, 'test-key')
        self.assertIn('count=3', http.call_args.args[0])
        self.assertIn('q=hello+%26+world', http.call_args.args[0])
        self.assertEqual(http.call_args.kwargs['headers']['X-Subscription-Token'], 'test-key')

    def test_search_http_error_is_actionable_without_exposing_body(self):
        error = urllib.error.HTTPError('https://example.org', 401, 'test-key', {}, io.BytesIO(b'secret'))
        with patch.object(ask, '_search_brave', side_effect=error):
            text, sources = ask.web_search('question', dict(self.cfg, search_provider='brave', search_api_key='test-key'))
        self.assertIn('HTTP 401', text)
        self.assertNotIn('test-key', text)
        self.assertNotIn('secret', text)

    def test_invalid_responses_return_useful_error(self):
        for body in [{}, None, {'choices': []}, {'choices': [{'message': {'content': None}}]}]:
            with self.subTest(body=body):
                with self.assertRaises(RuntimeError):
                    ask.response_text(body)
        result = self.run_cli(['--no-history', '--no-web', 'question'], responses=[({}, 0.1)])
        self.assertEqual(result[0], 3)

    def test_invalid_config_fails_without_overwriting(self):
        self.base.mkdir()
        path = Path(ask.CONFIG_PATH)
        path.write_text('{invalid')
        with self.assertRaises(RuntimeError):
            ask.load_config()
        self.assertEqual(path.read_text(), '{invalid')

    def test_readonly_config_load_creates_nothing(self):
        self.assertEqual(ask.load_config(create=False), ask.DEFAULT_CONFIG)
        self.assertFalse(self.base.exists())

    def test_file_slice_reaches_model(self):
        path = Path(self.tmp.name) / 'example.py'
        path.write_text('first\nsecond\nthird\n', encoding='utf-8')
        result = self.run_cli(['--no-history', '--no-web', '-f', str(path) + ':2', 'explain'])
        content = result[5][0][-1]['content']
        self.assertIn('second', content)
        self.assertNotIn('first', content)
        self.assertNotIn('third', content)

    def test_plain_metrics_have_no_ansi_and_no_color_respected(self):
        self.cfg['show_metrics'] = True
        result = self.run_cli(['--no-history', '--no-web', '--format', 'plain', 'question'])
        self.assertNotIn('\x1b', result[1] + result[2])
        with patch.dict(os.environ, {'NO_COLOR': ''}):
            self.assertEqual(ask._resolve_format(self.cfg, 'rich'), 'plain')

    def test_api_transport_payload_and_timeout(self):
        response = io.BytesIO(json.dumps(reply()[0]).encode())
        with patch('urllib.request.urlopen', return_value=response) as transport:
            body, _ = ask.call_api(self.cfg, 'test-key', [{'role': 'user', 'content': 'hello'}])
        request = transport.call_args.args[0]
        self.assertTrue(request.full_url.endswith('/chat/completions'))
        self.assertEqual(json.loads(request.data)['messages'][0]['content'], 'hello')
        self.assertEqual(request.get_header('Authorization'), 'Bearer test-key')
        self.assertEqual(ask.response_text(body), 'A grounded answer [1].')
        with patch('urllib.request.urlopen', side_effect=TimeoutError()):
            with self.assertRaisesRegex(RuntimeError, 'timeout'):
                ask.call_api(self.cfg, 'test-key', [])

    def test_help_does_not_create_configuration(self):
        with patch.object(sys, 'argv', ['ask', '--help']), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as result:
                ask.main()
        self.assertEqual(result.exception.code, 0)
        self.assertFalse(self.base.exists())


if __name__ == '__main__':
    unittest.main()
