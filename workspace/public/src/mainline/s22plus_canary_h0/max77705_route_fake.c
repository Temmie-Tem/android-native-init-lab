/* Host-only harness: runs max77705-usb-route.h against a simulated MAX77705.
 * usage: max77705_route_fake SCENARIO   (prints a meta line and the record as hex)
 * Scenarios: pass, nofix, initial_usb, initial_zero, dcp, no_vbus, cc_source, early_enum,
 *            write_timeout, not_held, dwell_change, write_probe, flood, no_identity,
 *            fast_replug, gap_replug, preread_change, deferred, revert, gap_departure,
 *            latched_replug, udc_during_gate, slow_gate, status1_only, begin_edge, gap_status,
 *            blind_gap, skip_then_edge, split_session, late_default
 * Clock: mx_begin() at 0 s; the gadget is bound at 2 s; 200 ms ticks follow.
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>

#define MX_FAKE 1
static void g_put32(uint8_t *p, uint32_t x) { for (unsigned i = 0; i < 4; i++) p[i] = (uint8_t)(x >> (8 * i)); }

static uint64_t fake_ms;
static const char *scenario;
static uint8_t usbc[256], pmic[256], fake_udc = 1;
static int cmd_armed, cmd_polls, ctrl1_value = 0x3f;
static unsigned bus_writes, bad_writes, route_bus_writes;
static uint64_t written_at, fail_status_until, inject_at, fail_uic_until;
static unsigned inject_nth, status_reads_at, slow_calls;

static int is(const char *name) { return !strcmp(scenario, name); }
static uint64_t mx_now(void) { return fake_ms; }
static uint8_t mx_udc_state(void)
{
    uint8_t now = fake_udc;
    if (is("slow_gate") && fake_ms == 5200 && ++slow_calls == 3) {
        fake_ms += 2000;                                /* the trailing UDC read stalls */
        usbc[0x08] = 0x00; usbc[0x0a] = 0x00;           /* and the cable is pulled meanwhile */
    }
    return now;
}

static int mx_raw_read(uint8_t addr, uint8_t reg, uint8_t *buf, uint16_t len)
{
    if (addr == 0x66) { for (uint16_t i = 0; i < len; i++) buf[i] = pmic[reg + i]; return 0; }
    if (addr == 0x42) return -1;                        /* FSA4480 absent, as on hardware */
    if (addr != 0x25) return -1;
    if (reg == 0x08 && fake_ms < fail_status_until) return -1;     /* status read fails */
    if (reg == 0x02 && !cmd_armed && fake_ms < fail_uic_until) return -1;   /* latch read fails */
    for (uint16_t i = 0; i < len; i++) buf[i] = usbc[(uint8_t)(reg + i)];
    if (reg == 0x08 && inject_at && fake_ms == inject_at && ++status_reads_at < inject_nth) return 0;
    if (reg == 0x08 && inject_at && fake_ms == inject_at) {
        /* Between this IC status read and the next UDC sample: a full cable
         * change and enumeration, leaving only latched flags behind. */
        if (is("latched_replug")) { usbc[0x02] |= 0x22; usbc[0x03] |= 0x01; fake_udc = 8; }
        if (is("udc_during_gate")) fake_udc = 6;
        inject_at = 0;
    }
    if (reg == 0x02 || reg == 0x03) {                   /* read-to-clear interrupt bytes */
        if (reg == 0x02 && cmd_armed && fake_ms == 0 && is("begin_edge"))
            buf[0] |= 0x20;                         /* a VBUS edge during the first mailbox poll */
        if (reg == 0x02 && cmd_armed && ++cmd_polls >= 3) {
            uint8_t op = usbc[0x21];
            if (!(op == 0x06 && is("write_timeout"))) {
                buf[0] |= 0x80;                          /* APCmdResI on the 3rd poll */
                if (op == 0x06 && !is("not_held")) ctrl1_value = usbc[0x22];
                if (op == 0x05 && is("preread_change") && fake_ms >= 5000 && !written_at) {
                    fake_udc = 6; usbc[0x0a] = 0xa2;    /* host reset + CC change during the pre-read */
                }
                usbc[0x51] = op;
                usbc[0x52] = op == 0x05 ? (uint8_t)ctrl1_value : 0x00;
                cmd_armed = 0;
            }
        }
        usbc[reg] = 0;
    }
    return 0;
}

static int mx_raw_write(uint8_t addr, const uint8_t *buf, uint16_t len)
{
    bus_writes++;
    if (addr != 0x25) { bad_writes++; return -1; }
    if (len == 3) {
        if (buf[0] != 0x21 || buf[1] != 0x06 || buf[2] != 0x09) bad_writes++;
        route_bus_writes++;
        written_at = fake_ms;
        usbc[0x21] = buf[1]; usbc[0x22] = buf[2];
        return 0;
    }
    if (len != 2) { bad_writes++; return -1; }
    if (buf[0] == 0x21 && buf[1] != 0x05) bad_writes++;
    if (buf[0] != 0x21 && buf[0] != 0x41) bad_writes++;
    if (buf[0] == 0x41) { cmd_armed = 1; cmd_polls = 0; }
    usbc[buf[0]] = buf[1];
    return 0;
}

#include "max77705-usb-route.h"

static void unplug(void) { usbc[0x02] |= 0x20 | 0x02; usbc[0x08] = 0x00; usbc[0x0a] = 0x00; ctrl1_value = 0x00; }
static void replug(void) { usbc[0x02] |= 0x20 | 0x02; usbc[0x08] = 0x82; usbc[0x0a] = 0xa1; }

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    scenario = argv[1];
    pmic[0] = 0x15; pmic[1] = 0x02;
    usbc[0] = 0x1a; usbc[1] = 0x6e;
    usbc[0x08] = 0x82; usbc[0x0a] = 0xa1;               /* VBUS + CDP, CC sink (Stage 1 values) */
    if (is("no_identity")) pmic[0] = 0x00;
    if (is("initial_usb") || is("skip_then_edge")) ctrl1_value = 0x09;
    if (is("initial_zero")) ctrl1_value = 0x00;
    if (is("dcp")) usbc[0x08] = 0x83;
    if (is("no_vbus")) usbc[0x08] = 0x02;
    if (is("cc_source")) usbc[0x0a] = 0xa2;
    if (is("write_probe")) {
        /* Every write outside the allowlist, and an ungated or repeated route write, is rejected. */
        unsigned before = bus_writes;
        int a = mx_write(0x25, 0x21, 0x06), b = mx_write(0x25, 0x22, 0x09), c = mx_write(0x66, 0x21, 0x05),
            d = mx_write(0x25, 0x41, 0x01), e = mx_write(0x42, 0x04, 0x98), f = mx_write_route();
        mx.gate = MX_GATE_WRITTEN;
        int g = mx_write_route(), h = mx_write_route();
        printf("rejected=%d%d%d%d%d%d%d%d bus_writes=%u writes_rejected=%u route_writes=%u\n",
               a != 0, b != 0, c != 0, d != 0, e != 0, f != 0, g != 0, h != 0, bus_writes - before,
               mx.writes_rejected, mx.route_writes);
        return 0;
    }
    mx_begin();
    fake_ms = 2000;                                     /* gadget bound */
    uint64_t request_at = 0;
    for (unsigned i = 0; i < 590 && !request_at; i++) {
        fake_ms += MX_TICK_MS;
        if (is("early_enum") && fake_ms == 3000) fake_udc = 6;
        if (is("dwell_change") && fake_ms == 3000) usbc[0x03] = 0x01;
        if (is("flood")) usbc[0x03] = 0x01;
        if (written_at && is("pass")) {
            if (fake_ms == written_at + 400) fake_udc = 6;
            if (fake_ms == written_at + 600) fake_udc = 8;
            if (fake_ms == written_at + 2000) request_at = fake_ms;
        }
        if (is("nofix") || is("initial_usb") || is("initial_zero") || is("dcp") || is("not_held") ||
            is("write_timeout")) {
            if (fake_ms == 45000) unplug();
            if (fake_ms == 48000) replug();
            if (fake_ms == 48600) fake_udc = 6;
            if (fake_ms == 48800) fake_udc = 8;
            if (fake_ms == 50000) request_at = fake_ms;
        }
        if (written_at && is("fast_replug")) {
            if (fake_ms == written_at + 1400) unplug();
            if (fake_ms == written_at + 1800) replug();
            if (fake_ms == written_at + 2400) fake_udc = 6;
            if (fake_ms == written_at + 2600) fake_udc = 8;
            if (fake_ms == written_at + 4000) request_at = fake_ms;
        }
        if (written_at && is("gap_replug")) {
            /* A whole cable-out/cable-in inside a window where status reads fail. */
            if (fake_ms == written_at + 1400) fail_status_until = written_at + 2400;
            if (fake_ms == written_at + 1600) unplug();
            if (fake_ms == written_at + 2000) { replug(); ctrl1_value = 0x09; }
            if (fake_ms == written_at + 2600) fake_udc = 6;
            if (fake_ms == written_at + 2800) fake_udc = 8;
            if (fake_ms == written_at + 4000) request_at = fake_ms;
        }
        if (written_at && is("revert")) {
            if (fake_ms == written_at + 1600) ctrl1_value = 0x3f;
            if (fake_ms == written_at + 2400) fake_udc = 6;
            if (fake_ms == written_at + 2600) fake_udc = 8;
            if (fake_ms == written_at + 4000) request_at = fake_ms;
        }
        if (is("deferred")) {
            if (fake_ms == 45000) unplug();
            if (fake_ms == 45400) replug();
            if (fake_ms == 46000) fake_udc = 6;
            if (fake_ms == 46200) fake_udc = 8;
            if (fake_ms == 48000) request_at = fake_ms;
        }
        if (is("gap_departure")) {
            /* The UDC leaves "not attached" on a tick whose IC read fails, then returns. */
            if (fake_ms == 3000) { fail_status_until = 3200; fake_udc = 6; }
            if (fake_ms == 3200) fake_udc = 1;
            if (fake_ms == 20000) request_at = fake_ms;
        }
        if (written_at && is("latched_replug")) {
            if (fake_ms == written_at + 1400) { inject_at = fake_ms; inject_nth = 1; status_reads_at = 0; }
            if (fake_ms == written_at + 3000) request_at = fake_ms;
        }
        /* The dwell ends at 5.2 s: the tick's own status read is the 1st, the
         * final gate's is the 2nd. Inject during the final gate. */
        if (is("udc_during_gate") && fake_ms == 5200) { inject_at = fake_ms; inject_nth = 2; status_reads_at = 0; }
        if (is("udc_during_gate") && fake_ms == 9000) request_at = fake_ms;
        if (written_at && is("status1_only")) {
            /* A VBUS ADC bucket change seen in status before its interrupt. */
            if (fake_ms == written_at + 1400) usbc[0x06] = 0x10;
            if (fake_ms == written_at + 1600) usbc[0x02] |= 0x10;
            if (fake_ms == written_at + 2000) fake_udc = 6;
            if (fake_ms == written_at + 2200) fake_udc = 8;
            if (fake_ms == written_at + 3000) request_at = fake_ms;
        }
        if (is("gap_status")) {
            /* Cable out and in during the dwell while every latch read fails:
             * only the gap events' status bytes show it. */
            if (fake_ms == 3000) { fail_uic_until = 3800; unplug(); ctrl1_value = 0x3f; }
            if (fake_ms == 3400) replug();
            if (fake_ms == 9000) request_at = fake_ms;
        }
        if (is("blind_gap")) {
            /* Cable out and in while both latch and status reads fail. */
            if (fake_ms == 3000) { fail_uic_until = 3800; fail_status_until = 3800; unplug(); ctrl1_value = 0x3f; }
            if (fake_ms == 3400) replug();
            if (fake_ms == 9000) request_at = fake_ms;
        }
        if (is("skip_then_edge")) {
            /* Pre-read finds 0x09 (no write); a cable edge on the very next tick. */
            if (fake_ms == 5400) usbc[0x02] |= 0x20;
            if (fake_ms == 9000) request_at = fake_ms;
        }
        if (written_at && is("split_session")) {
            /* Configured in the write's session, cable out before any switch
             * read succeeds, 0x09 read only after the reattach. */
            if (fake_ms == written_at + 400) fake_udc = 8;
            if (fake_ms == written_at + 600) { unplug(); fake_udc = 1; }
            if (fake_ms == written_at + 3600) { replug(); ctrl1_value = 0x09; }
            if (fake_ms == written_at + 4400) fake_udc = 6;
            if (fake_ms == written_at + 4600) fake_udc = 8;
            if (fake_ms == written_at + 5200) request_at = fake_ms;
        }
        if (written_at && is("late_default")) {
            /* 0x09 read back, no enumeration in that session; after a replug
             * the UDC only reaches default before the request. */
            if (fake_ms == written_at + 1800) unplug();
            if (fake_ms == written_at + 3800) { replug(); ctrl1_value = 0x09; }
            if (fake_ms == written_at + 4400) fake_udc = 6;
            if (fake_ms == written_at + 5200) request_at = fake_ms;
        }
        if (is("early_enum") && fake_ms == 3400) fake_udc = 8;
        if (is("early_enum") && fake_ms == 5000) request_at = fake_ms;
        if (!request_at) mx_tick();
    }
    mx_final();
    uint8_t rec[MX_RECORD_SIZE];
    mx_fill(rec);
    printf("bus_writes=%u bad_writes=%u route_bus_writes=%u commands=%u\n", bus_writes, bad_writes,
           route_bus_writes, mx.commands);
    for (unsigned i = 0; i < MX_RECORD_SIZE; i++) printf("%02x", rec[i]);
    printf("\n");
    return 0;
}
