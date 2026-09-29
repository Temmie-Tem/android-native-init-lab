"""One native terminal followed by the fixed installed-Debian extension."""
from pathlib import Path
import s22plus_switch_root_source_v1 as previous
from s22plus_debian_handoff_profile_v1 import PROFILE

ROOT=previous.ROOT
DEBIAN_HANDOFF_PROFILE=PROFILE
SWITCH_ROOT_PROFILE=None


def __getattr__(name):return getattr(previous,name)


def profile_contract():
    result=previous.profile_contract()
    result['switch_root_profile']=None
    result.update(debian_handoff_profile=PROFILE,switch_root=dict(request=37,sequence=5,seconds=300,
        owner_pid=1,root_readonly=False,installed_exec=True,terminal_reentry=False,
        init_request=39,init_sequence=6,release_request=40,release_sequence=7))
    return result


def source_files():
    native=ROOT/'workspace/public/src/native-init'
    return tuple(sorted(set(previous.source_files())|{Path(__file__),
        *(native/n for n in ('s22plus_debian_handoff_v1.h','s22plus_debian_handoff_common_v1.inc.c',
            's22plus_debian_handoff_prepare_v1.inc.c','s22plus_debian_handoff_witness_v1.inc.c',
            's22plus_debian_handoff_hook_v1.c'))}))
