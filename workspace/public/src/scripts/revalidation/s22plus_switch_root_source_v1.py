"""Fixed actual-PID1 terminal transition over the retained native UFS startup."""
from pathlib import Path
import s22plus_native_root_inspect_source_v1 as previous
import s22plus_native_staged_preflight_source_v1 as checker_source

ROOT=previous.ROOT
PROFILE='thermal-v3-reconnect-ufs-drain-switch-root-v1'
SWITCH_ROOT_PROFILE=PROFILE


def __getattr__(name): return getattr(previous,name)


def upgrade_native(raw, identity):
    replace=previous.resident.replace
    raw=replace(raw,b'#define RC1_CONTROL 35U',
        b'#include "s22plus_switch_root_v1.h"\n#define RC1_CONTROL 35U')
    raw=replace(raw,b'    if(type==RC1_DETACH && !size) {',b'''    if(type==SW_REQUEST && !size) {
        if(seq!=SW_SEQUENCE || s->active || s->pid || s->blocked || s->qcount || s->overload ||
           s->fault_sent || s->flags || s->dropped || !baseline_detach_available() ||
           now<s->start || now-s->start>600000U-SW_TIMEOUT_MS)return -P260_EPROTO;
        s->blocked=1;s->control=4;s->control_seq=seq;s->control_start=now;
        return rc1_reply_state(s,SW_ACCEPTED,seq,0U);
    }
    if(type==RC1_DETACH && !size) {''')
    raw=replace(raw,b'    if(s->control==3)return 0;',b'    if(s->control==3 || s->control==4)return 0;')
    include=(ROOT/'workspace/public/src/native-init/s22plus_switch_root_parent_v1.inc.c').read_bytes()
    include=include.replace(b'@@NAMESPACE@@',identity.namespace.encode())
    raw=replace(raw,b'static long rc1_console(int fd,const uint8_t nonce[32]) {',
        include+b'\nstatic long rc1_console(int fd,const uint8_t nonce[32]) {')
    raw=replace(raw,b'        if(s.control==3 && !s.qcount)',
        b'        if(s.control==4 && !s.qcount)sw_parent_exec(&s);\n        if(s.control==3 && !s.qcount)')
    return raw


def helper_template(identity): return upgrade_native(previous.helper_template(identity),identity)


def materialize_helper(identity,key): return upgrade_native(previous.materialize_helper(identity,key),identity)


def profile_contract():
    return dict(previous.profile_contract(),switch_root_profile=PROFILE,
        switch_root=dict(request=37,sequence=5,seconds=300,owner_pid=1,root_readonly=True,
            installed_exec=False,terminal_reentry=False,return_request=38,return_sequence=6))


def source_files():
    native=ROOT/'workspace/public/src/native-init'
    return tuple(sorted(set(checker_source.source_files())|{Path(__file__),
        *(native/name for name in ('s22plus_switch_root_v1.h','s22plus_switch_root_v1.c',
            's22plus_switch_root_parent_v1.inc.c','s22plus_switch_root_common_v1.inc.c',
            's22plus_switch_root_witness_v1.c'))}))
