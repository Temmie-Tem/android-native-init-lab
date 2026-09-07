"""Fixed P363 stock return modules and authenticated control declaration (H0)."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[5]
MODULE_ROOT = ROOT / 'workspace/private/outputs/s22plus_fyg8_p362/followup/modules'
# name, exact byte size, SHA256, fixed finit_module parameters; insertion order.
MODULES = (('nvmem_qcom-spmi-sdam.ko', 15352, '211a627ab5768382b2eb32ccb4ee51356969b83bbe9357b323dca0b917e5a156', ''), ('sec_reboot_cmd.ko', 35368, '560b05535402808d0921725021c4da2124443b0ada729a49c24abea2a1b76f95', ''), ('sec_qc_rbcmd.ko', 43840, '2e549ffe439378732c1a69e0f118a043c1e335908f163fa246e94715eb0ddbcd', ''), ('qcom-dload-mode.ko', 28360, '20b209f284202bac177017bc7b46b9730c7d0f063666adb277667b5340163be8', 'download_mode=0'), ('sec_qc_qcom_reboot_reason.ko', 28640, '873bcd3141e296c68a2f4d1d2a1930509dd408878e5b495ac007a67316e91f30', ''))
FRAME_CONTROL = 6
FRAME_CONTROL_READY = 0x89
FRAME_CONTROL_ACK = 0x8a
CONTROL_SEQUENCE = 5
CONTROL_BODY = bytes((1, 0, 0, 0))
READY_BODY = bytes((1, 10, 1, 0))
ACK_BODY = bytes((1, 0, 10, 0))
DOMAIN_CONTROL = b'S22PLUS-FYG8-P363-CONTROL-v1'
DOMAIN_READY = b'S22PLUS-FYG8-P363-CONTROL-READY-v1'
DOMAIN_ACK = b'S22PLUS-FYG8-P363-CONTROL-ACK-v1'
BOOT_ID_SEMANTIC = 'kernel-uuid-lowercase-ascii36-sha256-v2'
BOOT_RECEIPT_SEMANTIC = 'sha256-of-boot-v2-wire-digest'


def module_bytes():
    result = {}
    for name, size, digest, params in MODULES:
        path = MODULE_ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('P363 nonregular module input')
        raw = path.read_bytes()
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('P363 stock module identity differs: ' + name)
        result[name] = raw
    return result

def render_module_table():
    lines = ['struct p363_return_module {const char *path; uint64_t size; const uint8_t hash[32]; const char *params;};',
             'static const struct p363_return_module p363_return_modules[] = {']
    for name, size, digest, params in MODULES:
        hash_bytes = ','.join('0x'+digest[i:i+2] for i in range(0,64,2))
        lines.append('    {"/s22-display-modules/%s",%dULL,{%s},"%s"},' % (name,size,hash_bytes,params))
    return ('\n'.join(lines + ['};']) + '\n').encode()
