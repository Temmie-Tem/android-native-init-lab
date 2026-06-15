// V2487 Android audio HAL exec wrapper for ACDB tap measurement.
// Public source only. The wrapped vendor HAL binary is proprietary and is copied
// into the private Magisk module by the host-side planner; never commit it.
//
// This is intentionally freestanding: the private Android clang bundle used by
// this project does not ship an Android sysroot.  The wrapper only needs to
// prepend two environment variables and exec the preserved stock HAL, so raw ARM
// EABI syscalls are sufficient.

#define A90_REAL_HAL "/vendor/bin/hw/android.hardware.audio.service.a90orig"
#define A90_PRELOAD_SO "/vendor/lib/libacdbtap.so"
#define A90_CAPTURE_DIR "/data/local/tmp/a90-acdb-tap"
#define A90_ENV_LD_PRELOAD "LD_PRELOAD=" A90_PRELOAD_SO
#define A90_ENV_CAPTURE_DIR "A90_ACDBTAP_DIR=" A90_CAPTURE_DIR
#define A90_KMSG_PREFIX "A90_ACDBTAP_WRAPPER "

#define A90_AT_FDCWD (-100)
#define A90_O_WRONLY 00000001
#define A90_O_CLOEXEC 02000000

#define A90_NR_WRITE 4
#define A90_NR_CLOSE 6
#define A90_NR_EXECVE 11
#define A90_NR_EXIT_GROUP 248
#define A90_NR_OPENAT 322

typedef unsigned int a90_size_t;
typedef unsigned long a90_word_t;

static long a90_syscall1(long number, long arg0)
{
    register long r0 __asm__("r0") = arg0;
    register long r7 __asm__("r7") = number;
    __asm__ volatile("svc #0" : "+r"(r0) : "r"(r7) : "memory");
    return r0;
}

static long a90_syscall3(long number, long arg0, long arg1, long arg2)
{
    register long r0 __asm__("r0") = arg0;
    register long r1 __asm__("r1") = arg1;
    register long r2 __asm__("r2") = arg2;
    register long r7 __asm__("r7") = number;
    __asm__ volatile("svc #0" : "+r"(r0) : "r"(r1), "r"(r2), "r"(r7) : "memory");
    return r0;
}

static long a90_syscall4(long number, long arg0, long arg1, long arg2, long arg3)
{
    register long r0 __asm__("r0") = arg0;
    register long r1 __asm__("r1") = arg1;
    register long r2 __asm__("r2") = arg2;
    register long r3 __asm__("r3") = arg3;
    register long r7 __asm__("r7") = number;
    __asm__ volatile("svc #0" : "+r"(r0) : "r"(r1), "r"(r2), "r"(r3), "r"(r7) : "memory");
    return r0;
}

static a90_size_t a90_strlen(const char *text)
{
    a90_size_t length = 0;
    while (text != (const char *)0 && text[length] != '\0') {
        ++length;
    }
    return length;
}

static int a90_starts_with(const char *text, const char *prefix)
{
    a90_size_t index = 0;
    if (text == (const char *)0 || prefix == (const char *)0) {
        return 0;
    }
    while (prefix[index] != '\0') {
        if (text[index] != prefix[index]) {
            return 0;
        }
        ++index;
    }
    return 1;
}

static void a90_write_all(int fd, const char *text)
{
    a90_size_t length = a90_strlen(text);
    if (length == 0) {
        return;
    }
    (void)a90_syscall3(A90_NR_WRITE, fd, (long)text, (long)length);
}

static void a90_kmsg(const char *message)
{
    long fd = a90_syscall4(A90_NR_OPENAT, A90_AT_FDCWD, (long)"/dev/kmsg",
                           A90_O_WRONLY | A90_O_CLOEXEC, 0);
    if (fd < 0) {
        return;
    }
    a90_write_all((int)fd, A90_KMSG_PREFIX);
    a90_write_all((int)fd, message);
    a90_write_all((int)fd, " real=" A90_REAL_HAL " preload=" A90_PRELOAD_SO "\n");
    (void)a90_syscall1(A90_NR_CLOSE, fd);
}

static int a90_keep_env(const char *entry)
{
    return !a90_starts_with(entry, "LD_PRELOAD=") && !a90_starts_with(entry, "A90_ACDBTAP_DIR=");
}

__attribute__((used, noreturn)) void a90_start_c(a90_word_t *stack)
{
    a90_word_t argc = stack[0];
    char **argv = (char **)(stack + 1);
    char **envp = argv + argc + 1;
    a90_size_t env_count = 0;
    a90_size_t kept_count = 0;

    while (envp[env_count] != (char *)0) {
        if (a90_keep_env(envp[env_count])) {
            ++kept_count;
        }
        ++env_count;
    }

    char *new_env[kept_count + 3U];
    a90_size_t out_index = 0;
    new_env[out_index++] = (char *)A90_ENV_LD_PRELOAD;
    new_env[out_index++] = (char *)A90_ENV_CAPTURE_DIR;
    for (a90_size_t index = 0; index < env_count; ++index) {
        if (a90_keep_env(envp[index])) {
            new_env[out_index++] = envp[index];
        }
    }
    new_env[out_index] = (char *)0;

    if (argc > 0 && argv != (char **)0) {
        argv[0] = (char *)A90_REAL_HAL;
    }

    (void)a90_syscall3(A90_NR_EXECVE, (long)A90_REAL_HAL, (long)argv, (long)new_env);
    a90_kmsg("execve-failed");
    (void)a90_syscall1(A90_NR_EXIT_GROUP, 127);
    for (;;) {
    }
}

__attribute__((naked, noreturn)) void _start(void)
{
    __asm__ volatile("mov r0, sp\n"
                     "b a90_start_c\n");
}
