import urllib.request
import urllib.error
import json


def stream_sse(url, headers, payload, timeout=120):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            buffer = ''
            while True:
                chunk = resp.read(4096)
                if not chunk:
                    break
                buffer += chunk.decode('utf-8')
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str == '[DONE]':
                            yield {'type': 'done'}
                            return
                        try:
                            yield json.loads(data_str)
                        except json.JSONDecodeError:
                            pass
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        yield {'type': 'error', 'code': e.code, 'message': body}
    except Exception as e:
        yield {'type': 'error', 'message': str(e)}
