"""P375 attended root console; H0 until new capability review and live grant."""
from s22plus_fyg8_p375_namespace import load
load(globals())

ROOT_CONSOLE_SOURCE=ROOT/'workspace/public/src/native-init/s22plus_root_console_v1.inc.c'
_root_base_build=build_helper


def build_helper(child=None):
    value=_root_base_build(child)
    for name in ('exec','close'):
        line=('static const char p328_auth_domain_'+name+'[] = "S22PLUS-FYG8-P328-AUTH-'+name.upper()+'-v1";\n').encode()
        value=_once(value,line,b'')
    # materialize_helper supplies the sealed production child explicitly;
    # only the small local C-join fixture still needs predecessor command
    # helpers so its inherited source adapter can be generated.
    if child is None or child!=fixture_child_source():
        value=_replace_function(value,b'static long p345_exec_command(',b'')
        value=_once(value,b'static void p375_handoff_tag(uint8_t *,const char *,const uint8_t *,uint32_t,const uint8_t *,size_t);\n',b'')
        value=_once(value,b'static long p375_handoff_write(int,uint8_t,uint32_t,const uint8_t *,size_t,const struct timespec64 *);\n',b'')
        for result,name in (
            (b'void',b'p328_store_le64'),(b'uint64_t',b'p328_elapsed_ms'),
            (b'long',b'p328_reap_after_kill'),
            (b'int',b'p345_command_valid'),(b'void',b'p345_report_child_setup_failure'),
            (b'long',b'p345_try_read_cancel'),(b'long',b'p345_write_cancel_ack'),
            (b'long',b'p345_enter_readonly_child'),(b'long',b'p328_cleanup_process_group'),
            (b'int',b'p345_cancel_tag_valid'),(b'long',b'p345_chroot'),
            (b'long',b'p345_chdir'),(b'long',b'p345_close_extra_fds'),
            (b'long',b'p345_setup_view'),(b'long',b'p345_drop_privileges'),
            (b'long',b'p345_apply_limits'),(b'long',b'p345_install_filter'),
            (b'long',b'p345_mkdir'),(b'long',b'p345_setrlimit'),
            (b'long',b'p345_fchmod'),(b'long',b'p345_write_exact'),
            (b'long',b'p345_prctl'),(b'long',b'p345_copy_text'),
            (b'long',b'p345_create_busybox_placeholder'),(b'long',b'p345_call'),
            (b'void',b'p375_control_tag'),(b'long',b'p375_wait_checkpoint'),
            (b'long',b'p375_sample_wait'),(b'void',b'p375_handoff_tag'),
            (b'long',b'p375_handoff_write'),
            (b'long',b'p375_status_reply'),(b'long',b'p375_handoff_status'),
            (b'void',b'p375_reset_request'),
            (b'long',b'p375_write_status'),(b'int',b'p375_swap_line'),
            (b'int',b'p375_wait_line'),(b'long',b'p375_note_wait'),
            (b'long',b'p375_diag_child_status'),
            (b'long',b'p375_child_output'),(b'long',b'p375_try_control')):
            value=_replace_function(value,b'static '+result+b' '+name+b'(',b'')
        filter_declaration=b'static struct p345_sock_filter p345_filter[] = {'
        filter_start=value.index(filter_declaration)
        filter_end=value.index(b'};\n',filter_start)+3
        value=value[:filter_start]+value[filter_end:]
        value=_once(value,b'static unsigned int p375_display_consumed;\n',b'')
    start=value.index(b'    uint32_t expected_sequence = 3U;',value.index(b'static long p345_framed_console('))
    end=value.index(b'\n\n\nstatic long p335_getrandom_boot_id',start)
    # Keep exact OPEN/AUTH/BOOT-v2 handshake. Then permanently consume this
    # boot's console; neither success nor failure returns to a listener.
    replacement=b'''    rc=p375_diag_start(tty_fd,nonce);
    if(rc==0)rc=p375_prepare_return();
    if(rc==0)rc=p375_diag_enter(60U);
    if(rc==0)rc=p375_diag_result(60U,
        (syscall6(174,0,0,0,0,0,0)==0 && syscall6(175,0,0,0,0,0,0)==0 &&
         syscall6(176,0,0,0,0,0,0)==0 && syscall6(177,0,0,0,0,0,0)==0)?0:-P260_EPROTO);
    if(rc==0)rc=p375_diag_enter(61U);
    if(rc==0)rc=p375_diag_result(61U,syscall6(34,-100,(long)(uintptr_t)"/s22-root-work",0700,0,0,0));
    if(rc==0)rc=p375_diag_enter(62U);
    if(rc==0)rc=p375_diag_result(62U,sys_mount("tmpfs","/s22-root-work","tmpfs",6UL,"size=64m,nr_inodes=4096,mode=0700"));
    if(rc!=0)p375_diag_finish(rc);
    if(rc==0)rc=rc1_console(tty_fd,nonce);
    if(rc==1) {
        p375_diagnostic.terminal=1;
        (void)syscall6(142,0xfee1deadUL,672274793UL,0xa1b2c3d4UL,
            (long)(uintptr_t)"download",0,0);
    }
    for(;;)p282_poll_delay();
}
'''
    value=value[:start]+replacement+value[end:]
    anchor=b'static long p345_framed_console('
    root_source=(b'#define RC1_RUN_ID_ASCII "'+P375_RUN_ID_HEX.encode()+b'"\n'
                 +ROOT_CONSOLE_SOURCE.read_bytes())
    value=_once(value,anchor,root_source+b'\n'+anchor)
    return value

P345_HELPER_TEMPLATE=P345_HELPER=build_helper()
P375_HELPER_TEMPLATE=P375_HELPER=P345_HELPER
_root_audit=audit_binding


def audit_binding(*,child=None):
    inherited=_root_audit(child=child)
    retained=('predecessor_source','predecessor_run_id','fresh_run_id','run_id_hex',
        'kernel_boot_id_semantic','kernel_boot_id_auth_domain','return_modules',
        'dump_mode_initialization','return_recovery','automatic_recovery_proved',
        'target_open_flag_abi','directory_open_flag','module_nofollow_flag')
    value={key:inherited[key] for key in retained}
    value.update(schema='s22plus-fyg8-p375-root-console-runtime-v1',
        contract_id='s22plus-fyg8-root-console-v1',root_console=True,
        console_source=identity(ROOT_CONSOLE_SOURCE.read_bytes()),
        command_privilege='numeric-root-trusted-operator',child_isolation=False,
        same_boot_repeated_exec=True,separate_stdout_stderr=True,
        command_timeout_max_ms=300000,native_session_ms=600000,
        command_output_limit=1048576,ram_workspace_bytes=67108864,
        control_independent_of_child=True,control_mode='download',
        control_owner='native-PID1-supervisor',control_syscall_maximum=1,
        control_ack_scope='acceptance-only',control_ack_write_failure='consume-without-syscall',
        control_replay_forbidden=True,console_reentry=False,pty=False,
        exec_error_channel='cloexec-pipe-no-error-observed-is-not-exec-proof',
        cancellation_scope='owned-process-group',unresolved_cleanup_blocks_exec=True,
        root_child_hostile_isolation_claimed=False,device_contact=False,live_authorized=False)
    return value
