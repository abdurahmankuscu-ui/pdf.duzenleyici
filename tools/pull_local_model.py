"""Download the selected public model through the local Ollama service."""
import json
from pathlib import Path
import sys
import time
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import integrations

integrations.ensure_ollama()
request = urllib.request.Request(integrations.OLLAMA_URL + '/api/pull',
    data=json.dumps({'model': integrations.DEFAULT_MODEL, 'stream': True}).encode(),
    headers={'Content-Type': 'application/json'})
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
last_time = 0
last_status = ''
with opener.open(request, timeout=600) as response:
    for line in response:
        progress = json.loads(line)
        if 'error' in progress:
            raise RuntimeError(progress['error'])
        status = progress.get('status', '')
        if status != last_status or time.monotonic() - last_time > 15:
            total = progress.get('total', 0)
            percentage = f" {100*progress.get('completed', 0)/total:.0f}%" if total else ''
            print(status + percentage, flush=True)
            last_time = time.monotonic()
            last_status = status
print('Model ready:', integrations.DEFAULT_MODEL, flush=True)
