/* Execute the exact production reset function against bounded H0 registers. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
typedef uint32_t u32;
#define BIT(n) (1U << (n))
#include "reset-pin.h"
static u32 regs[2];
static unsigned int scenario, expiry, clocks, writes, assertions, deassertions;
static int reset_token;
static struct { void *reset_io; int *reset; } board = {regs, &reset_token};
static int remaining(void)
{
	clocks++;
	printf("budget %u\n", clocks);
	return clocks == expiry ? -ETIMEDOUT : 0;
}
static u32 readl(const void *address)
{
	assert(address == regs || address == regs + 1);
	u32 value = *(const u32 *)address;
	if (address == regs + 1 && scenario == 5 && writes == 1) value |= 1;
	if (address == regs + 1 && scenario == 6 && writes == 2) value &= ~1U;
	printf("read %s %u\n", address == regs ? "CTL" : "IO", value);
	return value;
}
static void writel(u32 value, void *address)
{
	assert(address == regs + 1 && writes < 2); /* No CTL writer or extra pulse. */
	writes++;
	*(u32 *)address = value;
	printf("write IO %u\n", value);
}
static int reset_control_assert(int *reset)
{
	assert(reset == &reset_token && !assertions++);
	puts("GCC assert");
	return scenario == 7 ? -EIO : 0;
}
static int reset_control_deassert(int *reset)
{
	assert(reset == &reset_token && assertions == 1 && !deassertions++);
	puts("GCC deassert");
	if (scenario == 3) regs[0] ^= 1;
	if (scenario == 4) regs[1] &= ~1U;
	return scenario == 8 ? -EIO : 0;
}
static void usleep_range(unsigned int low, unsigned int high)
{
	printf("sleep %u %u\n", low, high);
}
#include "reset.inc"
int main(int argc, char **argv)
{
	assert(argc == 5);
	regs[0] = (u32)strtoul(argv[1], NULL, 0);
	regs[1] = (u32)strtoul(argv[2], NULL, 0);
	scenario = (unsigned int)strtoul(argv[3], NULL, 0);
	expiry = (unsigned int)strtoul(argv[4], NULL, 0);
	int rc = reset_host_and_device();
	printf("RESULT %d %u %u %u %u\n", rc, writes, assertions, deassertions, regs[1]);
	return 0;
}
