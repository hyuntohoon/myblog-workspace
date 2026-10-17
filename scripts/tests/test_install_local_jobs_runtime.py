"""The four job plist templates render into the frozen runtime and nothing else."""
import plistlib
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts import install_local_jobs_runtime as installer

RUNTIME = '/runtime-under-test'
COPIED = {*installer.WORKSPACE_FILES, *(f'myblog_shared_db/{rel}' for rel in installer.SHARED_FILES)}


@pytest.mark.parametrize('label', installer.LABELS)
def test_template_renders_into_runtime(label):
    raw = (installer.ROOT / 'scripts' / f'{label}.plist').read_text()
    assert 'myblog-workspace' not in raw
    # launchd tolerates `--` inside the header comments (e.g. `--once`); expat does not.
    body = re.sub(r'<!--.*?-->', '', raw, flags=re.S)
    plist = plistlib.loads(body.replace('__RUNTIME__', RUNTIME).encode())
    assert plist['Label'] == label
    assert plist['WorkingDirectory'].startswith(RUNTIME)
    paths = [arg for arg in plist['ProgramArguments'] if arg.startswith('/')]
    assert paths and all(path.startswith(RUNTIME + '/') for path in paths)
    for path in paths:
        rel = path[len(RUNTIME) + 1:]
        assert rel == '.venv/bin/python' or rel in COPIED, f'{rel} is not copied into the runtime'
