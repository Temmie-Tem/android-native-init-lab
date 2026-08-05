#ifndef A90_BENCHMARK_H
#define A90_BENCHMARK_H

#include "a90_config.h"

#define A90_BENCHMARK_SCHEMA "a90-boot-benchmark-v1"

void a90_benchmark_mark(const char *stage);
void a90_benchmark_emit(const char *stage);

#endif /* A90_BENCHMARK_H */
