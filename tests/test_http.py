import unittest
from unittest.mock import patch

from replio.utils.http import stream_sse


class _FakeResp:
    def __init__(self, chunks):
        self.chunks = list(chunks)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, n):
        if not self.chunks:
            return b''
        return self.chunks.pop(0)


class TestStreamSse(unittest.TestCase):

    def _stream(self, chunks):
        resp = _FakeResp(chunks)
        with patch('urllib.request.urlopen', return_value=resp):
            return list(stream_sse('https://test.api.com/chat', {}, {'m': 1}))

    def test_parses_data_lines_and_done_marker(self):
        sse = (
            'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":" world"}}]}\n\n'
            'data: [DONE]\n'
        )
        events = self._stream([sse.encode('utf-8')])
        self.assertEqual(events, [
            {'choices': [{'delta': {'content': 'Hello'}}]},
            {'choices': [{'delta': {'content': ' world'}}]},
            {'type': 'done'},
        ])

    def test_survives_multibyte_char_split_across_chunks(self):
        sse = 'data: {"choices":[{"delta":{"content":"héllo wörld"}}]}\n\ndata: [DONE]\n'
        data = sse.encode('utf-8')
        first_byte = data.index(b'\xc3')
        chunks = [data[:first_byte + 1], data[first_byte + 1:]]
        events = self._stream(chunks)
        self.assertEqual(events, [
            {'choices': [{'delta': {'content': 'héllo wörld'}}]},
            {'type': 'done'},
        ])

    def test_error_event_on_http_error(self):
        with patch('urllib.request.urlopen',
                   side_effect=__import__('urllib.error').error.HTTPError(
                       'url', 500, 'boom', {}, None)):
            events = list(stream_sse('https://test.api.com/chat', {}, {'m': 1}))
        self.assertEqual(events[0]['type'], 'error')
        self.assertEqual(events[0]['code'], 500)


if __name__ == '__main__':
    unittest.main()
