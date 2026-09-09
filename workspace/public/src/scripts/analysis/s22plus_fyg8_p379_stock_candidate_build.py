"""v0.1.2-rc.2 bounded gauge failure diagnostics; fresh candidate."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p379_namespace import load_predecessor
load_predecessor(globals())

DEFAULT_OUTPUT_ROOT=ROOT/'workspace/private/outputs/s22plus-fyg8-v0.1.2-rc.2/candidate-build-final2'
_diagnostic_build=build_result
_diagnostic_audit=audit_existing

def build_result(output_root=DEFAULT_OUTPUT_ROOT,*,audit_only=False):
    return _diagnostic_build(output_root,audit_only=audit_only)

def audit_existing(output_root=DEFAULT_OUTPUT_ROOT):
    return _diagnostic_audit(output_root)

TELEMETRY_ROOT=ROOT/'workspace/private/outputs/s22plus-telemetry-provider-qualified-v5-diagnostic'
TELEMETRY_IDENTITY={'sha256': '329e3ac99a1febff226d66ee3bd940f0b8629c537b6eb910ee182f78c6ff293a', 'size': 304648}

def telemetry_qualification():
    receipt=json.loads(stable(TELEMETRY_ROOT/'result.json',{'size': 3939, 'sha256': 'b23dba371173159cbf56c754a5fde88a9cb7912dfcf4e97570876421bc57b593'}))
    if receipt['module']!=TELEMETRY_IDENTITY or not receipt['ab_identical']:
        raise AuditError('diagnostic telemetry qualification differs')
    for relative,pin in receipt['source_inputs'].items():stable(ROOT/relative,pin)
    return receipt

_diagnostic_sources=source_files

def source_files():
    from s22plus_fyg8_p379_namespace import P378_SOURCES
    result=dict(_diagnostic_sources())
    paths=[ROOT/relative for relative,_ in P378_SOURCES.values()]
    paths += [ROOT/'workspace/public/src/native-init'/name for name in
        ('s22plus_gauge_sample_v2.inc.c','s22plus_gauge_diagnostics_v1.inc.c','s22plus_status_metrics_v3.inc.c')]
    paths += list((ROOT/'workspace/public/src/kernel-modules/s22plus_max77705_telemetry_v2').iterdir())
    paths += [ROOT/'workspace/public/src/scripts/analysis/s22plus_fyg8_telemetry_provider_h0_v2.py']
    for path in paths:
        if path.is_file():result[str(path.relative_to(ROOT))]=path
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument('--audit-only',action='store_true')
    args=parser.parse_args()
    result=build_result(args.out,audit_only=args.audit_only)
    print(json.dumps({'verdict':result['verdict'],'ap':result['candidate']['a']['ap_tar_md5']},sort_keys=True))
