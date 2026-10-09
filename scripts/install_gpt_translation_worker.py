#!/usr/bin/env python3
"""Freeze a dedicated local runtime and install launchd DISABLED. No inference/login."""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.gpt_plan_auth import DEFAULT_DIR, PrivateState

log = logging.getLogger(__name__)
LABEL = 'com.myblog.gpt-translate-poller'
FILES = ('gpt_plan_auth.py','gpt_plan_client.py','gpt_translation_store.py','gpt_queue_worker.py',
         'gpt_worker_setup.py','lyrics_translate_poller.py','lyrics_demand_translate.py')


def revision(path):
    return subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()


def install(state, backend, shared):
    runtime=state.directory / 'runtime'
    if runtime.is_symlink():
        raise RuntimeError('Unsafe runtime path')
    # Prevent mutation of a currently executing runtime or configured live scheduler.
    with state.lock('worker.lock',blocking=False), state.lock('control.lock'):
        if state.settings().get('enabled'):
            raise RuntimeError('Pause the worker before reinstalling')
        runtime.mkdir(mode=0o700,exist_ok=True)
        (runtime/'scripts').mkdir(exist_ok=True)
        for name in FILES:
            shutil.copy2(ROOT/'scripts'/name,runtime/'scripts'/name)
        for source,target in ((backend/'app',runtime/'myblog_backend'/'app'),
                              (shared/'src',runtime/'myblog_shared_db'/'src')):
            target.parent.mkdir(exist_ok=True)
            shutil.copytree(source,target,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        # Local package at the same exact pin avoids independent private-Git authentication.
        lock=(backend/'requirements.lock').read_text()
        requirements=runtime/'requirements.lock'
        requirements.write_text('\n'.join(line for line in lock.splitlines() if not line.startswith('myblog-shared-db @ '))+'\nboto3==1.43.108\n')
        if not (runtime/'.venv/bin/python').exists():
            subprocess.run([sys.executable,'-m','venv',str(runtime/'.venv')],check=True)
        python=str(runtime/'.venv/bin/python')
        subprocess.run([python,'-m','pip','install','-r',str(requirements),str(shared)],check=True)
        manifest={'workspace':revision(ROOT),'backend':revision(backend),'shared':revision(shared),'enabled':False,
                  'script_sha256':{name:hashlib.sha256((runtime/'scripts'/name).read_bytes()).hexdigest() for name in FILES}}
        (runtime/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        raw=(ROOT/'scripts'/f'{LABEL}.plist').read_text().replace('__RUNTIME__',str(runtime)).replace('__STATE__',str(state.directory))
        plist=plistlib.loads(raw.encode())
        plist['ProgramArguments']+=['--state-dir',str(state.directory)]
        plist['EnvironmentVariables']={'HOME':str(Path.home()),'PATH':'/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin'}
        agents=Path.home()/'Library/LaunchAgents';agents.mkdir(parents=True,exist_ok=True)
        path=agents/f'{LABEL}.plist'
        domain=f'gui/{os.getuid()}'
        subprocess.run(['launchctl','disable',f'{domain}/{LABEL}'],check=True)
        subprocess.run(['launchctl','bootout',domain,str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        with path.open('wb') as handle:
            plistlib.dump(plist,handle)
        path.chmod(0o600)
        settings=state.settings();settings.update(enabled=False);state.write('settings.json',settings)
    return runtime


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir',type=Path,default=DEFAULT_DIR)
    parser.add_argument('--backend',type=Path,default=ROOT/'myblog_backend')
    parser.add_argument('--shared',type=Path,default=ROOT/'myblog_shared_db')
    args=parser.parse_args(argv)
    runtime=install(PrivateState(args.state_dir),args.backend.resolve(),args.shared.resolve())
    log.warning('GPT runtime installed disabled: %s',runtime)
    return 0


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(message)s')
    raise SystemExit(main())
