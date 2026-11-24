/* Stage 2 MAX77705 USB-route observer for the g0q Debian RAM profile.
 *
 * Read-only like Stage 1 (max77705-usb-observe.h), plus exactly one gated
 * intervention: a single CONTROL1_W(COM_USB = 0x09), the command Samsung's
 * FYG8 MUIC driver issues on a USB/CDP attach. Samsung's opcode write is one
 * bulk transfer of [opcode, data] starting at AP_DATAOUT0 (0x21), then 0x00 to
 * AP_DATAOUT32 (0x41). The write is attempted at most once per boot, never
 * retried, and only when every gate holds (see mx_route()).
 *
 * The only bus writes reachable here:
 *   0x25: [0x21, 0x05]            CONTROL1_R command        (any number, <= budget)
 *   0x25: [0x41, 0x00]            mailbox start strobe      (after each command)
 *   0x25: [0x21, 0x06, 0x09]      CONTROL1_W(COM_USB)       (at most once, gated)
 * mx_write()/mx_write_route() reject everything else before the bus. No
 * register value is written to the PMIC (0x66) or FSA4480 (0x42).
 *
 * Timeline: mx_begin() before USB setup; mx_tick() every 200 ms while the
 * gadget is bound and the request is awaited; mx_final() once at the
 * authenticated request; mx_fill() copies the record into the signed body.
 */
#include <linux/i2c.h>
#include <linux/i2c-dev.h>

#ifndef MX_FAKE
#if !defined(CANARY_DEBIAN_RAM)
#error "MAX77705 route observation requires the Debian RAM profile"
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
#define MX_CTRL1_WRITE 0x06
#define MX_COM_OPEN 0x3f
#define MX_COM_USB 0x09
#define MX_BC_VBUSDET 0x80
#define MX_BC_CHGTYP 0x03
#define MX_CHGTYP_SDP 0x01
#define MX_CHGTYP_CDP 0x02
#define MX_CC_STAT 0x07
#define MX_CC_STAT_SINK 0x01
#define MX_POLL_LIMIT 100U
#define MX_EVENTS 48U
#define MX_EVENT_SIZE 16U
#define MX_HEADER_SIZE 64U
#define MX_RECORD_SIZE (MX_HEADER_SIZE + MX_EVENTS * MX_EVENT_SIZE)
#define MX_COMMAND_LIMIT 32U
#define MX_TICK_MS 200U
#define MX_PERIODIC_MS 10000U
#define MX_EVENT_COMMAND_GAP_MS 1000U
#define MX_DWELL_MS 3000U
#define MX_GATE_FRESH_MS 50U   /* final sample to write: the gate's freshness bound */
#define MX_ADAPTER_PARENT "994000.i2c"

enum mx_ctrl1_status { MX_OK = 0, MX_TIMEOUT = 1, MX_PROTO = 2, MX_IO = 3, MX_SKIPPED = 4, MX_LIMIT = 5 };
enum mx_kind {
    MX_BEGIN = 0, MX_STATUS = 1, MX_PERIODIC = 2, MX_ON_EVENT = 3, MX_UDC = 4,
    MX_PREWRITE = 5, MX_WRITE = 6, MX_READBACK = 7, MX_DEFERRED = 8, MX_REQUEST = 9, MX_GAP = 10
};
enum mx_adapter { MX_ADAPTER_OK = 0, MX_ADAPTER_ABSENT = 1, MX_ADAPTER_OPEN = 2, MX_IDENTITY = 3 };
enum mx_gate {
    MX_GATE_PENDING = 0, MX_GATE_WRITTEN = 1, MX_GATE_UDC_LEFT = 2, MX_GATE_PREREAD_FAILED = 3,
    MX_GATE_NOT_OPEN = 4, MX_GATE_VBUS = 5, MX_GATE_CHGTYP = 6, MX_GATE_CC = 7, MX_GATE_BUDGET = 8,
    MX_GATE_UDC_UNREADABLE = 9, MX_GATE_STATUS_CHANGED = 10, MX_GATE_STALE = 11
};
/* usb_state_string() values; 0 = not sampled, 0xfe = unrecognised, 0xff = read error. */
enum mx_udc {
    MX_UDC_NONE = 0, MX_UDC_NOT_ATTACHED = 1, MX_UDC_ATTACHED = 2, MX_UDC_POWERED = 3,
    MX_UDC_RECONNECTING = 4, MX_UDC_UNAUTHENTICATED = 5, MX_UDC_DEFAULT = 6, MX_UDC_ADDRESSED = 7,
    MX_UDC_CONFIGURED = 8, MX_UDC_SUSPENDED = 9, MX_UDC_UNKNOWN = 0xfe, MX_UDC_ERROR = 0xff
};

struct mx_event {
    uint32_t t_ms;
    uint8_t kind, uic, cc_int, bc_status, cc_status0, usbc_status1, ctrl1, ctrl1_status, udc;
};

static struct {
    int fd;
    uint32_t adapter_status, adapter_errno, adapter_number;
    uint8_t pmic_id, pmic_rev, usbc_hw, usbc_fw;
    uint8_t initial_uic, initial_valid, fsa_status;
    uint8_t fsa[3];
    uint8_t last_bc, last_cc0, last_st1, have_last;
    uint8_t begin_bc, begin_cc0, rec_bc, rec_cc0, rec_st1;
    uint8_t udc, gate, route_writes, write_status, write_echo, write_data, prewrite_ctrl1;
    uint8_t ic_changed, deferred_pending, readback_pending, final_done;
    uint32_t events_total, commands, io_errors, writes_rejected;
    uint64_t start_ms, last_command_ms, last_periodic_ms, dwell_start_ms, write_ms;
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
static uint8_t mx_udc_state(void)
{
    char path[96], text[32];
    size_t size = 0;
    int n = snprintf(path, sizeof(path), "/sys/class/udc/%s/state", canary_udc);
    if (n <= 0 || (size_t)n >= sizeof(path) || read_small(path, text, sizeof(text) - 1, &size))
        return MX_UDC_ERROR;
    while (size && (text[size - 1] == '\n' || text[size - 1] == '\0'))
        size--;
    text[size] = 0;
    static const char *const names[] = { "not attached", "attached", "powered", "reconnecting",
                                         "unauthenticated", "default", "addressed", "configured", "suspended" };
    for (unsigned i = 0; i < sizeof(names) / sizeof(names[0]); i++)
        if (!strcmp(text, names[i]))
            return (uint8_t)(i + 1);
    return MX_UDC_UNKNOWN;
}
#endif

/* The single-byte write allowlist: CONTROL1 read command and the start strobe. */
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

/* The one route write: CONTROL1_W(COM_USB) as Samsung's bulk opcode write.
 * Callable once, and only after mx_route() recorded MX_GATE_WRITTEN. */
static int mx_write_route(void)
{
    if (mx.gate != MX_GATE_WRITTEN || mx.route_writes) {
        mx.writes_rejected++;
        return -1;
    }
    mx.route_writes++;
    static const uint8_t buf[3] = { MX_AP_DATAOUT0, MX_CTRL1_WRITE, MX_COM_USB };
    return mx_raw_write(MX_USBC_ADDR, buf, 3);
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

/* ---- the AP command mailbox ---- */
static uint8_t mx_await(uint8_t opcode, uint8_t *value, uint8_t *uic_seen)
{
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
            if (resp[0] != opcode)
                return MX_PROTO;
            *value = resp[1];
            return MX_OK;
        }
        struct timespec d = { 0, 1500000 };
        nanosleep(&d, NULL);
    }
    return MX_TIMEOUT;
}

static uint8_t mx_ctrl1(uint8_t *value, uint8_t *uic_seen)
{
    if (mx.commands >= MX_COMMAND_LIMIT)
        return MX_LIMIT;
    mx.commands++;
    mx.last_command_ms = mx_now();
    if (mx_write(MX_USBC_ADDR, MX_AP_DATAOUT0, MX_CTRL1_READ) ||
        mx_write(MX_USBC_ADDR, MX_AP_DATAOUT_END, 0x00))
        return MX_IO;
    return mx_await(MX_CTRL1_READ, value, uic_seen);
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
    e->ctrl1 = ctrl1; e->ctrl1_status = status; e->udc = mx.udc;
    /* Any non-mailbox flag a recorded event carries is an IC change, however
     * it was read (mailbox polls included). The begin event's CC_INT is the
     * boot chain's latch and is excluded, like the initial UIC latch. */
    if ((uic & ~MX_APCMDRES) || (kind != MX_BEGIN && cc_int))
        mx.ic_changed = 1;
    /* So is any status change between recorded events, however it was
     * sampled (a gap event can record one with its interrupt read failed). */
    if (kind != MX_BEGIN && (mx.last_bc != mx.rec_bc || mx.last_cc0 != mx.rec_cc0 || mx.last_st1 != mx.rec_st1))
        mx.ic_changed = 1;
    mx.rec_bc = mx.last_bc; mx.rec_cc0 = mx.last_cc0; mx.rec_st1 = mx.last_st1;
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
    if (!mx_status()) {
        mx.have_last = 1;
        mx.begin_bc = mx.last_bc;
        mx.begin_cc0 = mx.last_cc0;
    }
    mx.fsa_status = (uint8_t)(mx_read(MX_FSA_ADDR, 0x00, &mx.fsa[0]) |
                              (mx_read(MX_FSA_ADDR, 0x04, &mx.fsa[1]) << 1) |
                              (mx_read(MX_FSA_ADDR, 0x05, &mx.fsa[2]) << 2));
    uint8_t value = 0, seen = 0, st = mx_ctrl1(&value, &seen);
    mx.last_periodic_ms = mx_now();
    mx_record(MX_BEGIN, seen, cc_int, value, st);
}

/* The single intervention. Runs from mx_tick() once the gadget is bound and
 * the UDC has read "not attached" for MX_DWELL_MS with no IC change since
 * mx_begin(). Every outcome is final: the gate is evaluated once. */
static void mx_route(void)
{
    uint8_t value = 0, seen = 0, st;
    if (mx.commands + 2 > MX_COMMAND_LIMIT) {   /* the pre-read and the write */
        mx.gate = MX_GATE_BUDGET;
        return;
    }
    st = mx_ctrl1(&value, &seen);
    mx_record(MX_PREWRITE, seen, 0, value, st);
    mx.prewrite_ctrl1 = st == MX_OK ? value : 0;
    if (st != MX_OK) {
        mx.gate = MX_GATE_PREREAD_FAILED;
        return;
    }
    if (value != MX_COM_OPEN) {
        mx.gate = MX_GATE_NOT_OPEN;
        return;
    }
    /* The pre-read took time: sample the UDC, then interrupts and status, then
     * the UDC again, and gate on these fresh values only. The write needs
     * "not attached" on both sides of the final IC sample. Any change or
     * failed read is final. */
    uint8_t bc = mx.last_bc, cc0 = mx.last_cc0, st1 = mx.last_st1, uic = 0, cc_int = 0;
    uint64_t sampled = mx_now();
    uint8_t before = mx_udc_state();
    int bad = mx_read(MX_USBC_ADDR, MX_UIC_INT, &uic);
    bad |= mx_read(MX_USBC_ADDR, MX_CC_INT, &cc_int);
    bad |= mx_status();
    uint8_t after = mx_udc_state();
    int ic = (seen | uic) & ~MX_APCMDRES || cc_int || bc != mx.last_bc || cc0 != mx.last_cc0 || st1 != mx.last_st1;
    if (bad || ic) {
        if (ic)
            mx.ic_changed = 1;
        mx.udc = after;
        mx_record(bad ? MX_GAP : MX_STATUS, (uint8_t)((seen | uic) & ~MX_APCMDRES), cc_int, 0, MX_SKIPPED);
        mx.gate = bad ? MX_GATE_PREREAD_FAILED : MX_GATE_STATUS_CHANGED;
        return;
    }
    if (before != mx.udc) {
        mx.udc = before;
        mx_record(MX_UDC, 0, 0, 0, MX_SKIPPED);
    }
    if (after != mx.udc) {
        mx.udc = after;
        mx_record(MX_UDC, 0, 0, 0, MX_SKIPPED);
    }
    if (before == MX_UDC_ERROR || before == MX_UDC_UNKNOWN || after == MX_UDC_ERROR || after == MX_UDC_UNKNOWN)
        mx.gate = MX_GATE_UDC_UNREADABLE;
    else if (before != MX_UDC_NOT_ATTACHED || after != MX_UDC_NOT_ATTACHED)
        mx.gate = MX_GATE_UDC_LEFT;
    else if (!(mx.last_bc & MX_BC_VBUSDET))
        mx.gate = MX_GATE_VBUS;
    else if ((mx.last_bc & MX_BC_CHGTYP) != MX_CHGTYP_SDP && (mx.last_bc & MX_BC_CHGTYP) != MX_CHGTYP_CDP)
        mx.gate = MX_GATE_CHGTYP;
    else if ((mx.last_cc0 & MX_CC_STAT) != MX_CC_STAT_SINK)
        mx.gate = MX_GATE_CC;
    if (mx.gate != MX_GATE_PENDING)
        return;
    /* One clock read is both the freshness check and the dispatch time;
     * nothing but the write itself follows it. */
    uint64_t dispatch = mx_now();
    if (dispatch - sampled > MX_GATE_FRESH_MS) {
        mx.gate = MX_GATE_STALE;                /* the samples are too old to gate on */
        return;
    }
    mx.gate = MX_GATE_WRITTEN;
    mx.commands++;
    mx.write_ms = mx.last_command_ms = dispatch;
    uint8_t echo_value = 0, wseen = 0;
    if (mx_write_route() || mx_write(MX_USBC_ADDR, MX_AP_DATAOUT_END, 0x00))
        mx.write_status = MX_IO;
    else
        mx.write_status = mx_await(MX_CTRL1_WRITE, &echo_value, &wseen);
    mx.write_echo = mx.write_status == MX_OK ? MX_CTRL1_WRITE : 0;
    mx.write_data = echo_value;
    mx_record(MX_WRITE, wseen, 0, MX_COM_USB, mx.write_status);
    mx.readback_pending = 1;
}

static void mx_tick(void)
{
    if (mx.adapter_status != MX_ADAPTER_OK || !mx.have_last)
        return;
    uint8_t bc = mx.last_bc, cc0 = mx.last_cc0, st1 = mx.last_st1, uic = 0, cc_int = 0;
    /* The UDC is sampled before the IC: a cable change that completes before
     * this UDC sample is still latched when the IC is read just after it, so
     * it lands on the same event (or earlier), never after "configured". */
    uint8_t udc = mx_udc_state(), udc_changed = udc != mx.udc;
    mx.udc = udc;
    /* Read both read-to-clear bytes even if one fails, so a cleared flag is
     * never discarded; a failed tick is recorded as a coverage gap. */
    int bad = mx_read(MX_USBC_ADDR, MX_UIC_INT, &uic);
    bad |= mx_read(MX_USBC_ADDR, MX_CC_INT, &cc_int);
    bad |= mx_status();
    if (bad) {
        /* Lost coverage before the write is final: a cable change may have
         * happened unseen, so the write is never sent after a gap. */
        mx.ic_changed = 1;
        if (mx.gate == MX_GATE_PENDING) {
            mx.dwell_start_ms = 0;
            if (udc == MX_UDC_ERROR || udc == MX_UDC_UNKNOWN)
                mx.gate = MX_GATE_UDC_UNREADABLE;
            else if (udc != MX_UDC_NOT_ATTACHED)
                mx.gate = MX_GATE_UDC_LEFT;     /* an observed departure is final */
        }
        mx_record(MX_GAP, uic, cc_int, 0, MX_SKIPPED);
        return;
    }
    uint64_t now = mx_now();
    int gap = now - mx.last_command_ms >= MX_EVENT_COMMAND_GAP_MS;
    /* A late mailbox response flag alone is not an IC change. */
    int changed = (uic & ~MX_APCMDRES) || cc_int || bc != mx.last_bc || cc0 != mx.last_cc0 || st1 != mx.last_st1;
    if (changed) {
        mx.ic_changed = 1;
        uint8_t value = 0, st = MX_SKIPPED, seen = uic;
        if (gap)
            st = mx_ctrl1(&value, &seen);
        mx.deferred_pending = st == MX_SKIPPED;
        mx_record(st == MX_SKIPPED ? MX_STATUS : MX_ON_EVENT, seen, cc_int, value, st);
        return;
    }
    if (udc_changed)
        mx_record(MX_UDC, 0, 0, 0, MX_SKIPPED);
    /* Gate bookkeeping: the dwell restarts whenever the UDC is not "not attached". */
    if (mx.gate == MX_GATE_PENDING) {
        if (mx.ic_changed)
            mx.gate = MX_GATE_STATUS_CHANGED;
        else if (udc == MX_UDC_ERROR || udc == MX_UDC_UNKNOWN)
            mx.gate = MX_GATE_UDC_UNREADABLE;
        else if (udc != MX_UDC_NOT_ATTACHED)
            mx.gate = MX_GATE_UDC_LEFT;
        else if (!mx.dwell_start_ms)
            mx.dwell_start_ms = now ? now : 1;
        else if (now - mx.dwell_start_ms >= MX_DWELL_MS && gap) {
            mx_route();
            return;
        }
    }
    if ((mx.readback_pending || mx.deferred_pending) && gap) {
        uint8_t value = 0, seen = 0, st = mx_ctrl1(&value, &seen);
        mx_record(mx.readback_pending ? MX_READBACK : MX_DEFERRED, seen, 0, value, st);
        mx.readback_pending = mx.deferred_pending = 0;
        return;
    }
    if (now - mx.last_periodic_ms >= MX_PERIODIC_MS) {
        uint8_t value = 0, seen = 0, st = mx_ctrl1(&value, &seen);
        mx.last_periodic_ms = now;
        mx_record(MX_PERIODIC, seen, 0, value, st);
    }
}

/* One bounded read at the authenticated request, without command spacing. */
static void mx_final(void)
{
    if (mx.final_done || mx.adapter_status != MX_ADAPTER_OK || !mx.have_last)
        return;
    mx.final_done = 1;
    uint8_t uic = 0, cc_int = 0;
    mx.udc = mx_udc_state();
    int bad = mx_read(MX_USBC_ADDR, MX_UIC_INT, &uic);
    bad |= mx_read(MX_USBC_ADDR, MX_CC_INT, &cc_int);
    bad |= mx_status();
    if (bad) {
        mx_record(MX_GAP, uic, cc_int, 0, MX_SKIPPED);
        return;
    }
    uint8_t value = 0, seen = uic, st = mx_ctrl1(&value, &seen);
    mx_record(MX_REQUEST, seen, cc_int, value, st);
}

static void mx_fill(uint8_t *out)
{
    memset(out, 0, MX_RECORD_SIZE);
    g_put32(out + 0, 2);  /* record version */
    g_put32(out + 4, mx.adapter_status);
    g_put32(out + 8, mx.adapter_errno);
    g_put32(out + 12, mx.adapter_number);
    out[16] = mx.pmic_id; out[17] = mx.pmic_rev; out[18] = mx.usbc_hw; out[19] = mx.usbc_fw;
    out[20] = mx.initial_uic; out[21] = mx.initial_valid; out[22] = mx.fsa_status;
    out[23] = mx.fsa[0]; out[24] = mx.fsa[1]; out[25] = mx.fsa[2];
    g_put32(out + 28, mx.events_total);
    out[32] = (uint8_t)mx.commands; out[33] = (uint8_t)(mx.io_errors > 255 ? 255 : mx.io_errors);
    out[34] = (uint8_t)mx.writes_rejected; out[35] = mx.route_writes;
    g_put32(out + 36, (uint32_t)(mx_now() - mx.start_ms));
    out[40] = mx.gate; out[41] = mx.prewrite_ctrl1; out[42] = mx.write_status; out[43] = mx.write_echo;
    out[44] = mx.write_data; out[45] = mx.begin_bc; out[46] = mx.begin_cc0; out[47] = mx.udc;
    g_put32(out + 48, mx.write_ms ? (uint32_t)(mx.write_ms - mx.start_ms) : 0);
    g_put32(out + 52, mx.dwell_start_ms ? (uint32_t)(mx.dwell_start_ms - mx.start_ms) : 0);
    for (unsigned i = 0; i < MX_EVENTS; i++) {
        uint8_t *p = out + MX_HEADER_SIZE + i * MX_EVENT_SIZE;
        const struct mx_event *e = &mx.ev[i];
        g_put32(p, e->t_ms);
        p[4] = e->kind; p[5] = e->uic; p[6] = e->cc_int; p[7] = e->bc_status;
        p[8] = e->cc_status0; p[9] = e->usbc_status1; p[10] = e->ctrl1; p[11] = e->ctrl1_status;
        p[12] = e->udc;
    }
}
