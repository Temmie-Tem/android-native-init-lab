"""Derive the isolated SCM USB H0 producer and verifier from the packaged Debian RAM profile."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATUS = ('indeterminate', 'unbound', 'bound')


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('Unexpected base source around ' + before[:64])
    return text.replace(before, after)


def stage_sources(output, *, lifecycle_model=False):
    """Write fresh offline sources. The VM observer uses NCM and keeps its VM evidence flag."""
    output = Path(output)
    output.mkdir(mode=0o700)
    subject = 'platform-model' if lifecycle_model else 'scm'
    schema = 's22plus-debian-scm-usb-h0-v1-' + subject
    domain = 'G0Q-SCM-USB-H0-v1-' + subject
    prefix = 'G0QT' if lifecycle_model else 'G0QO'
    request, response = prefix + 'RQ1', prefix + 'RS1'

    source = (HERE / 'init.c').read_text()
    source = replace_once(source, 'static int proof(', '#include "scm-usb-observe.h"\nstatic int proof(')
    source = replace_once(source, '    g_tag(response+G0Q_BODY_SIZE,',
                          '    g_put32(response+352,scm_observe());\n    g_tag(response+G0Q_BODY_SIZE,')
    # The legacy VM profile uses virtio-net. Exercise the target USB gadget setup in this VM.
    source = replace_once(source, '#ifdef CANARY_H0_VM\n    int e=network("eth0");\n#else\n'
                          '    int e=usb();\n#endif', '    int e=usb();')
    subject_guard = ('#ifdef SCM_USB_LIFECYCLE_MODEL\n'
                     '#error "Select the SCM observation subject when staging sources"\n'
                     '#endif\n')
    if lifecycle_model:
        subject_guard += '#define SCM_USB_LIFECYCLE_MODEL\n'
    source = subject_guard + source
    (output / 'init.c').write_text(source)
    (output / 'scm-usb-observe.h').write_bytes((HERE / 'scm-usb-observe.h').read_bytes())

    protocol = (HERE / 'protocol.h').read_text()
    protocol = replace_once(protocol, '#elif defined(CANARY_DEBIAN_RAM)\n#define G0Q_BODY_SIZE 352U',
                            '#elif defined(CANARY_DEBIAN_RAM)\n#define G0Q_BODY_SIZE 356U')
    for old, new in [('G0QDRQ1', request), ('G0QDRS1', response),
                     ('G0Q-DEBIAN-SYSVINIT-RAM-v1', domain)]:
        protocol = replace_once(protocol, old, new)
    protocol = replace_once(protocol, '../../native-init/s22plus_fyg8_max77705_result_parser.inc.c',
                            's22plus_fyg8_max77705_result_parser.inc.c')
    (output / 'protocol.h').write_text(protocol)

    verifier = (HERE / 'verify.py').read_text()
    start, end = verifier.index('def protocol('), verifier.index('def response_size(')
    verifier = verifier[:start] + (
        'def protocol(manifest=None):\n'
        f'    require(manifest and manifest.get("debian_ram", {{}}).get("schema") == {schema!r},\n'
        '            "incorrect SCM observation schema")\n'
        f'    return {domain.encode()!r}, {request.encode()+bytes(1)!r}, '
        f'{response.encode()+bytes(1)!r}, 356\n\n\n'
    ) + verifier[end:]
    verifier = replace_once(verifier, "    require(manifest['vm'] is vm,",
                            "    require(vm is True, 'SCM decoder is qualified only for H0')\n"
                            "    require(manifest['vm'] is vm,")
    verifier = replace_once(verifier, '    extra={}\n',
                            "    readout, = struct.unpack_from('<I', body, 352)\n"
                            f"    states = {STATUS!r}\n"
                            "    require(readout < len(states), 'unknown SCM binding value')\n"
                            f"    extra = {{'scm_binding': states[readout], 'subject': {subject!r}}}\n")
    verifier = replace_once(verifier, "'PASS_H0_VM_DEBIAN_SYSVINIT_RAM'",
                            "'AUTHENTICATED_H0_SCM_USB_OBSERVATION'")
    (output / 'scm_verify.py').write_text(verifier)
    return schema
