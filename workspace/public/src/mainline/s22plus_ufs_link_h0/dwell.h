/* One authenticated late dispatch. A physical compilation must explicitly
 * select the fixed module backend and Download return. */
#if !defined(CANARY_H0_VM) && !defined(ML030_G0Q_MODULE)
#error "no physical UFS backend selected"
#endif
#if defined(ML030_G0Q_MODULE) && (!defined(CANARY_DOWNLOAD_RAM) || defined(ML030_QEMU_UFS))
#error "the g0q module requires its distinct Download runtime"
#endif
#ifdef ML030_QEMU_UFS
#include "emulated_uic.h"
#endif
#define ML030_DWELL_MS 300000U
#define ML030_END_MS 540000U
#define ML030_BODY 136U
#define ML030_FRAME (ML030_BODY + 32U)

#ifdef ML030_G0Q_MODULE
#include "link-runtime.h"
#endif

static uint64_t ml030_u64(const uint8_t *p) {
    return (uint64_t)g_u32(p) | ((uint64_t)g_u32(p + 4) << 32);
}

static int ml030_tag_ok(const uint8_t *frame, unsigned kind) {
    uint8_t tag[32];
    g_tag(tag, canary_key, canary_id, kind, frame, ML030_BODY);
    return g_equal(tag, frame + ML030_BODY, sizeof(tag));
}

static int ml030_dwell(int fd, const uint8_t base[G0Q_RESPONSE_SIZE]) {
    uint8_t frame[ML030_FRAME], witness[ML030_FRAME], next[G0Q_RESPONSE_SIZE], zero[32] = {0};
    uint64_t t0 = ml030_u64(base + 216);
    if (!t0 || t0 >= 120000 || now_ms() >= 120000) return ETIMEDOUT;
    /* Absolute guest BOOTTIME measured from this boot, never extended on I/O. */
    deadline = ML030_END_MS;
    int err = transfer(fd, frame, sizeof(frame), 0);
    if (err) return err;
    uint64_t now = now_ms();
    if (now < t0 + ML030_DWELL_MS || now >= deadline) return ETIMEDOUT;
    if (memcmp(frame, "G030ASK1", 8) || !ml030_tag_ok(frame, 16) ||
        !g_equal(frame + 8, canary_id, 32) || !g_equal(frame + 40, base + 40, 32) ||
        g_equal(frame + 72, zero, 32) || g_equal(frame + 72, base + 40, 32) ||
        !g_equal(frame + 104, base + 72, 16) || ml030_u64(frame + 120) != t0 ||
        ml030_u64(frame + 128)) return EACCES;
    /* Reobserve this exact boot, PID 1 and observer, FDT, timer and zero block devices. */
    if ((err = proof(frame + 72, next))) return err;
    if (!g_equal(next + 72, base + 72, 144) || !g_equal(next + 256, base + 256, 96) ||
        ml030_u64(next + 216) < t0 + ML030_DWELL_MS || now_ms() >= deadline) return EPROTO;
    memcpy(witness, frame, ML030_BODY);
    memcpy(witness, "G030WIT1", 8);
    memcpy(witness + 128, next + 216, 8);
    g_tag(witness + ML030_BODY, canary_key, canary_id, 17, witness, ML030_BODY);
    if ((err = transfer(fd, witness, sizeof(witness), 1))) return err;
    /* A late witness alone cannot dispatch. Only the verified host can send this distinct permit. */
    if ((err = transfer(fd, frame, sizeof(frame), 0))) return err;
    if (memcmp(frame, "G030GO01", 8) || !ml030_tag_ok(frame, 18) ||
        !g_equal(frame + 8, witness + 8, ML030_BODY - 8) || now_ms() >= deadline) return EACCES;
#ifdef ML030_G0Q_MODULE
    return ml030_module_result(fd, witness);
#elif defined(ML030_QEMU_UFS)
    if ((err = emu_link_once())) return err;
    memcpy(frame, "G030EMU1", 8);
#else
    dprintf(2, "ML030_VM_HANDOFF_ONCE NO_UFS_BACKEND\n");
    memcpy(frame, "G030H001", 8);
#endif
    g_tag(frame + ML030_BODY, canary_key, canary_id, 19, frame, ML030_BODY);
    return transfer(fd, frame, sizeof(frame), 1);
}
