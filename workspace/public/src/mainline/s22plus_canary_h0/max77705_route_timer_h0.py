"""Stage the MAX77705 route observer with the ML050 automatic Download timer (H0).

The producer is the reviewed Stage 2 route observer, staged unchanged by
max77705_route_h0.stage_sources(). This wrapper changes three things only:
1. the wire identity (schema, domain, request/response magics), so a record
   from this profile can never verify as an attended Stage 2 route record
   and vice versa;
2. the ML050 timer composition (build_initramfs.py udc_timer_return): PID1
   arms the independent recovery child before anything else, then closes its
   IPC end. The child alone owns one ordinary RESTART2("download") at guest
   BOOTTIME 555 s, never at or after 570 s. No early commit is reachable;
   the wire protocol still has no Download command;
3. download-return.h (for download_ready) and recovery.h are compiled in
   with G0Q_AUTOMATIC_RECOVERY; build with -I <ufs_link_h0>.

If arming fails, PID1 parks before USB setup, so no authenticated response
exists. An authenticated response therefore implies the child was armed.
"""
from pathlib import Path

import max77705_route_h0

HERE = Path(__file__).resolve().parent
TIMER_INCLUDE_DIR = HERE.parent / 's22plus_ufs_link_h0'
BOARD = ('s22plus-fyg8-debian-max77705-route-timer-v1', 'G0Q-FYG8-DEBIAN-MAX77705-ROUTE-TIMER-v1', 'G0QX')
VM = ('s22plus-debian-max77705-route-timer-h0-v1', 'G0Q-MAX77705-ROUTE-TIMER-H0-v1', 'G0QY')
ROUTE_BOARD = ('s22plus-fyg8-debian-max77705-route-v1', 'G0Q-FYG8-DEBIAN-MAX77705-ROUTE-v1', 'G0QR')
ROUTE_VM = ('s22plus-debian-max77705-route-h0-v1', 'G0Q-MAX77705-ROUTE-H0-v1', 'G0QW')
INCLUDE = '#ifdef CANARY_DOWNLOAD_RAM\n#include "download-return.h"\n#endif'
BEGIN = '    dprintf(2,"G0Q_RAM_PID1_BEGIN\\n");'
ARM = ('    { int armed = recovery_begin(); if (armed) park(armed); }\n'
       '    close(recovery_fd); recovery_fd = -1;\n')

replace_once = max77705_route_h0.replace_once


def _rename(text, old, new):
    """Replace each identity string; every staged occurrence must change."""
    for before, after in zip(old, new):
        text = text.replace(before, after)
    for before in old:
        if before in text:
            raise ValueError('route identity survived renaming: ' + before)
    return text


def stage_sources(output, *, board=False):
    output = Path(output)
    route_schema = max77705_route_h0.stage_sources(output, board=board)
    old, new = (ROUTE_BOARD, BOARD) if board else (ROUTE_VM, VM)
    if route_schema != old[0]:
        raise ValueError('unexpected route schema ' + route_schema)
    old_magics = (old[2] + 'RQ1', old[2] + 'RS1')
    new_magics = (new[2] + 'RQ1', new[2] + 'RS1')

    source = (output / 'init.c').read_text()
    source = replace_once(source, INCLUDE, '#include "download-return.h"')
    source = replace_once(source, BEGIN, ARM + BEGIN)
    if source.count('#include "max77705-usb-route.h"') != 1 or source.count('recovery_begin()') != 1:
        raise ValueError('route producer or timer arm missing from staged init.c')
    (output / 'init.c').write_text(source)

    protocol = (output / 'protocol.h').read_text()
    protocol = _rename(protocol, (old[1], *old_magics), (new[1], *new_magics))
    (output / 'protocol.h').write_text(protocol)

    verifier = (output / 'max77705_verify.py').read_text()
    verifier = _rename(verifier, (old[0], old[1], *old_magics), (new[0], new[1], *new_magics))
    if board:
        verifier = replace_once(verifier, "'AUTHENTICATED_MAX77705_ROUTE_TRANSCRIPT'",
                                "'AUTHENTICATED_MAX77705_ROUTE_TIMER_TRANSCRIPT'")
    else:
        verifier = replace_once(verifier, "'AUTHENTICATED_H0_MAX77705_ROUTE_OBSERVATION'",
                                "'AUTHENTICATED_H0_MAX77705_ROUTE_TIMER_OBSERVATION'")
    verifier = replace_once(verifier, "'subject': 'max77705-route'}", "'subject': 'max77705-route-timer'}")
    (output / 'max77705_verify.py').write_text(verifier)
    return new[0]
