"""v0.1.2-rc.3 observed model binding and optional native memory snapshots."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p380_namespace import load_predecessor
load_predecessor(globals())

DEFAULT_OUTPUT_ROOT=ROOT/'workspace/private/outputs/s22plus-fyg8-v0.1.2-rc.3/candidate-build-final'
_model_build=build_result
_model_audit=audit_existing


def build_result(output_root=DEFAULT_OUTPUT_ROOT,*,audit_only=False):
    return _model_build(output_root,audit_only=audit_only)


def audit_existing(output_root=DEFAULT_OUTPUT_ROOT):
    return _model_audit(output_root)


TELEMETRY_ROOT=ROOT/'workspace/private/outputs/s22plus-telemetry-provider-qualified-v6-model'
TELEMETRY_IDENTITY={'size':304408,'sha256':'0026fcb72d95f787456f44d131e31170c292fe3a9c19665ca691ffec2ee2ba0c'}


def telemetry_qualification():
    receipt=json.loads(stable(TELEMETRY_ROOT/'result.json',{'size':3934,'sha256':'5a0d2ee71d16e37368fdf8ab61b9ccd1e59c83512708aa6f1c9ff038775ecfe4'}))
    if receipt['module']!=TELEMETRY_IDENTITY or not receipt['ab_identical']:
        raise AuditError('exact-model telemetry qualification differs')
    for relative,pin in receipt['source_inputs'].items():stable(ROOT/relative,pin)
    return receipt


_model_sources=source_files


def source_files():
    from s22plus_fyg8_p380_namespace import P379_SOURCES
    result=dict(_model_sources())
    paths=[ROOT/relative for relative,_ in P379_SOURCES.values()]
    paths+=list((ROOT/'workspace/public/src/kernel-modules/s22plus_max77705_telemetry_v3').iterdir())
    paths+=[ROOT/'workspace/public/src/scripts/analysis/s22plus_fyg8_telemetry_provider_h0_v3.py']
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
