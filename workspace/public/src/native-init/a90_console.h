#ifndef A90_CONSOLE_H
#define A90_CONSOLE_H

#include <stdbool.h>
#include <stddef.h>
#include <sys/types.h>

enum a90_cancel_kind {
    CANCEL_NONE = 0,
    CANCEL_SOFT,
    CANCEL_HARD,
};

int a90_console_wait_tty(void);
int a90_console_attach(void);
int a90_console_reattach(const char *reason, bool announce);
void a90_console_printf(const char *fmt, ...);
int a90_console_write(const void *buf, size_t len);
void a90_console_drain_input(unsigned int quiet_ms, unsigned int max_ms);
ssize_t a90_console_readline(char *buf, size_t size);
int a90_console_dup_stdio(void);
enum a90_cancel_kind a90_console_read_cancel_event(void);
enum a90_cancel_kind a90_console_poll_cancel(int timeout_ms);
int a90_console_cancelled(const char *tag, enum a90_cancel_kind cancel);

#endif
