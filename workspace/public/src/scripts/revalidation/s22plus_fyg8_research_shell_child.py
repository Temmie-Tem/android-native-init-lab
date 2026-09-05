"""H0-only successor transform for bounded shell child cleanup.

No device entry point, new command permission or artifact publication.
Consumed P344 sources/evidence remain unchanged. A fresh reviewed candidate
must explicitly integrate this transform before any device execution.
"""


def bound_child_drain(helper: bytes) -> bytes:
    if type(helper) is not bytes:
        raise ValueError('helper must be bytes')
    old = b'''        if (reaped) {
            if (amount == 0 || amount == -EAGAIN) break;
            continue;
        }'''
    new = b'''        if (reaped) {
            if (amount == 0 || amount == -EAGAIN) break;
            /* Descendant output must not bypass the original deadline. */
            if (p282_deadline_expired(&deadline)) {
                flags |= P328_FLAG_TRUNCATED;
                break;
            }
            continue;
        }'''
    cleanup_old = b'''static long p328_cleanup_process_group(long pid) {
    (void)sys_kill(-pid, SIGKILL);
    struct timespec64 deadline = {0};
    long rc = p282_deadline_after(1LL, &deadline);
    if (rc != 0) return rc;
    for (;;) {
        int status = 0;'''
    cleanup_new = cleanup_old.replace(b'        int status = 0;',
        b'        if (p282_deadline_expired(&deadline)) return -ETIMEDOUT;\n'
        b'        int status = 0;')
    if helper.count(old) != 1 or helper.count(cleanup_old) != 1:
        raise ValueError('reviewed child/drain source shape differs')
    return helper.replace(old, new, 1).replace(cleanup_old, cleanup_new, 1)
