#!/usr/bin/env python3
"""Freeze the four local launchd jobs into a dedicated runtime and (re)install their plists.

research-poller, genre-heal-poller, buckit-nightly and genre-backfill used to run straight
out of the shared workspace checkout, so whatever that checkout happened to have checked
out was production. This copies the files they need from two clean checkouts (workspace +
myblog_shared_db, normally fresh worktrees at origin/main) into
~/.local/share/myblog-jobs/runtime, mirroring the workspace layout so every script's
__file__-relative paths keep working, with one venv and a manifest of the revisions.
Changing code on main changes nothing until this is rerun. Precedent:
install_gpt_translation_worker.py.

    python3 scripts/install_local_jobs_runtime.py --shared <myblog_shared_db checkout>

Refuses while any of the four jobs has a live process, or while a source tree has
uncommitted changes. The previous plists are kept under <state>/plist-backup/<timestamp>/;
rollback = copy them back, then `launchctl bootout` + `launchctl bootstrap` each label.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = Path.home() / '.local/share/myblog-jobs'
AGENTS = Path.home() / 'Library/LaunchAgents'
PYTHON = '/opt/homebrew/bin/python3.12'  # same base interpreter as the gpt runtime

log = logging.getLogger(__name__)
LABELS = ('com.myblog.research-poller', 'com.myblog.genre-heal-poller',
          'com.myblog.buckit-nightly', 'com.myblog.genre-backfill')
# Workspace files, relative to the workspace root (and to the runtime root).
WORKSPACE_FILES = ('scripts/research_poller.py', 'scripts/album_research_v2.md',
                   'scripts/buckit_nightly.py', 'scripts/genre_heal_poller.py',
                   'scripts/neuralwatt_claude_shim.py', 'scripts/automation_heartbeat.py',
                   'docs/editorial/buckit-nightly-run.md', 'docs/editorial/buckit-nightly.md',
                   'docs/editorial/review-critique-method.md')
SHARED_FILES = ('scripts/backfill_genres.py',)
# The scripts import shared_db from <root>/myblog_shared_db/src, not from the venv, so the
# venv only carries third-party packages (pins match the backend/worker venvs they replace).
REQUIREMENTS = ('psycopg[binary]==3.3.4', 'boto3==1.43.15', 'SQLAlchemy==2.0.51')


def revision(path: Path) -> str:
    return subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()


def require_clean(path: Path) -> None:
    dirty = subprocess.check_output(['git', '-C', str(path), 'status', '--porcelain', '--untracked-files=no'],
                                    text=True).strip()
    if dirty:
        raise RuntimeError(f'{path} has uncommitted changes; install from a clean checkout')


def running(label: str) -> bool:
    """True when launchd reports a live PID for the label (`launchctl list <label>` has a "PID" key)."""
    out = subprocess.run(['launchctl', 'list', label], capture_output=True, text=True)
    return out.returncode == 0 and '"PID" =' in out.stdout


def copy_tree(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)  # drop modules deleted upstream; the jobs are stopped
    shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))


def install(workspace: Path, shared: Path, state: Path) -> Path:
    for source in (workspace, shared):
        require_clean(source)
    busy = [label for label in LABELS if running(label)]
    if busy:
        raise RuntimeError(f'job(s) running now, retry when idle: {", ".join(busy)}')

    runtime = state / 'runtime'
    if runtime.is_symlink():
        raise RuntimeError('Unsafe runtime path')
    domain = f'gui/{os.getuid()}'
    backup = state / 'plist-backup' / time.strftime('%Y%m%d-%H%M%S')
    backup.mkdir(parents=True)
    for label in LABELS:
        path = AGENTS / f'{label}.plist'
        if path.exists():
            shutil.copy2(path, backup / path.name)
        subprocess.run(['launchctl', 'bootout', f'{domain}/{label}'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
        for rel in WORKSPACE_FILES:
            (runtime / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(workspace / rel, runtime / rel)
        copy_tree(shared / 'src', runtime / 'myblog_shared_db' / 'src')
        for rel in SHARED_FILES:
            (runtime / 'myblog_shared_db' / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(shared / rel, runtime / 'myblog_shared_db' / rel)
        # buckit_nightly writes its draft backups to <root>/docs/buckit/<date>/; keep them in the
        # state dir so they outlive any reinstall of the runtime.
        (state / 'buckit').mkdir(exist_ok=True)
        link = runtime / 'docs' / 'buckit'
        if not link.is_symlink():
            link.symlink_to(state / 'buckit')

        python = runtime / '.venv/bin/python'
        if not python.exists():
            subprocess.run([PYTHON, '-m', 'venv', str(runtime / '.venv')], check=True)
        subprocess.run([str(python), '-m', 'pip', 'install', '--quiet', *REQUIREMENTS], check=True)

        copied = [*WORKSPACE_FILES, *(f'myblog_shared_db/{rel}' for rel in SHARED_FILES)]
        manifest = {'workspace': revision(workspace), 'shared': revision(shared),
                    'sha256': {rel: hashlib.sha256((runtime / rel).read_bytes()).hexdigest() for rel in copied}}
        (runtime / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')

        for label in LABELS:
            rendered = (workspace / 'scripts' / f'{label}.plist').read_text().replace('__RUNTIME__', str(runtime))
            path = AGENTS / f'{label}.plist'
            path.write_text(rendered)
            subprocess.run(['launchctl', 'bootstrap', domain, str(path)], check=True)
    except BaseException:
        # Never leave the jobs unloaded: put the previous plists back and start them again.
        for saved in backup.glob('*.plist'):
            shutil.copy2(saved, AGENTS / saved.name)
            subprocess.run(['launchctl', 'bootout', domain, str(AGENTS / saved.name)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['launchctl', 'bootstrap', domain, str(AGENTS / saved.name)])
        log.error('install failed; previous plists restored from %s', backup)
        raise
    log.info('jobs runtime installed: %s (workspace %s, shared %s); old plists in %s',
             runtime, manifest['workspace'][:7], manifest['shared'][:7], backup)
    return runtime


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--workspace', type=Path, default=ROOT)
    parser.add_argument('--shared', type=Path, default=ROOT / 'myblog_shared_db')
    parser.add_argument('--state-dir', type=Path, default=STATE)
    args = parser.parse_args(argv)
    install(args.workspace.resolve(), args.shared.resolve(), args.state_dir)
    return 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    raise SystemExit(main())
