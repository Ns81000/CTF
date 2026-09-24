# cartographer v2 state library -- Phase 1
# musl static build.  `make CARTO_TEST_BUILD=1` additionally compiles the
# test-only time-scale hook (never present in a shipped artefact).

.RECIPEPREFIX := >

CC      := musl-gcc
CFLAGS  := -O2 -Wall -Wextra -std=c11 -static -fno-ident
AR      := ar

ifneq ($(CARTO_TEST_BUILD),)
CFLAGS  += -DCARTO_TEST_TIME_SCALE_ENABLE
endif

all: libstate.a test_state mkrec

keys_blob.h: gen_keys.py
>python3 gen_keys.py keys_blob.h

carto_sha256.o: carto_sha256.c carto_sha256.h
>$(CC) $(CFLAGS) -c carto_sha256.c -o carto_sha256.o

state_core.o: state_core.c state.h policy.h carto_sha256.h keys_blob.h
>$(CC) $(CFLAGS) -c state_core.c -o state_core.o

state_policy.o: state_policy.c state.h policy.h carto_sha256.h
>$(CC) $(CFLAGS) -c state_policy.c -o state_policy.o

libstate.a: carto_sha256.o state_core.o state_policy.o
>$(AR) rcs libstate.a carto_sha256.o state_core.o state_policy.o

test_state: test_part1.c test_part2.c test_util.h libstate.a state.h policy.h
>$(CC) $(CFLAGS) test_part1.c test_part2.c libstate.a -o test_state -lm

# test-only helper, never shipped: leaves a record on disk for the
# independent Python implementation to check.
mkrec: mkrec.c libstate.a state.h policy.h
>$(CC) $(CFLAGS) mkrec.c libstate.a -o mkrec

/tmp/carto_v2_vectors.txt: gen_vectors.py
>python3 gen_vectors.py

test: test_state /tmp/carto_v2_vectors.txt
>./test_state

verify: libstate.a mkrec
>bash test_state.sh

clean:
>rm -f *.o libstate.a test_state mkrec

.PHONY: all test verify clean
