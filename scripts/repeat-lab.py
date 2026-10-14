"""Repeat the assessed lab with real measurements; changes only this named lab cluster.
Run with Python 3.12 from the repository root. Requires Docker, kind and kubectl.
Original evidence must be archived before replacing the canonical measurement files.
"""
import collections
import datetime as dt
import json
import pathlib
import subprocess
import threading
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
E = ROOT / 'evidence'
SID = '02230135'
NAME = 'cte412-' + SID
CTX = 'kind-' + NAME
NS = 'nb-' + SID
K = ['kubectl', '--context', CTX, '-n', NS]
ROLL = ROOT/'manifests/rolling/00-deployment.yaml'
BLUE = ROOT/'manifests/bluegreen/00-blue-deployment.yaml'
GREEN = ROOT/'manifests/bluegreen/01-green-deployment.yaml'
SVC = ROOT/'manifests/bluegreen/02-production-services.yaml'
FLAGS = ROOT/'manifests/bluegreen/04-feature-flags.yaml'
FINAL = {p: p.read_text(encoding='utf-8') for p in [ROLL, BLUE, GREEN, SVC, FLAGS]}
RESULTS = []

def stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')

def save(name, data):
    (E/name).write_text(data, encoding='utf-8', newline='\n')

def run(args, file=None, allowed=(0,)):
    result = subprocess.run([str(a) for a in args], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    if file:
        save(file, 'Student ID: '+SID+'\nCommand: '+subprocess.list2cmdline([str(a) for a in args])+'\n'+result.stdout+f'\nExit code: {result.returncode}\n')
    if result.returncode not in allowed:
        raise RuntimeError(subprocess.list2cmdline([str(a) for a in args])+'\n'+result.stdout)
    return result.stdout

def apply(path):
    return run(K+['apply','-f',path])

def rollout(name='notice-board'):
    return run(K+['rollout','status','deployment/'+name,'--timeout=240s'])

def obj(kind, name=None, selector=None):
    args=K+['get',kind]
    if name: args += [name]
    if selector: args += ['-l',selector]
    return json.loads(run(args+['-o','json']))

def host(path):
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:30090'+path, timeout=3) as r:
        return json.loads(r.read())

def variant(version, cause, recreate=False):
    import re
    text=FINAL[ROLL].replace('notice-board:02230135-1.1.0','notice-board:02230135-'+version).replace('version: "1.1.0"','version: "'+version+'"')
    text=re.sub(r'kubernetes.io/change-cause: .*', 'kubernetes.io/change-cause: "'+cause+'" # Explain this revision.',text)
    if recreate:
        text=text.replace('    type: RollingUpdate # Replace Pods gradually while maintaining ready capacity.\n    rollingUpdate:\n      maxUnavailable: 0 # Keep all three Pods ready during the rolling update.\n      maxSurge: 1 # Allow one extra Pod to be created during the rolling update.', '    type: Recreate # Remove old Pods before starting the new release.')
        assert 'rollingUpdate:' not in text
    ROLL.write_text(text,encoding='utf-8')

def endpoints(prefix):
    for svc, tag in [('notice-board','production'),('notice-board-preview','preview')]:
        run(K+['get','endpointslices','-l','kubernetes.io/service-name='+svc,'-o','yaml'],f't7-{tag}-endpoints-{prefix}.txt')

class Measurement:
    def __init__(self, key):
        self.key=key
        self.start=stamp()
        self.events=[]
        self.samples=[]
        self.stop=threading.Event()
        self.thread=threading.Thread(target=self.sample,daemon=True)
        self.thread.start()
        self.watch=None
        if key=='t5-rolling':
            self.watchfile=(E/'t5-rolling-pod-watch.txt').open('w',encoding='utf-8')
            self.watchfile.write('Student ID: '+SID+'\n'); self.watchfile.flush()
            self.watch=subprocess.Popen(K+['get','pods','-l','app=notice-board','--watch','-o','wide'],cwd=ROOT,stdout=self.watchfile,stderr=subprocess.STDOUT)
    def sample(self):
        while not self.stop.is_set():
            try:
                pods=obj('pods',selector='app=notice-board')['items']
                active=[p for p in pods if not p['metadata'].get('deletionTimestamp')]
                self.samples.append({'timestamp':stamp(),'total':len(pods),'nonTerminating':len(active),'pods':[{'name':p['metadata']['name'],'version':p['metadata']['labels'].get('version'),'terminating':bool(p['metadata'].get('deletionTimestamp')),'ready':any(c['type']=='Ready' and c['status']=='True' for c in p.get('status',{}).get('conditions',[]))} for p in pods]})
            except Exception as exc:
                self.events.append(stamp()+' sampling error '+str(exc))
            self.stop.wait(0.7)
    def event(self, msg):
        self.events.append(stamp()+' '+msg)
    def finish(self, zero=False, old='1.0.0', new='1.1.0'):
        time.sleep(10.5)
        end=stamp()
        self.stop.set(); self.thread.join(timeout=10)
        if self.watch:
            self.watch.terminate(); self.watch.wait(timeout=10); self.watchfile.close()
        log=run(K+['logs','monitor','--since-time='+self.start])
        lines=[]
        counts=collections.Counter(); failures=0; parsed=[]
        for line in log.splitlines():
            ts,status,body=line.split(' ',2)
            if ts>end: continue
            lines.append(line)
            version=None
            if status=='FAIL': failures+=1
            else:
                version=json.loads(body)['version']; counts[version]+=1
            parsed.append((ts,status,version))
        save(self.key+'-log.txt','\n'.join(lines)+'\n')
        self.events.append(end+' capture ended')
        save(self.key+'-events.txt','Student ID: '+SID+'\n'+'\n'.join(self.events)+'\n')
        save(self.key+'-pod-samples.json',json.dumps(self.samples,indent=2)+'\n')
        # Execute the actual assessed shell summariser inside the Alpine image.
        summary=run(['docker','run','--rm','--mount',f'type=bind,source={ROOT},target=/lab,readonly','notice-board:02230135-1.0.0','sh','/lab/scripts/summarise.sh','/lab/evidence/'+self.key+'-log.txt'])
        save(self.key+'-summary.txt',summary)
        oldtimes=[x[0] for x in parsed if x[2]==old]; newtimes=[x[0] for x in parsed if x[2]==new]
        mixed=0.0
        if oldtimes and newtimes and max(oldtimes)>min(newtimes):
            mixed=(dt.datetime.fromisoformat(max(oldtimes).replace('Z','+00:00'))-dt.datetime.fromisoformat(min(newtimes).replace('Z','+00:00'))).total_seconds()
        record={'experiment':self.key,'start':self.start,'end':end,'requests':len(lines),'failed':failures,'versions':dict(counts),'mixedSeconds':mixed,'peakPods':max(x['total'] for x in self.samples),'peakNonTerminatingPods':max(x['nonTerminating'] for x in self.samples),'events':self.events}
        RESULTS.append(record); save('t9-results.json',json.dumps(RESULTS,indent=2)+'\n')
        print(json.dumps(record),flush=True)
        if zero and failures: raise RuntimeError(f'{self.key}: {failures} failures; investigate before claiming completion')
        return record

def main():
    clusters=run(['kind','get','clusters']).splitlines()
    if NAME in clusters:
        raise RuntimeError('A lab cluster already exists. Inspect it before running this fresh-session script.')
    print('Creating isolated lab cluster',flush=True)
    run(['kind','create','cluster','--name',NAME,'--config','cluster/kind-cluster.yaml'],'t1-cluster-create.txt')
    run(K+['wait','--for=condition=Ready','nodes','--all','--timeout=240s'])
    for f in ['00-namespace.yaml','01-resourcequota.yaml','02-limitrange.yaml']: apply(ROOT/'manifests/base'/f)
    run(['kubectl','config','set-context',CTX,'--namespace='+NS])
    run(K+['get','nodes','-o','wide'],'t1-nodes.txt')
    run(K+['describe','quota','notice-board-quota'],'t1-quota.txt')
    run(['kubectl','config','view','--minify','--context',CTX],'t1-context.txt')
    run(K+['get','namespace',NS,'-o','yaml'],'t1-namespace.txt')
    run(K+['describe','limitrange','notice-board-defaults'],'t1-limitrange.txt')
    versions='Student ID: '+SID+'\n'
    for args in [['docker','version'],['kind','version'],K+['version','-o','yaml'],['git','--version']]: versions+=run(args)+'\n'
    save('t1-software-versions.txt',versions)
    print('Building and loading application images',flush=True)
    tags=[]
    for version in ['1.0.0','1.1.0','1.2.0-broken']:
        tag='notice-board:'+SID+'-'+version; tags.append(tag)
        run(['docker','build','--build-arg','APP_VERSION='+version,'--build-arg','STUDENT_ID='+SID,'-t',tag,'./app'],'t2-build-'+version+'.txt')
    run(['docker','image','ls','notice-board'],'t2-local-images.txt')
    run(['kind','load','docker-image',*tags,'--name',NAME],'t2-image-load.txt')
    run(['docker','exec',NAME+'-worker','crictl','images'],'t2-worker-images.txt')
    # Capture warm-up inside a freshly started local container, avoiding manual timing.
    probe="""import urllib.request, urllib.error, time, json, os
print('Student ID: 02230135 uid='+str(os.getuid()), flush=True)
for stage in ['before-five-seconds','after-five-seconds']:
 if stage.startswith('after'): time.sleep(5.2)
 for path in ['/version','/healthz']:
  try: r=urllib.request.urlopen('http://127.0.0.1:8080'+path)
  except urllib.error.HTTPError as e: r=e
  print(stage,path,'HTTP',r.status,r.read().decode(),flush=True)
"""
    local='nb-audit-'+SID
    run(['docker','run','-d','--name',local,tags[0]])
    try:
        health=run(['docker','exec',local,'python','-c',probe]); save('t2-baseline-health.txt',health)
        assert 'HTTP 503' in health and 'HTTP 200' in health
        run(['docker','exec',local,'id'],'t2-container-user.txt')
    finally: run(['docker','rm','-f',local])
    variant('1.0.0','Task 3: baseline 02230135-1.0.0')
    for f in ['00-deployment.yaml','01-service.yaml','02-service-external.yaml']: apply(ROOT/'manifests/rolling'/f)
    rollout()
    run(K+['get','deployment,replicaset,pods','-l','app=notice-board','-o','wide'],'t3-workloads.txt')
    run(K+['get','endpointslices','-l','kubernetes.io/service-name=notice-board','-o','yaml'],'t3-endpointslices.txt')
    responses=[host('/version') for _ in range(18)]
    assert len({x['pod'] for x in responses})>=2
    save('t3-host-version-responses.txt','\n'.join(json.dumps(x) for x in responses)+'\n')
    run(K+['get','services','-l','app=notice-board'],'t3-services.txt')
    run(K+['describe','quota','notice-board-quota'],'t3-quota.txt')
    apply(ROOT/'manifests/base/03-monitor-code.yaml'); apply(ROOT/'manifests/base/04-monitor-pod.yaml')
    run(K+['wait','--for=condition=Ready','pod/monitor','--timeout=120s'])
    uid=obj('pod','monitor')['metadata']['uid']; save('t4-monitor-uid.txt',uid+'\n')
    run(K+['get','pod','monitor','-o','wide'],'t4-monitor-pod.txt')
    full=(E/'t9-monitor-full.log').open('w',encoding='utf-8')
    follow=subprocess.Popen(K+['logs','-f','monitor'],cwd=ROOT,stdout=full,stderr=subprocess.PIPE)
    print('Task 4: one minute at rest',flush=True)
    # Ready means the container started, not that Python has emitted its first line.
    for attempt in range(60):
        if run(K+['logs','monitor','--tail=1']).strip(): break
        time.sleep(1)
    else: raise RuntimeError('Monitor produced no log output')
    start=stamp(); time.sleep(61)
    rest=run(K+['logs','monitor','--since-time='+start]); save('t4-at-rest-log.txt',rest); save('t4-at-rest-first10.txt','\n'.join(rest.splitlines()[:10])+'\n')
    assert ' FAIL ' not in rest
    summary=run(['docker','run','--rm','--mount',f'type=bind,source={ROOT},target=/lab,readonly',tags[0],'sh','/lab/scripts/summarise.sh','/lab/evidence/t4-at-rest-log.txt']); save('t4-at-rest-summary.txt',summary)
    print('Task 5: Recreate',flush=True)
    m=Measurement('t5-recreate'); time.sleep(10.5)
    variant('1.1.0','Task 5: Recreate release 02230135-1.1.0',True)
    m.event('apply started'); apply(ROLL); m.event('apply completed'); rollout(); m.event('rollout completed')
    save('t5-recreate-manifest.yaml',ROLL.read_text()); m.finish()
    variant('1.0.0','Task 5: restore baseline 02230135-1.0.0',True); apply(ROLL); rollout()
    time.sleep(3)
    print('Task 5: RollingUpdate',flush=True)
    m=Measurement('t5-rolling'); time.sleep(10.5)
    variant('1.1.0','Task 5: RollingUpdate release 02230135-1.1.0')
    m.event('apply started'); apply(ROLL); m.event('apply completed'); rollout(); m.event('rollout completed')
    save('t5-rolling-manifest.yaml',ROLL.read_text()); m.finish(zero=True)
    run(K+['rollout','history','deployment/notice-board'],'t5-rollout-history.txt')
    for key in ['recreate','rolling']:
        out=run(['docker','run','--rm','--mount',f'type=bind,source={ROOT},target=/lab,readonly',tags[0],'python','/lab/scripts/mixed-window.py','/lab/evidence/t5-'+key+'-log.txt']); save('t5-'+key+'-mixed-window.txt',out)
    print('Task 6: failed release and rollback',flush=True)
    m=Measurement('t6-monitor'); time.sleep(10.5)
    variant('1.2.0-broken','Task 6: broken release 02230135-1.2.0-broken')
    m.event('broken apply started'); apply(ROLL); m.event('broken apply completed')
    run(K+['rollout','status','deployment/notice-board','--timeout=180s'],'t6-failed-rollout.txt',allowed=(1,))
    d=obj('deployment','notice-board')
    assert any(c['type']=='Progressing' and c['status']=='False' and c['reason']=='ProgressDeadlineExceeded' for c in d['status']['conditions'])
    save('t6-conditions.txt','Student ID: '+SID+'\n'+json.dumps(d['status']['conditions'],indent=2)+'\n')
    run(K+['get','deployment','notice-board','-o','yaml'],'t6-failed-deployment.txt')
    run(K+['get','pods','-l','app=notice-board','-L','version','-o','wide'],'t6-failed-pods.txt')
    save('t6-serving-version.txt',json.dumps(host('/version'))+'\n'); save('t6-broken-manifest.yaml',ROLL.read_text())
    m.event('rollback started'); run(K+['rollout','undo','deployment/notice-board'],'t6-rollback.txt'); rollout(); m.event('rollback completed')
    variant('1.1.0','Task 5: RollingUpdate release 02230135-1.1.0'); apply(ROLL)
    run(K+['diff','-f',ROLL],'t6-manifest-diff.txt')
    run(K+['get','pods','-l','app=notice-board','-L','version'],'t6-restored-pods.txt')
    m.finish(zero=True)
    print('Task 7: prepare blue and green (setup gap excluded from switch windows)',flush=True)
    run(K+['delete','-f',ROLL,'--wait=true'])
    BLUE.write_text(FINAL[BLUE],encoding='utf-8')
    green_initial=FINAL[GREEN].replace('      annotations:\n        cte412/flag-revision: "enabled-1" # Replace Pods so they read the updated flag.\n','')
    # Start green with a false-valued ConfigMap; Task 8 will demonstrate the flag change.
    FLAGS.write_text(FINAL[FLAGS].replace('FEATURE_PINNED: "true"','FEATURE_PINNED: "false"'),encoding='utf-8')
    GREEN.write_text(green_initial,encoding='utf-8'); SVC.write_text(FINAL[SVC].replace('slot: green','slot: blue'),encoding='utf-8')
    for f in [FLAGS,BLUE,GREEN,SVC,ROOT/'manifests/bluegreen/03-preview-service.yaml']: apply(f)
    rollout('notice-board-blue'); rollout('notice-board-green')
    endpoints('before')
    code="import urllib.request; print(urllib.request.urlopen('http://%s/version').read().decode())"
    preview='Student ID: '+SID+'\nProduction:\n'+run(K+['exec','monitor','--','python','-c',code%'notice-board'])+'Preview:\n'+run(K+['exec','monitor','--','python','-c',code%'notice-board-preview'])
    save('t7-preview-comparison.txt',preview)
    run(K+['describe','quota','notice-board-quota'],'t7-quota.txt')
    combined_start=stamp(); switch_events=[]
    for i,slot in enumerate(['green','blue','green'],1):
        print('Task 7: switch '+str(i)+' to '+slot,flush=True)
        m=Measurement('t7-switch'+str(i)); time.sleep(10.5)
        SVC.write_text(FINAL[SVC].replace('slot: green','slot: '+slot),encoding='utf-8')
        m.event('switch apply started target='+slot); apply(SVC); m.event('switch apply completed target='+slot)
        r=m.finish(zero=True,old='1.1.0' if slot=='blue' else '1.0.0',new='1.0.0' if slot=='blue' else '1.1.0'); switch_events+=r['events']
        assert host('/version')['version']==('1.0.0' if slot=='blue' else '1.1.0')
        if i==1: endpoints('after')
    save('t7-switch-events.txt','Student ID: '+SID+'\n'+'\n'.join(switch_events)+'\n')
    save('t7-switch-monitor-log.txt',run(K+['logs','monitor','--since-time='+combined_start]))
    save('t7-switch-monitor-summary.txt',run(['docker','run','--rm','--mount',f'type=bind,source={ROOT},target=/lab,readonly',tags[0],'sh','/lab/scripts/summarise.sh','/lab/evidence/t7-switch-monitor-log.txt']))
    print('Task 8: false -> ConfigMap true -> declarative replacement',flush=True)
    m=Measurement('t8-monitor'); time.sleep(10.5)
    assert host('/notices')['pinnedFirst'] is False
    save('t8-notices-before.txt',json.dumps(host('/notices'))+'\n')
    pods=obj('pods',selector='app=notice-board,slot=green')['items']; before={p['metadata']['name']:p['metadata']['uid'] for p in pods}
    save('t8-pods-before-flag.txt','Student ID: '+SID+'\n'+json.dumps(before,indent=2)+'\n')
    FLAGS.write_text(FINAL[FLAGS],encoding='utf-8'); m.event('ConfigMap-only apply started'); apply(FLAGS); m.event('ConfigMap-only apply completed'); time.sleep(3)
    existing=run(K+['get','configmap','notice-board-flags','-o','yaml'])
    for name in before:
        val=run(K+['exec',name,'--','printenv','FEATURE_PINNED']).strip(); assert val=='false'; existing+='\nPod: '+name+'\n'+val+'\n'
    assert before=={p['metadata']['name']:p['metadata']['uid'] for p in obj('pods',selector='app=notice-board,slot=green')['items']}
    save('t8-existing-pod-flags.txt','Student ID: '+SID+'\n'+existing)
    assert host('/notices')['pinnedFirst'] is False
    save('t8-notices-after-configmap-only.txt',json.dumps(host('/notices'))+'\n')
    GREEN.write_text(FINAL[GREEN],encoding='utf-8'); m.event('flag rollout apply started'); apply(GREEN); rollout('notice-board-green'); m.event('flag rollout completed')
    newflags='Student ID: '+SID+'\n'
    for p in obj('pods',selector='app=notice-board,slot=green')['items']:
        if p['metadata'].get('deletionTimestamp'): continue
        name=p['metadata']['name']; val=run(K+['exec',name,'--','printenv','FEATURE_PINNED']).strip(); assert val=='true'; newflags+='Pod: '+name+'\n'+val+'\n'
    save('t8-new-pod-flags.txt',newflags)
    after=host('/notices'); assert after['pinnedFirst'] and after['notices'][0]['id']==2
    save('t8-notices-after.txt',json.dumps(after)+'\n'); m.finish(zero=True)
    monitor=obj('pod','monitor'); assert monitor['metadata']['uid']==uid
    assert all(x.get('restartCount',0)==0 for x in monitor['status']['containerStatuses'])
    save('t8-monitor-continuity.txt','Student ID: '+SID+'\nSame monitor UID Tasks 4-8: '+uid+'\nRestarts: 0\n')
    # Persist complete session before deleting the measuring instrument.
    follow.terminate(); follow.wait(timeout=10); full.close()
    save('t9-monitor-full.log',run(K+['logs','monitor']))
    print('Experiments complete; final-state rebuild is next.',flush=True)
    for p,s in FINAL.items(): p.write_text(s,encoding='utf-8')

if __name__=='__main__':
    try: main()
    finally:
        for p,s in FINAL.items(): p.write_text(s,encoding='utf-8')
