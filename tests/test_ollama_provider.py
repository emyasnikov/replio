import unittest
from unittest.mock import patch

from replio.providers.ollama import OllamaProvider


def _sse(chunks):
    for c in chunks:
        if 'type' in c:
            yield c
        else:
            yield {'choices': [c]}


class TestOllamaStreaming(unittest.TestCase):

    def setUp(self):
        self.provider = OllamaProvider(base_url='https://test.api.com', model='test-model')

    def _chat(self, chunks, tools=None):
        with patch('replio.providers.ollama.stream_sse', return_value=_sse(chunks)):
            return list(self.provider.chat(
                [{'role': 'user', 'content': 'hi'}], tools=tools
            ))

    def test_accumulates_fragmented_tool_call(self):
        events = self._chat([
            {'delta': {'tool_calls': [{'index': 0, 'id': 'call_1', 'function': {'name': 'web_search'}}]}},
            {'delta': {'tool_calls': [{'index': 0, 'function': {'arguments': '{"query":'}}]}},
            {'delta': {'tool_calls': [{'index': 0, 'function': {'arguments': ' "python"}'}}]}},
            {'delta': {}, 'finish_reason': 'tool_calls'},
        ])
        tool_events = [e for e in events if e['type'] == 'tool_calls']
        self.assertEqual(len(tool_events), 1)
        tc = tool_events[0]['tool_calls'][0]
        self.assertEqual(tc['id'], 'call_1')
        self.assertEqual(tc['function']['name'], 'web_search')
        self.assertEqual(tc['function']['arguments'], '{"query": "python"}')

    def test_done_when_no_tool_calls(self):
        events = self._chat([
            {'delta': {'content': 'Hello'}},
            {'delta': {}, 'finish_reason': 'stop'},
        ])
        self.assertEqual(events, [
            {'type': 'token', 'content': 'Hello'},
            {'type': 'done', 'reason': 'stop'},
        ])

    def test_thinking_event(self):
        events = self._chat([
            {'delta': {'reasoning_content': 'think...'}},
            {'delta': {'content': 'Answer'}},
            {'delta': {}, 'finish_reason': 'stop'},
        ])
        self.assertEqual(events[0], {'type': 'thinking', 'content': 'think...'})

    def test_tools_passed_to_stream_payload(self):
        schema = [{'type': 'function', 'function': {'name': 'web_search'}}]
        with patch('replio.providers.ollama.stream_sse') as mock_sse:
            mock_sse.return_value = _sse([{'delta': {}, 'finish_reason': 'stop'}])
            list(self.provider.chat(
                [{'role': 'user', 'content': 'hi'}], tools=schema
            ))
        payload = mock_sse.call_args[0][2]
        self.assertEqual(payload['tools'], schema)

    def test_max_tokens_omitted_when_zero(self):
        with patch('replio.providers.ollama.stream_sse') as mock_sse:
            mock_sse.return_value = _sse([{'delta': {}, 'finish_reason': 'stop'}])
            list(self.provider.chat([{'role': 'user', 'content': 'hi'}]))
        payload = mock_sse.call_args[0][2]
        self.assertNotIn('max_tokens', payload)

    def test_max_tokens_included_when_set(self):
        self.provider.max_tokens = 4096
        with patch('replio.providers.ollama.stream_sse') as mock_sse:
            mock_sse.return_value = _sse([{'delta': {}, 'finish_reason': 'stop'}])
            list(self.provider.chat([{'role': 'user', 'content': 'hi'}]))
        payload = mock_sse.call_args[0][2]
        self.assertEqual(payload['max_tokens'], 4096)

    def test_error_passthrough(self):
        events = self._chat([
            {'type': 'error', 'code': 500, 'message': 'boom'},
        ])
        self.assertEqual(events, [{'type': 'error', 'code': 500, 'message': 'boom'}])


if __name__ == '__main__':
    unittest.main()
