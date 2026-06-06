#ifndef A90_LOG_H
#define A90_LOG_H

#include <stdbool.h>

int a90_log_set_path(const char *path);
void a90_log_select_or_fallback(const char *preferred_path);
void a90_logf(const char *tag, const char *fmt, ...);
const char *a90_log_path(void);
bool a90_log_ready(void);

#endif
