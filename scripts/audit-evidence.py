"""Audit canonical evidence without contacting a cluster or changing any files."""
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import re

root=Path(__file__).resolve().parents[1]
e=root/'evidence'

def read(name):
    return (e/name).read_text(encoding='utf-8-sig')

def records(name):
    rows=[]
    for line in read(name).splitlines():
        if not line.strip(): continue
        timestamp,status,body=line.split(' ',2)
        datetime.fromisoformat(timestamp.replace('Z','+00:00'))
        assert status in ('OK','FAIL')
        payload=json.loads(body) if status=='OK' else None
        if payload: assert payload['student']=='02230135'
        rows.append((timestamp,status,payload,line))
    assert rows
    return rows

results=json.loads(read('t9-results.json'))
assert len(results)==7
full={r[3] for r in records('t9-monitor-full.log')}
for result in results:
    key=result['experiment']
    rows=records(key+'-log.txt')
    failed=sum(r[1]=='FAIL' for r in rows)
    counts=Counter(r[2]['version'] for r in rows if r[2])
    assert len(rows)==result['requests'] and failed==result['failed']
    assert dict(counts)==result['versions']
    old='1.1.0' if key=='t7-switch2' else '1.0.0'
    new='1.0.0' if key=='t7-switch2' else '1.1.0'
    oldtimes=[r[0] for r in rows if r[2] and r[2]['version']==old]
    newtimes=[r[0] for r in rows if r[2] and r[2]['version']==new]
    mixed=0.0
    if oldtimes and newtimes and max(oldtimes)>min(newtimes):
        mixed=(datetime.fromisoformat(max(oldtimes).replace('Z','+00:00'))-datetime.fromisoformat(min(newtimes).replace('Z','+00:00'))).total_seconds()
    assert abs(mixed-result['mixedSeconds'])<0.001
    assert all(r[3] in full for r in rows), 'Measurement missing from full session'
    summary=read(key+'-summary.txt')
    assert int(re.search(r'Total requests: (\d+)',summary)[1])==len(rows)
    assert int(re.search(r'Failed requests: (\d+)',summary)[1])==failed
    samples=json.loads(read(key+'-pod-samples.json'))
    assert max(s['total'] for s in samples)==result['peakPods']
    if key!='t5-recreate': assert failed==0
    if key in ['t5-recreate','t5-rolling']:
        start=datetime.fromisoformat(result['start'].replace('Z','+00:00'))
        end=datetime.fromisoformat(result['end'].replace('Z','+00:00'))
        apply=datetime.fromisoformat(next(s.split(' ',1)[0] for s in result['events'] if 'apply started' in s).replace('Z','+00:00'))
        done=datetime.fromisoformat(next(s.split(' ',1)[0] for s in result['events'] if 'rollout completed' in s).replace('Z','+00:00'))
        assert (apply-start).total_seconds()>=10 and (end-done).total_seconds()>=10
    print(f"PASS {key}: {len(rows)} requests, {failed} failures, peak {result['peakPods']} application Pods")
rest=records('t4-at-rest-log.txt')
span=(datetime.fromisoformat(rest[-1][0].replace('Z','+00:00'))-datetime.fromisoformat(rest[0][0].replace('Z','+00:00'))).total_seconds()
assert span>=60 and all(r[1]=='OK' for r in rest)
assert all(r[3] in full for r in rest)
print(f'PASS Task 4: {span:.3f} seconds at rest, zero failures')
conditions=read('t6-conditions.txt')
assert 'ProgressDeadlineExceeded' in conditions and '"status": "False"' in conditions
assert 'Exit code: 0' in read('t6-manifest-diff.txt')
print('PASS Task 6: Kubernetes deadline condition and zero manifest diff')
for name in ['t8-notices-before.txt','t8-notices-after-configmap-only.txt']:
    assert json.loads(read(name))['pinnedFirst'] is False
assert json.loads(read('t8-notices-after.txt'))['pinnedFirst'] is True
assert read('t8-existing-pod-flags.txt').splitlines().count('false')==3
assert read('t8-new-pod-flags.txt').splitlines().count('true')==3
assert read('t4-monitor-uid.txt').strip() in read('t8-monitor-continuity.txt')
assert 'Restarts: 0' in read('t8-monitor-continuity.txt')
print('PASS Task 8: false before replacement, true after; same monitor without restarts')
assert 'final Task 8 state verified successfully' in read('t9-rebuild.txt')
assert 'Exit code: 0' in read('t9-rebuild.txt')
assert 'cte412-02230135' not in read('t9-cluster-deleted.txt').split('Remaining clusters:')[1]
print('PASS Task 9: actual README rebuild and lab-cluster deletion')
for path in (root/'manifests').rglob('*.yaml'):
    text=path.read_text(encoding='utf-8-sig')
    assert text.startswith('# Purpose:') and '# Apply:' in text
    assert 'YOUR FULL NAME' not in text and 'postgressDeadlineSeconds' not in text
assert 'version: "1.0.0"' in (root/'manifests/bluegreen/00-blue-deployment.yaml').read_text()
report=(root/'report/p06-report.md').read_text()
for heading in ['1. Objective','2. Environment','3. Results','4. Analysis','5. Reflection','6. References']:
    assert '## '+heading in report
for question in ['A1.','A2.','A3.','A4.','A5.']: assert '### '+question in report
assert 'TO BE RECORDED' not in (root/'README.md').read_text()
print('PASS manifest checks, report headings, analysis questions and README')
print('Student ID: 02230135 - all canonical evidence checks passed.')
