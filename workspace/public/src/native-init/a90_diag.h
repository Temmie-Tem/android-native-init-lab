#ifndef A90_DIAG_H
#define A90_DIAG_H

#include <stddef.h>

int a90_diag_print_summary(void);
int a90_diag_print_full(void);
int a90_diag_write_bundle(char *out_path, size_t out_size);
const char *a90_diag_default_dir(void);

#endif
