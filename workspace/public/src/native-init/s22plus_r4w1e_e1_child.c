#include <stddef.h>
#include <stdint.h>

#define NR_WRITE 64
#define NR_EXIT 93

static const char k_child_token[] =
    "S22PLUS_R4W1E_E1_CHILD_OK:4c3e58c0785b\n";

static inline long syscall3(long nr, long a0, long a1, long a2) {
    register long x0 asm("x0") = a0;
    register long x1 asm("x1") = a1;
    register long x2 asm("x2") = a2;
    register long x8 asm("x8") = nr;
    asm volatile(
        "svc #0"
        : "+r"(x0)
        : "r"(x1), "r"(x2), "r"(x8)
        : "memory");
    return x0;
}

__attribute__((noreturn)) static void sys_exit(int status) {
    (void)syscall3(NR_EXIT, status, 0, 0);
    for (;;) {
        asm volatile("wfe" ::: "memory");
    }
}

__attribute__((noreturn)) void _start(void) {
    size_t offset = 0;
    size_t length = sizeof(k_child_token) - 1U;
    while (offset < length) {
        long result = syscall3(
            NR_WRITE,
            1,
            (long)(uintptr_t)(k_child_token + offset),
            (long)(length - offset));
        if (result <= 0) {
            sys_exit(111);
        }
        offset += (size_t)result;
    }
    sys_exit(23);
}
