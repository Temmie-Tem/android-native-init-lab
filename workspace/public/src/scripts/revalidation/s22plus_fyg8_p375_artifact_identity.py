"""P375 boot-only artifact binding for the attended root console."""
from s22plus_fyg8_p375_namespace import load
load(globals())

# Final value is computed by the existing exact Image transform, before build.
# No device consumer accepts a predecessor digest for P375.
_p375_base_identity=validate_p375_identity

def validate_p375_identity():
    value=_p375_base_identity()
    for key in ('normal_middle_command_readonly','fixed_display_once_child',
                'initial_session_count','same_fd_session_count','total_session_count',
                'total_command_count','idle_seconds','initial_reconnect_count'):
        value.pop(key,None)
    value.update(arbitrary_root_shell=True,read_only_child_required=False,
        fixed_display_once_child=False,root_console=True,console_sessions=1,
        same_boot_repeated_commands=True,console_reentry=False,live_authorized=False)
    return value
