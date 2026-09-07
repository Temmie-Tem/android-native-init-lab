"""P365 corrected ARM64 successor; no device authority."""
from s22plus_fyg8_p365_namespace import load
load(globals())

FLAG_SOURCE=ROOT/'workspace/public/src/native-init/s22plus_arm64_open_flags_v1.h'
_flag_base_exec=_exec_function

def _exec_function(value):
    value=_flag_base_exec(value).replace(b'p364',b'p365').replace(b'P364',b'P365')
    value=_once(value,b'sys_openat(module->path,O_RDONLY|O_CLOEXEC|0400000,0)',
        b'sys_openat(module->path,O_RDONLY|O_CLOEXEC|S22_ARM64_O_NOFOLLOW,0)')
    value=_once(value,b'sys_openat("/sys/bus/nvmem/devices",O_RDONLY|O_CLOEXEC|0200000,0)',
        b'sys_openat("/sys/bus/nvmem/devices",O_RDONLY|O_CLOEXEC|S22_ARM64_O_DIRECTORY,0)')
    return FLAG_SOURCE.read_bytes()+b'\n'+value

P345_HELPER_TEMPLATE=P345_HELPER=build_helper()
P365_HELPER_TEMPLATE=P365_HELPER=P345_HELPER_TEMPLATE
_flag_base_audit=audit_binding

def audit_binding(*,child=None):
    value=_flag_base_audit(child=child)
    value.update(target_open_flag_abi='linux-arm64',
        directory_open_flag=0o40000,module_nofollow_flag=0o100000)
    return value
