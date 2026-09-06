"""P351 fixed observation adds a fresh provider-readiness witness to P350."""
from pathlib import Path
import ast
import hashlib

PARENT_TEMPLATE = Path(__file__).with_name('s22plus_fyg8_p350_research_shell_observer.py')
PARENT_TEMPLATE_SHA = 'c6590cd5d376a19e325fecfd729b38758a3c5f3fc8c3937cceca85e67a3cd7b6'
_parent_source = PARENT_TEMPLATE.read_bytes()
if hashlib.sha256(_parent_source).hexdigest() != PARENT_TEMPLATE_SHA:
    raise ValueError('P351 observer template identity differs')
_text = _parent_source.decode().replace('P350', 'P351').replace('p350', 'p351')


def _once(old, new):
    global _text
    if _text.count(old) != 1:
        raise ValueError('P351 observer transform seam differs')
    _text = _text.replace(old, new, 1)


_once("        crtc = int(match[1])\n", "        crtc = int(match[1])\n        ready = parse_readiness(middle.output)\n")
_once('middle.output != display_output(crtc)', 'middle.output != display_output(crtc, ready)')
_once('semantic = dict(module_insertions=9,', 'semantic = dict(module_insertions=12, readiness=ready,')
_once("sem=row.get('semantic',{});crtc=sem.get('crtc')", "sem=row.get('semantic',{});crtc=sem.get('crtc');ready=sem.get('readiness')")
_once('expected_sem=dict(module_insertions=9,', 'expected_sem=dict(module_insertions=12,readiness=validate_readiness(ready),')
_once("commands[1]['output']!=identity(display_output(crtc))", "commands[1]['output']!=identity(display_output(crtc,ready))")
_tree = ast.parse(_text)
_tree.body = [n for n in _tree.body if not (isinstance(n, ast.FunctionDef) and n.name == 'display_output')]
exec(compile(ast.fix_missing_locations(_tree), str(PARENT_TEMPLATE) + '#p351', 'exec'), globals())

READY_FIELDS = ('mdp', 'dsi', 'elapsed_ms', 'scans')
READY_PATTERN = (rb'DISPLAY_READY ready=1 complete=1 bus=1 pmic=1 rails=15 drm=1 '
                 rb'mdp=(-?[0-9]+) dsi=(-?[0-9]+) elapsed_ms=([0-9]+) scans=([0-9]+)\n')


def validate_readiness(value):
    if (not isinstance(value, dict) or set(value) != set(READY_FIELDS)
            or any(type(value[k]) is not int for k in READY_FIELDS)
            or value['mdp'] not in (-1, 0, 1) or value['dsi'] not in (-1, 0, 1)
            or not 0 <= value['elapsed_ms'] <= 15000 or not 2 <= value['scans'] <= 152):
        raise QualificationError('P351 fresh readiness evidence differs')
    return dict(value)


def parse_readiness(output):
    matches = list(re.finditer(READY_PATTERN, output))
    if len(matches) != 1 or any(len(v) > 6 for v in matches[0].groups()):
        raise QualificationError('P351 readiness witness absent or duplicated')
    return validate_readiness(dict(zip(READY_FIELDS, map(int, matches[0].groups()))))


def display_output(crtc, ready):
    if type(crtc) is not int or not 1 <= crtc <= 0xffffffff:
        raise QualificationError('P351 CRTC identifier differs')
    ready = validate_readiness(ready)
    rows = []
    for i in range(12):
        rows.extend((f'DISPLAY_LOAD_BEGIN index={i}\n', f'DISPLAY_LOAD_DONE index={i}\n'))
    rows.append('DISPLAY_READY ready=1 complete=1 bus=1 pmic=1 rails=15 drm=1 '
                'mdp={mdp} dsi={dsi} elapsed_ms={elapsed_ms} scans={scans}\n'.format(**ready))
    rows.extend(f'DISPLAY_FLIP run={RUN_ID_HEX} counter={i} crtc={crtc} completed=1\n' for i in range(10))
    rows.append(f'DISPLAY_DONE run={RUN_ID_HEX} completed_frames=10 disabled=1\n')
    return ''.join(rows).encode('ascii')
