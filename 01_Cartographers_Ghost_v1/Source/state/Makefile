# cartographer state library - Phase 0
# musl static build; `make test` also regenerates HMAC differential vectors.

.RECIPEPREFIX := >

CC      := musl-gcc
# -fno-ident folded in during Phase 2 (PHASE_1_LOG D17 follow-up): the
# stage-side objcopy --remove-section .comment scrub remains in place.
CFLAGS  := -O2 -Wall -Wextra -std=c11 -static -fno-ident
AR      := ar

# Phase FINAL: `make CARTO_TEST_BUILD=1` compiles the TEST-ONLY time-scale
# hook (CARTO_TEST_TIME_SCALE, see state_policy.c) into the library so the
# calibrated pacing budget can be exercised in seconds.  Shipped builds never
# pass this, so the hook is absent from every deliverable binary.
ifneq ($(CARTO_TEST_BUILD),)
CFLAGS  += -DCARTO_TEST_TIME_SCALE_ENABLE
endif

all: libstate.a

carto_sha256.o: carto_sha256.c carto_sha256.h
>$(CC) $(CFLAGS) -c carto_sha256.c -o carto_sha256.o

state_core.o: state_core.c state.h state_internal.h policy.h carto_sha256.h
>$(CC) $(CFLAGS) -c state_core.c -o state_core.o

state_policy.o: state_policy.c state.h state_internal.h policy.h carto_sha256.h
>$(CC) $(CFLAGS) -c state_policy.c -o state_policy.o

libstate.a: carto_sha256.o state_core.o state_policy.o
>$(AR) rcs libstate.a carto_sha256.o state_core.o state_policy.o

test_state: test_part1.c test_part2.c test_util.h libstate.a state.h policy.h
>$(CC) $(CFLAGS) test_part1.c test_part2.c libstate.a -o test_state -lm

/tmp/carto_vectors.txt: gen_vectors.py
>python3 gen_vectors.py

/tmp/carto_selftest.txt: gen_vectors.py
>python3 gen_vectors.py

test: test_state /tmp/carto_vectors.txt /tmp/carto_selftest.txt
>./test_state

clean:
>rm -f *.o libstate.a test_state

.PHONY: all test clean
