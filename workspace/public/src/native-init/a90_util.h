#ifndef A90_UTIL_H
#define A90_UTIL_H

#include <stddef.h>
#include <sys/types.h>

long monotonic_millis(void);
int ensure_dir(const char *path, mode_t mode);
int negative_errno_or(int fallback_errno);
int write_all_checked(int fd, const char *buf, size_t len);
void write_all(int fd, const char *buf, size_t len);
int read_text_file(const char *path, char *buf, size_t buf_size);
void trim_newline(char *buf);
void flatten_inline_text(char *buf);
int read_trimmed_text_file(const char *path, char *buf, size_t buf_size);

#endif
