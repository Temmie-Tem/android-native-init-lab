"""Build P385 through the shared direct native packager; no device actions."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'workspace/public/src/scripts/revalidation')]
import s22plus_fyg8_p385_candidate as candidate
import s22plus_fyg8_p384_stock_candidate_build as packager

DEFAULT_OUTPUT_ROOT = ROOT/'workspace/private/outputs/s22plus-fyg8-v0.2.0-rc.3/candidate-build-verified-v2'
SCHEMA = 's22plus-fyg8-p385-stock-candidate-build-v1'
VERDICT = 'PASS_P385_STOCK_CANDIDATE_BUILD_H0'
TARGET = dict(packager.TARGET)
REFERENCE, REFERENCE_RESULT, REFERENCE_IDENTITY = packager.REFERENCE, packager.REFERENCE_RESULT, packager.REFERENCE_IDENTITY
write, canonical = packager.write, packager.canonical


def source_receipts(): return packager.source_receipts(candidate)
def join_runtime(raw): return packager.join_runtime(raw, candidate)
def audit_existing(output_root=DEFAULT_OUTPUT_ROOT):
    return packager.audit_existing(output_root, candidate=candidate)
def build_result(output_root=DEFAULT_OUTPUT_ROOT, *, audit_only=False):
    return packager.build_result(output_root, audit_only=audit_only, candidate=candidate)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument('--audit-only', action='store_true')
    args = parser.parse_args()
    result = build_result(args.out, audit_only=args.audit_only)
    print(json.dumps(dict(verdict=result['verdict'], ap=result['candidate']['a']['ap_tar_md5']), sort_keys=True))
