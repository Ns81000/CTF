# stage3_oracle -- musl static build into the solver package.
.RECIPEPREFIX := >

CC      := musl-gcc
CFLAGS  := -O2 -Wall -Wextra -std=c11 -static -fno-ident
LIBDIR  := ../state
LIB     := $(LIBDIR)/libstate.a
PKGDIR  := ../../cartographer

all: $(PKGDIR)/stage3_oracle/oracle

stage3_blob.h: gen_oracle.py
>python3 gen_oracle.py

stage3_tables.json: gen_oracle.py
>python3 gen_oracle.py

$(LIB):
>$(MAKE) -C $(LIBDIR)

$(PKGDIR)/stage3_oracle/oracle: oracle.c stage3_blob.h $(LIB) $(LIBDIR)/state.h $(LIBDIR)/policy.h
>mkdir -p $(PKGDIR)/stage3_oracle
>$(CC) $(CFLAGS) -I$(LIBDIR) oracle.c $(LIB) -o $@
>strip --strip-all $@
>objcopy --remove-section .comment $@ 2>/dev/null || true

# test-only: the same oracle with the duration hook compiled in, so the
# calibrated sitting can be exercised in seconds.  Never shipped.
oracle_test: oracle.c stage3_blob.h $(LIBDIR)/carto_sha256.c $(LIBDIR)/state_core.c $(LIBDIR)/state_policy.c
>$(CC) $(CFLAGS) -DCARTO_TEST_TIME_SCALE_ENABLE -I$(LIBDIR) -I. oracle.c $(LIBDIR)/carto_sha256.c $(LIBDIR)/state_core.c $(LIBDIR)/state_policy.c -o $@ -lm

seed3: seed3.c $(LIB)
>$(CC) $(CFLAGS) -I$(LIBDIR) seed3.c $(LIB) -o $@ -lm

test: all oracle_test seed3
>bash test_stage3.sh

clean:
>rm -f $(PKGDIR)/stage3_oracle/oracle oracle_test

.PHONY: all test clean
