"""P353 fresh H0 namespace over the sealed P351 template; no device authority."""
from pathlib import Path
import ast
import hashlib

P351_TEMPLATE = Path(__file__).with_name('s22plus_fyg8_p351_stock_candidate_build.py')
P351_TEMPLATE_SHA = '5564871d5c3f4b841b38bc4052ecba82d7327ee24d2ad17f71597d54e8ae3907'
_source = P351_TEMPLATE.read_bytes()
if hashlib.sha256(_source).hexdigest() != P351_TEMPLATE_SHA:
    raise ValueError("P353 predecessor template identity differs")
_source = _source.replace(b'P351', b'P353').replace(b'p351', b'p353')
_source = _source.replace(b'c351f1e0a90b5e6d7c8a9b0c1d2e3f0b', b'c353f1e0a90b5e6d7c8a9b0c1d2e3f0b')
_source = _source.replace(b'outputs/s22plus_fyg8_p353/h0-work/executability-final.json', b'outputs/s22plus_fyg8_p351/h0-work/executability-final.json')
_source = _source.replace(b'display_prerequisites=prerequisite_identity(),source_inputs=sources,',
                          b'display_kms_contract=kms_identity(),display_prerequisites=prerequisite_identity(),source_inputs=sources,')
_source = _source.replace(b"'stock-candidate-build-v1-20260906-01'",
                          b"'stock-candidate-build-v1-20260907-01'")
_tree = ast.parse(_source)
_tree.body = [n for n in _tree.body if not (isinstance(n, ast.If) and '__name__' in ast.unparse(n.test))]
exec(compile(ast.fix_missing_locations(_tree), str(P351_TEMPLATE) + '#p353', 'exec'), globals())

import s22plus_fyg8_display_kms_contract_h0 as kms

KMS_CONTRACT = ROOT / 'workspace/private/outputs/s22plus_fyg8_p352/h0-work/kms-contract.json'
KMS_SHA = '05a2a739cbbd6d53cb27abf043b64ecd6bd7bd4653b6e9834a0fe846d2ad7cff'


def qualified_kms_contract():
    raw = stable(KMS_CONTRACT)
    if hashlib.sha256(raw).hexdigest() != KMS_SHA:
        raise AuditError('P353 source-derived KMS qualification differs')
    result = json.loads(raw)
    if result['extractor'] != identity(stable(Path(kms.__file__))) or result['fixture'] != identity(stable(kms.FIXTURE)):
        raise AuditError('P353 KMS producer/fixture changed')
    if result['selected'] != kms.SELECTED or result['driver_name'] != 'msm_drm':
        raise AuditError('P353 KMS selection changed')
    for group in ('inputs', 'tools'):
        for path, expected in result[group].items():
            if identity((ROOT / path).read_bytes()) != expected:
                raise AuditError('P353 KMS source/tool changed: ' + path)
    for path in (kms.prerequisite.fixed.DEFAULT_DTBO, kms.prerequisite.fixed.DEFAULT_VENDOR_DTB):
        kms.prerequisite.fixed.require_sha((ROOT / path).read_bytes(), kms.prerequisite.fixed.p225.INPUT_PINS[path], 'KMS stock DT')
    return result


def kms_identity():
    qualified_kms_contract()
    return identity(stable(KMS_CONTRACT))

_p353_source_files = source_files

def source_files():
    result = _p353_source_files()
    paths = [P351_TEMPLATE, NATIVE / 's22plus_native_display_diagnostic_v3.inc.c', kms.FIXTURE]
    for stem in ('artifact_identity', 'research_shell_runtime', 'research_shell_observer', 'stock_process_v2_adapter'):
        paths.append(ROOT / 'workspace/public/src/scripts/revalidation' / ('s22plus_fyg8_p351_' + stem + '.py'))
    for path in paths:
        result[str(path.relative_to(ROOT))] = path
    return result


_p353_audit_existing = audit_existing


def audit_existing(output_root=DEFAULT_OUTPUT_ROOT):
    result = _p353_audit_existing(output_root)
    if result.get('display_kms_contract') != kms_identity():
        raise AuditError('P353 KMS build join differs')
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument('--audit-only', action='store_true')
    args = parser.parse_args()
    result = build_result(args.out, audit_only=args.audit_only)
    print(json.dumps({'verdict': result['verdict'], 'ap': result['candidate']['a']['ap_tar_md5']}, sort_keys=True))
