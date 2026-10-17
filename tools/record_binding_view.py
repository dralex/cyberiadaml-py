# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The dumps of the CyberiadaML binding, recorded for the cml tests
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
"""Record what the CyberiadaML binding reads from the examples.

    LD_LIBRARY_PATH=... PYTHONPATH=<binding build> \
        python3 tools/record_binding_view.py

writes tests/cml/binding-view.json: per example (tests/examples) and mode
the dump of the LocalDocument (geometry off, the file path left out) or the
class of the exception. tests/cml/test_view.py reads the same with cml.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / 'tests' / 'examples'
VIEW = ROOT / 'tests' / 'cml' / 'binding-view.json'
FILE = re.compile(r", file: '[^']*'")


def view(module, path: pathlib.Path) -> dict:
    """Return the dump or the exception of both modes."""
    result = {}
    for mode, strict in (('lenient', False), ('strict', True)):
        try:
            document = module.LocalDocument()
            document.open(str(path), module.formatDetect,
                          module.geometryFormatNone, False, False, False,
                          False, False, strict)
            result[mode] = FILE.sub('', repr(document))
        except module.Exception as error:
            result[mode] = 'EXC ' + type(error).__name__
        except Exception as error:  # the binding registers them flat
            result[mode] = 'EXC ' + type(error).__name__
    return result


def documents():
    """Return the examples: the standard ones and the Lapki corpus."""
    for folder in ('standard', 'lapki'):
        yield from sorted((EXAMPLES / folder).rglob('*.graphml'))


def main() -> int:
    """Record the view of the importable CyberiadaML module."""
    import CyberiadaML  # type: ignore[import-not-found]
    views = {str(p.relative_to(EXAMPLES)): view(CyberiadaML, p)
             for p in documents()}
    record = {'binding': getattr(CyberiadaML, '__version__', '?'),
              'documents': views}
    VIEW.write_text(json.dumps(record, indent=1, ensure_ascii=False) + '\n',
                    encoding='utf-8')
    print('%d documents recorded' % len(views))
    return 0


if __name__ == '__main__':
    sys.exit(main())
