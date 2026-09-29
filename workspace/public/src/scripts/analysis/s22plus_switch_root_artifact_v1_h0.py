"""Join A/B boot-only bytes, static witness and exact original-A return basis."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_native_root_inspect_artifact_v1_h0 as previous


def qualify(namespace,output,*,key_path,build_directory=None):
    return previous.qualify(namespace,output,key_path=key_path,build_directory=build_directory,switch_root=True)
