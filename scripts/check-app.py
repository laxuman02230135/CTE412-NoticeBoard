"""Check endpoint behaviour against the built image; run inside its Python runtime."""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

def request(path):
    try:
        response = urllib.request.urlopen('http://127.0.0.1:8080' + path, timeout=2)
    except urllib.error.HTTPError as error:
        response = error
    return response.status, json.loads(response.read())

for version, flag in [('1.0.0', 'false'), ('1.1.0', 'false'), ('1.1.0', 'true'), ('1.2.0-broken', 'false')]:
    environment = dict(os.environ, APP_VERSION=version, FEATURE_PINNED=flag)
    process = subprocess.Popen([sys.executable, '/app/app.py'], env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for attempt in range(30):
            try:
                status, health = request('/healthz')
                break
            except OSError:
                time.sleep(0.05)
        else:
            raise AssertionError('Application failed to start')
        assert status == 503 and health['uptimeSeconds'] < 5
        time.sleep(5.1)
        status, health = request('/healthz')
        assert status == (503 if version.endswith('broken') else 200)
        status, identity = request('/version')
        assert status == 200 and identity['student'] == '02230135' and identity['version'] == version
        status, notices = request('/notices')
        assert status == 200 and len(notices['notices']) >= 3
        if version == '1.0.0':
            assert all('category' not in x for x in notices['notices'])
        else:
            assert all('category' in x and isinstance(x['pinned'], bool) for x in notices['notices'])
        assert notices['pinnedFirst'] == (version != '1.0.0' and flag == 'true')
        assert notices['notices'][0]['id'] == (2 if flag == 'true' else 1)
        print(json.dumps({'student':'02230135','version':version,'flag':flag,'healthAfterWarmup':health,'notices':notices,'result':'PASS'}), flush=True)
    finally:
        process.terminate()
        process.wait(timeout=5)
assert os.getuid() == 10001
print('Student 02230135: all endpoint checks passed as non-root UID 10001.')
