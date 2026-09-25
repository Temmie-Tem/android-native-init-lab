"""Measured bootstrap followed by adoption of its settled module state."""
from pathlib import Path
import s22plus_native_output_drain_source_v1 as previous
import s22plus_native_ufs_source_v1 as ufs

ROOT = previous.ROOT
DEVICE = ROOT/'workspace/public/src/debian/s22plus_v1/device'
PREFLIGHT_PROFILE = 'thermal-v3-reconnect-ufs-drain-prehandoff-v1'


def __getattr__(name):
    return getattr(previous,name)


def profile_contract():
    return dict(previous.profile_contract(), preflight_profile=PREFLIGHT_PROFILE,
        measured_module_order='P405-81', observer_modules='adopt-exact-loaded-set',
        module_checkpoint_semantic='adopted-availability-only', temporal_module_witness='not-applicable',
        protected_root=True, persistent_writes=False, pid1_handoff=False,
        result_transport='sealed-memfd-198-current-boot')


def source_files():
    names=('preflight_record.h','preflight_gate.inc.c','preflight_read.c','preflight.inc.c','target.inc.c')
    return tuple(sorted(set(previous.source_files())|{Path(__file__),*(DEVICE/name for name in names),
        DEVICE.parent/'handoff.c'}))


def native_sources(rows):
    rows=dict(rows); filename='s22plus_fyg8_p290_e3_runtime.c'; raw=rows[filename]
    replace,section=previous.resident.replace,previous.resident.section
    raw=replace(raw,b'static long p241_verify_module_prefix(size_t count) {',
        b'#include "preflight_gate.inc.c"\n\nstatic long p241_verify_module_prefix(size_t ignored) {\n'
        b'    (void)ignored; const size_t count = BP_MODULE_COUNT;\n'
        b'    _Static_assert(S22PLUS_O2_MODULE_PLAN_COUNT + 8 == BP_MODULE_COUNT, "adopted module set");')
    raw=replace(raw,b'const char *names[S22PLUS_O2_MODULE_PLAN_COUNT];',b'const char *names[BP_MODULE_COUNT];')
    raw=replace(raw,b'unsigned char found[S22PLUS_O2_MODULE_PLAN_COUNT];',b'unsigned char found[BP_MODULE_COUNT];')
    raw=replace(raw,b'for (size_t index = 0; index < count; ++index) {\n        names[index] = s22plus_o2_module_plan[index].runtime_name;\n    }',
        b'for (size_t index = 0; index < S22PLUS_O2_MODULE_PLAN_COUNT; ++index) {\n'
        b'        names[index] = s22plus_o2_module_plan[index].runtime_name;\n    }\n'+
        b''.join(f'    names[S22PLUS_O2_MODULE_PLAN_COUNT+{i}]="{name}";\n'.encode()
            for i,(_,name,_,_) in enumerate(ufs.MODULES)))
    raw=section(raw,b'static long p241_load_and_verify_module(size_t index) {',b'static int p241_basename_equals(',
        b'static long p241_load_and_verify_module(size_t index) {\n'
        b'    if (index >= S22PLUS_O2_MODULE_PLAN_COUNT || bp_native_record.modules_completed != BP_MODULE_COUNT) return -71;\n'
        b'    return p241_verify_module_prefix(BP_MODULE_COUNT);\n}\n\n')
    raw=replace(raw,b'        long p319_post_load_rc = p319_after_module_load(index, 0L);\n        if (p319_post_load_rc != 0) p290_fail_next(p319_post_load_rc);\n',b'')
    start=b'        long p319_post_load_rc = p319_after_module_load(index, p305_folded_load_rc);'
    end=b'    long p305_checkpoint_rc = s22_r4w1e_checkpoint_progress('
    raw=section(raw,start,end,b'        /* Temporal insertion/provider witnesses do not apply to adoption. */\n    }\n')
    raw=replace(raw,b'__attribute__((noreturn)) void _start(void) {\n',
        b'__attribute__((noreturn)) void _start(void) {\n    bp_native_enter(k_run_id, 0);\n')
    raw=replace(raw,b'    E1_REQUIRE(S22_R4W1E_STAGE_PROC_MOUNTED, 0U, mount_proc());',
        b'    E1_REQUIRE(S22_R4W1E_STAGE_PROC_MOUNTED, 0U, mount_proc());\n'
        b'    if (bp_native_boot() != 0) quiet_park();')
    rows[filename]=raw
    # These retained helpers only supplied the retired temporal witness. Mark
    # their unreferenced roots explicitly; do not call them with invented events.
    rows[filename]=replace(rows[filename],b'static long p319_after_module_load(',
        b'static __attribute__((unused)) long p319_after_module_load(')
    helper='s22plus_fyg8_p290_e3_runtime.inc.c'
    for old,new in ((b'static long p317_capture_preclient_provider(',
                    b'static __attribute__((unused)) long p317_capture_preclient_provider('),
                   (b'static __attribute__((noreturn)) void p317_fail_observer(',
                    b'static __attribute__((noreturn,unused)) void p317_fail_observer('),
                   (b'static __attribute__((noreturn)) void p317_fail_precondition(',
                    b'static __attribute__((noreturn,unused)) void p317_fail_precondition(')):
        rows[helper]=replace(rows[helper],old,new)
    for name in ('preflight_record.h','preflight_gate.inc.c'):rows[name]=(DEVICE/name).read_bytes()
    return rows


def render_display(identity,modules):
    raw=previous.render_display(identity,modules)
    old=ufs.loader_source()
    run=','.join(map(str,bytes.fromhex(identity.run_id_hex)))
    names=','.join('"/sys/module/'+name+'"' for _,name,_,_ in ufs.MODULES)
    adopted=(DEVICE/'preflight_record.h').read_bytes()+f'''
static void ufs1_prepare(void) {{
    static const unsigned char run[16]={{{run}}};
    static const char *const modules[]={{{names}}};
    int fd=open("/proc/1/fd/198",O_RDONLY|O_CLOEXEC);
    struct stat st; struct bp_record record;
    require(fd>=0 && !fstat(fd,&st) && S_ISREG(st.st_mode) && !st.st_uid && !st.st_gid &&
        !st.st_nlink && (st.st_mode&07777)==0400 && fcntl(fd,1034)==BP_SEALS &&
        pread(fd,&record,sizeof(record),0)==sizeof(record) && bp_valid(&record,run,0) &&
        st.st_size==(off_t)(sizeof(record)+record.log_size),"preflight-sealed-proof");
    if(close(fd)) fail("preflight-proof-close");
    for(unsigned i=0;i<8;++i) {{
        require(!lstat(modules[i],&st) && S_ISDIR(st.st_mode),"preflight-ufs-adoption");
    }}
    /* Measured insertion occurred before this observer and renderer existed. */
}}
'''.encode()
    return previous.resident.replace(raw,old,adopted)
