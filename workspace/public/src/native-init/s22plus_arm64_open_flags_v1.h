/* ARM64 Linux UAPI open flags for the freestanding S22+ supervisor.
 * arch/arm64/include/uapi/asm/fcntl.h overrides the generic/x86 values.
 * Validate these against target headers and real ARM64 syscall behavior.
 */
#ifndef S22PLUS_ARM64_OPEN_FLAGS_V1_H
#define S22PLUS_ARM64_OPEN_FLAGS_V1_H
#define S22_ARM64_O_DIRECTORY 040000U
#define S22_ARM64_O_NOFOLLOW 0100000U
#endif
