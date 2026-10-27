#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The snapshot of the conformance examples and the Lapki dialect corpus
#
# Copyright (C) 2026 Alexey Fedoseev <aleksey@fedoseev.net>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see https://www.gnu.org/licenses/
#
# -----------------------------------------------------------------------------
"""Copy the cyberiadaml-compat-tests examples into tests/examples.

Usage: tools/sync_examples.py [COMPAT_TESTS_DIR]
"""

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / 'tests' / 'examples'
STANDARD_DIRS = ('core', 'ext', 'fa', 'field', 'geometry', 'negative',
                 'standard')


def _revision(repo: pathlib.Path) -> str:
    out = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'],
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


def sync(compat: pathlib.Path) -> str:
    """Replace the snapshot; return the source revision."""
    fixtures = compat / 'fixtures'
    standard = EXAMPLES / 'standard'
    lapki = EXAMPLES / 'lapki'
    for target in (standard, lapki):
        if target.exists():
            shutil.rmtree(target)
    for name in STANDARD_DIRS:
        shutil.copytree(fixtures / name, standard / name)
    shutil.copy2(fixtures / 'manifest.json', standard / 'manifest.json')
    shutil.copytree(fixtures / 'dialect' / 'lapki', lapki)
    revision = _revision(compat)
    (EXAMPLES / 'REVISION').write_text(
        'cyberiadaml-compat-tests %s\n' % revision, encoding='utf-8')
    return revision


def main(argv: list) -> int:
    """Run the tool."""
    compat = pathlib.Path(argv[1]) if len(argv) > 1 else \
        ROOT.parent / 'cyberiadaml-compat-tests'
    print('tests/examples from cyberiadaml-compat-tests %s' % sync(compat))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
