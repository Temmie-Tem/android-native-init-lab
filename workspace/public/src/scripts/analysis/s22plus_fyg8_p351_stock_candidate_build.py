"""P351 H0 packaging: exact display providers, readiness and white renderer."""
from pathlib import Path
import ast
import hashlib

PARENT_TEMPLATE = Path(__file__).with_name('s22plus_fyg8_p350_stock_candidate_build.py')
PARENT_TEMPLATE_SHA = '2cc546ce347ce185a8e859a919fdf7317c2c089e2ffc6e904fc708f7f743f9a4'
_parent_source = PARENT_TEMPLATE.read_bytes()
if hashlib.sha256(_parent_source).hexdigest() != PARENT_TEMPLATE_SHA:
    raise ValueError('P351 builder template identity differs')
_text = _parent_source.decode().replace('P350', 'P351').replace('p350', 'p351')
_text = _text.replace('P351_DISPLAY_VARIANT', 'P350_DISPLAY_VARIANT')
_text = _text.replace('stock-candidate-build-v1-20260906-02', 'stock-candidate-build-v1-20260906-01')


def _once(old, new):
    global _text
    if _text.count(old) != 1:
        raise ValueError('P351 builder transform seam differs')
    _text = _text.replace(old, new, 1)


_once('tuple(order)!=MODULE_NAMES', 'tuple(order)!=artifact.DISPLAY_MODULE_NAMES[3:]')
_once("    write(out/'inputs/s22plus_native_display_plan.h',plan)",
      "    write(out/'inputs/s22plus_native_display_plan.h',plan)\n    write(out/'inputs/renderer.c',renderer_source.render())")
_once("    modules={n:stable(DISPLAY/'union-modules-final'/n,{'size':graph['results'][n]['size'],'sha256':graph['results'][n]['sha256']}) for n in MODULE_NAMES}",
      '    modules=display_modules(graph)')
_once('        source_inputs=sources,', '        display_prerequisites=prerequisite_identity(),source_inputs=sources,')
# Both compilation and dependency extraction use the exact generated input.
if _text.count("'-I',HEADERS,NATIVE/'s22plus_native_display_h0.c'") != 2:
    raise ValueError('P351 renderer compiler seam differs')
_text = _text.replace("'-I',HEADERS,NATIVE/'s22plus_native_display_h0.c'",
                      "'-I',HEADERS,'-I',NATIVE,out/'inputs/renderer.c'")
_tree = ast.parse(_text)
_tree.body = [n for n in _tree.body if not (isinstance(n, ast.If) and '__name__' in ast.unparse(n.test))]
exec(compile(ast.fix_missing_locations(_tree), str(PARENT_TEMPLATE) + '#p351', 'exec'), globals())

import s22plus_fyg8_p351_display_renderer as renderer_source
import s22plus_fyg8_display_executability_h0 as prerequisites

PROVIDERS = ROOT / 'workspace/private/outputs/s22-display-provider-h0'
PREREQUISITE = ROOT / 'workspace/private/outputs/s22plus_fyg8_p351/h0-work/executability-final.json'
PREREQUISITE_SHA = '40eaaf46a7dbb2293cf647a3962f71e528dd2a9bfce207ebecc5e6d455bc0d8a'
ADDITIONS = {
    'pmic_class.ko': {'size': 14408, 'sha256': '9fd0b4fd098ed0d5e8110c7e12966d5ce4844be313345088d9dfa533588a10e5'},
    's2dos05-regulator.ko': {'size': 79256, 'sha256': 'e7a194604a55b6c4ef5843a57d6d27e4613281b6e9f45dbca144b63a5abb5381'},
    'i2c-gpio.ko': {'size': 279984, 'sha256': '591962b082222ced903e7d8901bda637ff3a3c0dc3e156a89ee9c6253349f82a'},
}


def prerequisite_identity():
    linkage = stable(PROVIDERS / 'scoped-linkage.json')
    if hashlib.sha256(linkage).hexdigest() != '67b6ca3cbe7694ab8b9a0b0ec8b10dcea3fb553ea1c61352884dff8792c6e822':
        raise AuditError('P351 reviewed provider linkage changed')
    raw = stable(PREREQUISITE)
    if hashlib.sha256(raw).hexdigest() != PREREQUISITE_SHA:
        raise AuditError('P351 display prerequisite not qualified or changed')
    result = json.loads(raw)
    if result['extractor'] != identity(stable(Path(prerequisites.__file__))):
        raise AuditError('P351 prerequisite extractor changed')
    for name, expected in result['inputs'].items():
        stable(ROOT / name, expected)
    for name, expected in result['tool_inputs'].items():
        if identity(Path(name).read_bytes()) != expected:
            raise AuditError('P351 prerequisite tool changed')
    for path, key in ((prerequisites.fixed.DEFAULT_DTBO, 'dtbo'),
                      (prerequisites.fixed.DEFAULT_VENDOR_DTB, 'vendor_dtb'),
                      (prerequisites.fixed.DEFAULT_CONFIG, 'image_config')):
        stable(ROOT / path, result[key])
    stable(DISPLAY / 'vendor-kernel-out/.config', result['display_config'])
    if prerequisites.fixed.module_plan.load_metadata(ROOT / prerequisites.fixed.DEFAULT_METADATA).metadata_hashes != result['metadata']:
        raise AuditError('P351 module metadata changed')
    for name, expected in result['modules'].items():
        path = provider_path(name) if name in ADDITIONS else DISPLAY / 'union-modules-final' / name
        stable(path, expected)
    return identity(raw)


def provider_path(name):
    return PROVIDERS / ('i2c-display-only' if name == 'i2c-gpio.ko' else 'modules') / name


_base_module_plan = module_plan


def module_plan(graph):
    prerequisite_identity()
    plan = _base_module_plan(graph).replace(b'P351_DISPLAY_MODULE_COUNT 9U', b'P350_DISPLAY_MODULE_COUNT 12U')
    plan = plan.replace(b'p351_display_module', b'p350_display_module')
    extra = ''.join('    {"/s22-display-modules/%s", %dULL, 0},\n' % (name, value['size'])
                    for name, value in ADDITIONS.items()).encode()
    seam = b'p350_display_modules[] = {\n'
    if plan.count(seam) != 1:
        raise AuditError('P351 provider plan seam differs')
    return plan.replace(seam, seam + extra)


def display_modules(graph):
    return {name: stable(provider_path(name), ADDITIONS[name]) if name in ADDITIONS else
            stable(DISPLAY / 'union-modules-final' / name,
                   {k: graph['results'][name][k] for k in ('size', 'sha256')}) for name in MODULE_NAMES}


_base_source_files = source_files


def source_files():
    values = _base_source_files()
    paths = [PARENT_TEMPLATE, NATIVE / 's22plus_native_display_ready_v2.inc.c',
             NATIVE / 's22plus_native_display_visible_layout_h0.c']
    paths += [ROOT / 'workspace/public/src/scripts/revalidation' / ('s22plus_fyg8_p350_' + name + '.py')
              for name in ('artifact_identity', 'research_shell_runtime', 'research_shell_observer', 'stock_process_v2_adapter')]
    for path in paths:
        values[str(path.relative_to(ROOT))] = path
    return values


_base_audit_existing = audit_existing


def audit_existing(output_root=DEFAULT_OUTPUT_ROOT):
    result = _base_audit_existing(output_root)
    if result.get('display_prerequisites') != prerequisite_identity():
        raise AuditError('P351 prerequisite build join differs')
    out = Path(output_root)
    if stable(out / 'inputs/renderer.c') != renderer_source.render():
        raise AuditError('P351 generated renderer differs')
    graph = json.loads(stable(DISPLAY / 'union-audit-final.json'))
    if stable(out / 'inputs/s22plus_native_display_plan.h', result['module_plan']) != module_plan(graph):
        raise AuditError('P351 generated module plan differs')
    expected = {name: identity(raw) for name, raw in display_modules(graph).items()}
    if result['module_bytes'] != expected:
        raise AuditError('P351 exact display module join differs')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument('--audit-only', action='store_true')
    args = parser.parse_args()
    result = build_result(args.out, audit_only=args.audit_only)
    print(json.dumps({'verdict': result['verdict'], 'ap': result['candidate']['a']['ap_tar_md5']}, sort_keys=True))
