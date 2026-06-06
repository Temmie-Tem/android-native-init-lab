#ifndef A90_CMDPROTO_H
#define A90_CMDPROTO_H

#include <stdbool.h>

#include "a90_config.h"

struct a90_cmdproto_decoded {
    char *argv[CMDV1X_MAX_ARGS];
    char buffer[CMDV1X_BUFFER_BYTES];
    int argc;
};

const char *a90_cmdproto_status(int result, bool unknown, bool busy);
void a90_cmdproto_begin(unsigned long seq,
                        const char *command,
                        int argc,
                        unsigned int flags);
void a90_cmdproto_end(unsigned long seq,
                      const char *command,
                      int result,
                      int result_errno,
                      long duration_ms,
                      unsigned int flags,
                      const char *status);
int a90_cmdproto_decode_v1x(char **tokens,
                            int token_count,
                            struct a90_cmdproto_decoded *decoded);

#endif
