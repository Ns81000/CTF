#ifndef CARTO_TEST_UTIL_H
#define CARTO_TEST_UTIL_H

#include <stdio.h>

extern int g_run;
extern int g_fail;

void run_part2_tests(void);

#define RUN(name)                                                       \
    do {                                                                \
        g_run++;                                                        \
        if ((name)() != 0) {                                            \
            g_fail++;                                                   \
            printf("[FAIL] %s\n", #name);                               \
        } else {                                                        \
            printf("[PASS] %s\n", #name);                               \
        }                                                               \
    } while (0)

#define CHECK(cond, msg)                                                \
    do {                                                                \
        if (!(cond)) {                                                  \
            printf("    check failed: %s (at %s:%d)\n",                 \
                   (msg), __FILE__, __LINE__);                          \
            return -1;                                                  \
        }                                                               \
    } while (0)

#endif /* CARTO_TEST_UTIL_H */
