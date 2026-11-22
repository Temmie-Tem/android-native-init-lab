"""Stage the MAX77705 USB-switch observer profile from the packaged Debian RAM observer.

Same pattern as scm_usb_h0.py: derive init.c / protocol.h / verifier from the
reviewed Debian RAM base, append a fixed 616-byte MAX77705 record to the signed
body (352 -> 968 bytes), and give the profile its own wire domain and magics.
The VM profile and the board profile use different domains, so a VM response
can never verify as a board observation.
"""
from pathlib import Path
import shutil

import max77705_record

HERE = Path(__file__).resolve().parent
BODY = 352 + max77705_record.SIZE


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('Unexpected base source around ' + before[:64])
    return text.replace(before, after)


def stage_sources(output, *, board=False):
    output = Path(output)
    output.mkdir(mode=0o700)
    if board:
        schema, domain, prefix = 's22plus-fyg8-debian-max77705-usb-v1', 'G0Q-FYG8-DEBIAN-MAX77705-USB-v1', 'G0QU'
    else:
        schema, domain, prefix = 's22plus-debian-max77705-usb-h0-v1', 'G0Q-MAX77705-USB-H0-v1', 'G0QM'
    request, response = prefix + 'RQ1', prefix + 'RS1'

    source = (HERE / 'init.c').read_text()
    mode_guard = ('#ifdef CANARY_H0_VM\n#error "board MAX77705 profile built with the VM flag"\n#endif\n' if board else
                  '#ifndef CANARY_H0_VM\n#error "H0 MAX77705 profile requires the VM flag"\n#endif\n')
    source = mode_guard + source
    source = replace_once(source, 'static int proof(', '#include "max77705-usb-observe.h"\nstatic int proof(')
    source = replace_once(source, '    g_tag(response+G0Q_BODY_SIZE,',
                          '    mx_fill(response+352);\n    g_tag(response+G0Q_BODY_SIZE,')
    # Sample from boot: first reads before USB setup, then while waiting for the request.
    source = replace_once(source, '    dprintf(2,"G0Q_RAM_PID1_BEGIN\\n");\n',
                          '    dprintf(2,"G0Q_RAM_PID1_BEGIN\\n");\n    mx_begin();\n')
    source = replace_once(
        source,
        '        struct pollfd p={fd,POLLIN,0};int rc=poll(&p,1,(int)(deadline-now));\n'
        '        if(rc<0) {if(errno==EINTR)continue;error=errno;break;}\n'
        '        if(!rc) {error=ETIMEDOUT;break;}\n',
        '        struct pollfd p={fd,POLLIN,0};uint64_t wait=deadline-now;if(wait>MX_TICK_MS)wait=MX_TICK_MS;\n'
        '        int rc=poll(&p,1,(int)wait);\n'
        '        if(rc<0) {if(errno==EINTR)continue;error=errno;break;}\n'
        '        if(!rc) {mx_tick();continue;}\n')
    # Like the SCM profile, exercise the target USB gadget path in the VM too.
    source = replace_once(source, '#ifdef CANARY_H0_VM\n    int e=network("eth0");\n#else\n'
                          '    int e=usb();\n#endif', '    int e=usb();')
    (output / 'init.c').write_text(source)
    shutil.copy2(HERE / 'max77705-usb-observe.h', output / 'max77705-usb-observe.h')
    shutil.copy2(HERE / 'max77705_record.py', output / 'max77705_record.py')

    protocol = (HERE / 'protocol.h').read_text()
    protocol = replace_once(protocol, '#elif defined(CANARY_DEBIAN_RAM)\n#define G0Q_BODY_SIZE 352U',
                            f'#elif defined(CANARY_DEBIAN_RAM)\n#define G0Q_BODY_SIZE {BODY}U')
    for old, new in [('G0QDRQ1', request), ('G0QDRS1', response), ('G0Q-DEBIAN-SYSVINIT-RAM-v1', domain)]:
        protocol = replace_once(protocol, old, new)
    protocol = replace_once(protocol, '../../native-init/s22plus_fyg8_max77705_result_parser.inc.c',
                            's22plus_fyg8_max77705_result_parser.inc.c')
    protocol = protocol.replace('#define G0Q_RESPONSE_SIZE',
                                f'_Static_assert({BODY}U == 352U + {max77705_record.SIZE}U, "record size");\n'
                                '#define G0Q_RESPONSE_SIZE', 1)
    (output / 'protocol.h').write_text(protocol)

    verifier = (HERE / 'verify.py').read_text()
    start, end = verifier.index('def protocol('), verifier.index('def response_size(')
    verifier = verifier[:start] + (
        'def protocol(manifest=None):\n'
        f'    require(manifest and manifest.get("debian_ram", {{}}).get("schema") == {schema!r},\n'
        '            "incorrect MAX77705 observation schema")\n'
        f'    return {domain.encode()!r}, {request.encode() + bytes(1)!r}, '
        f'{response.encode() + bytes(1)!r}, {BODY}\n\n\n'
    ) + verifier[end:]
    mode_check = ("    require(vm is False, 'board capture required')\n" if board else
                  "    require(vm is True, 'MAX77705 H0 decoder is VM-only')\n")
    verifier = replace_once(verifier, "    require(manifest['vm'] is vm,",
                            mode_check + "    require(manifest['vm'] is vm,")
    if board:
        # Board decoding accepts only a sealed raw capture and the exact loader-handed FDT.
        start, end = verifier.index('def verify(raw_path,'), verifier.index('def verify_capture(')
        verifier = verifier[:start] + verifier[end:]
        verifier = replace_once(verifier, 'def verify_capture(handle,manifest,nonce):',
                                'def verify_capture(handle,manifest,nonce,*,expected_loader_fdt_sha256):')
        verifier = replace_once(
            verifier, '    return _verify(raw,manifest,nonce,vm=False,directory=handle.receipt_path.parent)',
            '    result = _verify(raw,manifest,nonce,vm=False,directory=handle.receipt_path.parent)\n'
            '    require(result["live_fdt_sha256"] == expected_loader_fdt_sha256,\n'
            '            "live FDT differs from qualified loader output")\n'
            '    return result')
    verifier = replace_once(
        verifier, '    extra={}\n',
        # The record decoder is embedded so a host that loads this file from
        # pinned bytes (exec, no __file__) needs no second, unpinned read.
        '    _r = {"__name__": "max77705_record"}\n'
        '    exec(compile(_MAX77705_RECORD_SOURCE, "<embedded max77705_record>", "exec"), _r)\n'
        f'    _decoded = _r["decode"](body[352:{BODY}])\n'
        "    extra = {'max77705': _decoded, 'max77705_verdict': _r['verdict'](_decoded), 'subject': 'max77705'}\n")
    record_source = (HERE / 'max77705_record.py').read_text()
    verifier = replace_once(verifier, 'def protocol(manifest=None):',
                            f'_MAX77705_RECORD_SOURCE = {record_source!r}\n\n\ndef protocol(manifest=None):')
    verifier = replace_once(verifier, "'PASS_H0_VM_DEBIAN_SYSVINIT_RAM'", "'AUTHENTICATED_H0_MAX77705_USB_OBSERVATION'")
    if board:
        verifier = replace_once(verifier, "'AUTHENTICATED_DEBIAN_SYSVINIT_RAM_OBSERVATION'",
                                "'AUTHENTICATED_MAX77705_USB_TRANSCRIPT'")
    (output / 'max77705_verify.py').write_text(verifier)
    return schema
