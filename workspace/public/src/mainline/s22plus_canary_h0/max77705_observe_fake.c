/* Host-only harness: runs max77705-usb-observe.h against a simulated MAX77705.
 * usage: max77705_observe_fake SCENARIO   (prints the record as hex + a bus log)
 * Scenarios: autonomous, open_stays, stale_latch, timeout, bad_echo, no_identity,
 *            write_probe, flood
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
static uint8_t usbc[256], pmic[256], fsa_present;
static int cmd_armed, cmd_polls, ctrl1_value = 0x3f, attached;
static unsigned bus_writes, bad_writes;

static uint64_t mx_now(void) { return fake_ms; }

static int mx_raw_read(uint8_t addr, uint8_t reg, uint8_t *buf, uint16_t len)
{
    if (addr == 0x66) { for (uint16_t i = 0; i < len; i++) buf[i] = pmic[reg + i]; return 0; }
    if (addr == 0x42) { if (!fsa_present) return -1; memset(buf, 0x11, len); return 0; }
    if (addr != 0x25) return -1;
    for (uint16_t i = 0; i < len; i++) buf[i] = usbc[(uint8_t)(reg + i)];
    if (reg == 0x02 || reg == 0x03) {           /* read-to-clear interrupt bytes */
        if (reg == 0x02 && cmd_armed && ++cmd_polls >= 3 && strcmp(scenario, "timeout")) {
            buf[0] |= 0x80;                         /* APCmdResI on the 3rd poll */
            usbc[0x51] = strcmp(scenario, "bad_echo") ? 0x05 : 0x06;
            usbc[0x52] = (uint8_t)ctrl1_value;
            cmd_armed = 0;
        }
        usbc[reg] = 0;
    }
    return 0;
}

static int mx_raw_write(uint8_t addr, const uint8_t *buf, uint16_t len)
{
    bus_writes++;
    if (addr != 0x25 || len != 2) { bad_writes++; return -1; }
    if (buf[0] == 0x21 && buf[1] != 0x05) bad_writes++;
    if (buf[0] == 0x41) { cmd_armed = 1; cmd_polls = 0; }
    usbc[buf[0]] = buf[1];
    return 0;
}

#include "max77705-usb-observe.h"

static void attach(void)
{
    attached = 1;
    usbc[0x02] |= 0x20 | 0x02;          /* VBUSDetI | CHGTypI */
    usbc[0x08] = 0x81;                  /* BC_STATUS: VBUSDet + SDP */
    if (!strcmp(scenario, "autonomous")) ctrl1_value = 0x09;
}

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    scenario = argv[1];
    pmic[0] = 0x15; pmic[1] = 0x02;
    usbc[0] = 0x1a; usbc[1] = 0x6e;
    fsa_present = 1;
    if (!strcmp(scenario, "no_identity")) pmic[0] = 0x00;
    if (!strcmp(scenario, "stale_latch")) { usbc[0x02] = 0x80; usbc[0x51] = 0x05; usbc[0x52] = 0x77; }
    if (!strcmp(scenario, "write_probe")) {
        /* Every disallowed write must be rejected before reaching the bus. */
        unsigned before = bus_writes;
        int a = mx_write(0x25, 0x21, 0x06), b = mx_write(0x25, 0x22, 0x09), c = mx_write(0x66, 0x21, 0x05),
            d = mx_write(0x25, 0x41, 0x01), e = mx_write(0x42, 0x04, 0x98);
        printf("rejected=%d%d%d%d%d bus_writes=%u writes_rejected=%u\n",
               a != 0, b != 0, c != 0, d != 0, e != 0, bus_writes - before, mx.writes_rejected);
        return 0;
    }
    mx_begin();
    unsigned ticks = !strcmp(scenario, "flood") ? 3000 : 600;   /* 200 ms ticks */
    for (unsigned i = 0; i < ticks; i++) {
        fake_ms += MX_TICK_MS;
        if (fake_ms == 60000 && strcmp(scenario, "flood")) attach();
        if (!strcmp(scenario, "flood")) usbc[0x03] = 0x01;     /* constant CC interrupt */
        mx_tick();
    }
    uint8_t rec[MX_RECORD_SIZE];
    mx_fill(rec);
    printf("bus_writes=%u bad_writes=%u commands=%u\n", bus_writes, bad_writes, mx.commands);
    for (unsigned i = 0; i < MX_RECORD_SIZE; i++) printf("%02x", rec[i]);
    printf("\n");
    return 0;
}
