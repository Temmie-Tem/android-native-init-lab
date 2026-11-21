/* Stage 1 MAX77705 USB-switch observer for the g0q Debian RAM profile.
 *
 * Read-only by construction: the only bytes ever written to the bus are the
 * CONTROL1 *read* command (0x05 to AP_DATAOUT0) and its start strobe (0x00 to
 * AP_DATAOUT32). mx_write() rejects anything else, so CONTROL1_W (0x06) and
 * every other register write are unreachable. Plain status registers are read
 * directly; UIC_INT/CC_INT are read-to-clear and no other driver owns them.
 *
 * Timeline: mx_begin() before USB setup, mx_tick() from the request wait loop,
 * mx_fill() copies the record into the signed body.
 */
#include <linux/i2c.h>
#include <linux/i2c-dev.h>

#ifndef MX_FAKE
#if !defined(CANARY_DEBIAN_RAM)
#error "MAX77705 observation requires the Debian RAM profile"
#endif
#endif

#define MX_PMIC_ADDR 0x66
#define MX_USBC_ADDR 0x25
#define MX_FSA_ADDR 0x42
#define MX_PMIC_ID_EXPECTED 0x15
#define MX_PMIC_REV_LOW3 0x02
#define MX_UIC_INT 0x02
#define MX_CC_INT 0x03
#define MX_USBC_STATUS1 0x06
#define MX_BC_STATUS 0x08
#define MX_CC_STATUS0 0x0a
#define MX_AP_DATAOUT0 0x21
#define MX_AP_DATAOUT_END 0x41
#define MX_AP_DATAIN0 0x51
#define MX_APCMDRES 0x80
#define MX_CTRL1_READ 0x05
#define MX_POLL_LIMIT 100U
#define MX_EVENTS 48U
#define MX_EVENT_SIZE 12U
#define MX_HEADER_SIZE 40U
#define MX_RECORD_SIZE (MX_HEADER_SIZE + MX_EVENTS * MX_EVENT_SIZE)
#define MX_COMMAND_LIMIT 32U
#define MX_TICK_MS 200U
#define MX_PERIODIC_MS 10000U
#define MX_EVENT_COMMAND_GAP_MS 1000U
#define MX_ADAPTER_PARENT "994000.i2c"

enum mx_ctrl1_status { MX_OK = 0, MX_TIMEOUT = 1, MX_PROTO = 2, MX_IO = 3, MX_SKIPPED = 4, MX_LIMIT = 5 };
enum mx_kind { MX_BEGIN = 0, MX_STATUS = 1, MX_PERIODIC = 2, MX_ON_EVENT = 3 };
enum mx_adapter { MX_ADAPTER_OK = 0, MX_ADAPTER_ABSENT = 1, MX_ADAPTER_OPEN = 2, MX_IDENTITY = 3 };

struct mx_event {
    uint32_t t_ms;
    uint8_t kind, uic, cc_int, bc_status, cc_status0, usbc_status1, ctrl1, ctrl1_status;
};

static struct {
    int fd;
    uint32_t adapter_status, adapter_errno, adapter_number;
    uint8_t pmic_id, pmic_rev, usbc_hw, usbc_fw;
    uint8_t initial_uic, initial_valid, fsa_status;
    uint8_t fsa[3];
    uint8_t last_bc, last_cc0, last_st1, have_last;
    uint32_t events_total, commands, io_errors, writes_rejected;
    uint64_t start_ms, last_command_ms, last_periodic_ms;
    struct mx_event ev[MX_EVENTS];
} mx = { .fd = -1 };

/* ---- transport (replaced by the host test harness under MX_FAKE) ---- */
#ifndef MX_FAKE
static int mx_rdwr(struct i2c_msg *msgs, unsigned count)
{
    struct i2c_rdwr_ioctl_data data = { msgs, count };
    return ioctl(mx.fd, I2C_RDWR, &data) == (int)count ? 0 : -1;
}
static int mx_raw_read(uint8_t addr, uint8_t reg, uint8_t *buf, uint16_t len)
{
    struct i2c_msg m[2] = { { addr, 0, 1, &reg }, { addr, I2C_M_RD, len, buf } };
    return mx_rdwr(m, 2);
}
static int mx_raw_write(uint8_t addr, const uint8_t *buf, uint16_t len)
{
    struct i2c_msg m = { addr, 0, len, (uint8_t *)buf };
    return mx_rdwr(&m, 1);
}
static uint64_t mx_now(void) { return now_ms(); }
#endif

/* The write allowlist: CONTROL1 read command and its start strobe only. */
static int mx_write(uint8_t addr, uint8_t reg, uint8_t value)
{
    int allowed = addr == MX_USBC_ADDR &&
                  ((reg == MX_AP_DATAOUT0 && value == MX_CTRL1_READ) ||
                   (reg == MX_AP_DATAOUT_END && value == 0x00));
    if (!allowed) {
        mx.writes_rejected++;
        return -1;
    }
    uint8_t buf[2] = { reg, value };
    return mx_raw_write(addr, buf, 2);
}
static int mx_read(uint8_t addr, uint8_t reg, uint8_t *value)
{
    if (mx_raw_read(addr, reg, value, 1)) {
        mx.io_errors++;
        return -1;
    }
    return 0;
}

/* ---- adapter discovery ---- */
#ifndef MX_FAKE
static int mx_open_adapter(void)
{
    DIR *dir = opendir("/sys/class/i2c-dev");
    if (!dir) {
        mx.adapter_status = MX_ADAPTER_ABSENT;
        mx.adapter_errno = (uint32_t)errno;
        return -1;
    }
    struct dirent *ent;
    int found = -1;
    while ((ent = readdir(dir))) {
        unsigned n;
        char tail;
        if (sscanf(ent->d_name, "i2c-%u%c", &n, &tail) != 1)
            continue;
        char link[PATH_MAX], real[PATH_MAX];
        snprintf(link, sizeof(link), "/sys/class/i2c-dev/%s/device/..", ent->d_name);
        if (!realpath(link, real))
            continue;
        const char *base = strrchr(real, '/');
        if (base && !strcmp(base + 1, MX_ADAPTER_PARENT)) {
            if (found >= 0) { found = -2; break; }  /* ambiguous */
            found = (int)n;
        }
    }
    closedir(dir);
    if (found < 0) {
        mx.adapter_status = MX_ADAPTER_ABSENT;
        mx.adapter_errno = found == -2 ? EEXIST : ENOENT;
        return -1;
    }
    char node[32];
    snprintf(node, sizeof(node), "/dev/i2c-%d", found);
    mx.adapter_number = (uint32_t)found;
    mx.fd = open(node, O_RDWR | O_CLOEXEC);
    if (mx.fd < 0) {
        mx.adapter_status = MX_ADAPTER_OPEN;
        mx.adapter_errno = (uint32_t)errno;
        return -1;
    }
    return 0;
}
#endif

/* ---- CONTROL1 read through the AP command mailbox ---- */
static uint8_t mx_ctrl1(uint8_t *value, uint8_t *uic_seen)
{
    if (mx.commands >= MX_COMMAND_LIMIT)
        return MX_LIMIT;
    mx.commands++;
    mx.last_command_ms = mx_now();
    if (mx_write(MX_USBC_ADDR, MX_AP_DATAOUT0, MX_CTRL1_READ) ||
        mx_write(MX_USBC_ADDR, MX_AP_DATAOUT_END, 0x00))
        return MX_IO;
    for (unsigned i = 0; i < MX_POLL_LIMIT; i++) {
        uint8_t uic;
        if (mx_read(MX_USBC_ADDR, MX_UIC_INT, &uic))
            return MX_IO;
        *uic_seen |= uic;
        if (uic & MX_APCMDRES) {
            uint8_t resp[2];
            if (mx_raw_read(MX_USBC_ADDR, MX_AP_DATAIN0, resp, 2)) {
                mx.io_errors++;
                return MX_IO;
            }
            if (resp[0] != MX_CTRL1_READ)
                return MX_PROTO;
            *value = resp[1];
            return MX_OK;
        }
        struct timespec d = { 0, 1500000 };
        nanosleep(&d, NULL);
    }
    return MX_TIMEOUT;
}

static void mx_record(uint8_t kind, uint8_t uic, uint8_t cc_int, uint8_t ctrl1, uint8_t status)
{
    mx.events_total++;
    unsigned slot = mx.events_total <= MX_EVENTS ? mx.events_total - 1
                                                : MX_EVENTS / 2 + (mx.events_total - 1 - MX_EVENTS / 2) % (MX_EVENTS / 2);
    /* First half is kept from boot; the second half is a ring of the latest. */
    struct mx_event *e = &mx.ev[slot];
    e->t_ms = (uint32_t)(mx_now() - mx.start_ms);
    e->kind = kind; e->uic = uic; e->cc_int = cc_int;
    e->bc_status = mx.last_bc; e->cc_status0 = mx.last_cc0; e->usbc_status1 = mx.last_st1;
    e->ctrl1 = ctrl1; e->ctrl1_status = status;
}

static int mx_status(void)
{
    return mx_read(MX_USBC_ADDR, MX_BC_STATUS, &mx.last_bc) ||
           mx_read(MX_USBC_ADDR, MX_CC_STATUS0, &mx.last_cc0) ||
           mx_read(MX_USBC_ADDR, MX_USBC_STATUS1, &mx.last_st1);
}

static void mx_begin(void)
{
    mx.start_ms = mx_now();
#ifndef MX_FAKE
    if (mx_open_adapter())
        return;
#endif
    if (mx_read(MX_PMIC_ADDR, 0x00, &mx.pmic_id) || mx_read(MX_PMIC_ADDR, 0x01, &mx.pmic_rev) ||
        mx.pmic_id != MX_PMIC_ID_EXPECTED || (mx.pmic_rev & 7) != MX_PMIC_REV_LOW3) {
        mx.adapter_status = MX_IDENTITY;
        return;
    }
    mx_read(MX_USBC_ADDR, 0x00, &mx.usbc_hw);
    mx_read(MX_USBC_ADDR, 0x01, &mx.usbc_fw);
    /* Clear and keep any latch the boot chain left, before the first command. */
    if (!mx_read(MX_USBC_ADDR, MX_UIC_INT, &mx.initial_uic))
        mx.initial_valid = 1;
    uint8_t cc_int = 0;
    mx_read(MX_USBC_ADDR, MX_CC_INT, &cc_int);
    mx_status();
    mx.have_last = 1;
    mx.fsa_status = (uint8_t)(mx_read(MX_FSA_ADDR, 0x00, &mx.fsa[0]) |
                              (mx_read(MX_FSA_ADDR, 0x04, &mx.fsa[1]) << 1) |
                              (mx_read(MX_FSA_ADDR, 0x05, &mx.fsa[2]) << 2));
    uint8_t value = 0, seen = 0, st = mx_ctrl1(&value, &seen);
    mx.last_periodic_ms = mx_now();
    mx_record(MX_BEGIN, seen, cc_int, value, st);
}

static void mx_tick(void)
{
    if (mx.adapter_status != MX_ADAPTER_OK || !mx.have_last)
        return;
    uint8_t bc = mx.last_bc, cc0 = mx.last_cc0, st1 = mx.last_st1, uic = 0, cc_int = 0;
    if (mx_read(MX_USBC_ADDR, MX_UIC_INT, &uic) || mx_read(MX_USBC_ADDR, MX_CC_INT, &cc_int) || mx_status())
        return;
    uint64_t now = mx_now();
    int changed = uic || cc_int || bc != mx.last_bc || cc0 != mx.last_cc0 || st1 != mx.last_st1;
    if (changed) {
        uint8_t value = 0, st = MX_SKIPPED, seen = uic;
        if (now - mx.last_command_ms >= MX_EVENT_COMMAND_GAP_MS)
            st = mx_ctrl1(&value, &seen);
        mx_record(st == MX_SKIPPED ? MX_STATUS : MX_ON_EVENT, seen, cc_int, value, st);
    } else if (now - mx.last_periodic_ms >= MX_PERIODIC_MS) {
        uint8_t value = 0, seen = 0, st = mx_ctrl1(&value, &seen);
        mx.last_periodic_ms = now;
        mx_record(MX_PERIODIC, seen, 0, value, st);
    }
}

static void mx_fill(uint8_t *out)
{
    memset(out, 0, MX_RECORD_SIZE);
    g_put32(out + 0, 1);  /* record version */
    g_put32(out + 4, mx.adapter_status);
    g_put32(out + 8, mx.adapter_errno);
    g_put32(out + 12, mx.adapter_number);
    out[16] = mx.pmic_id; out[17] = mx.pmic_rev; out[18] = mx.usbc_hw; out[19] = mx.usbc_fw;
    out[20] = mx.initial_uic; out[21] = mx.initial_valid; out[22] = mx.fsa_status;
    out[23] = mx.fsa[0]; out[24] = mx.fsa[1]; out[25] = mx.fsa[2];
    g_put32(out + 28, mx.events_total);
    out[32] = (uint8_t)mx.commands; out[33] = (uint8_t)(mx.io_errors > 255 ? 255 : mx.io_errors);
    out[34] = (uint8_t)mx.writes_rejected;
    g_put32(out + 36, (uint32_t)(mx_now() - mx.start_ms));
    for (unsigned i = 0; i < MX_EVENTS; i++) {
        uint8_t *p = out + MX_HEADER_SIZE + i * MX_EVENT_SIZE;
        const struct mx_event *e = &mx.ev[i];
        g_put32(p, e->t_ms);
        p[4] = e->kind; p[5] = e->uic; p[6] = e->cc_int; p[7] = e->bc_status;
        p[8] = e->cc_status0; p[9] = e->usbc_status1; p[10] = e->ctrl1; p[11] = e->ctrl1_status;
    }
}
