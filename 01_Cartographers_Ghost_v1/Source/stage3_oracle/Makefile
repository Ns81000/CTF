# stage3_oracle - Phase 4
# musl static build; links the Phase-0 shared state library (../state).
# Deliverable lands in the solver package: ../../cartographer/stage3_oracle/
#
# oracle_blob.h (masked KDF seeds + round-function fold tables) is generated
# deterministically by gen_oracle_constants.py (INTERNAL, not shipped).
# model_oracle.py / solve_attack.py / test_stage3.sh are INTERNAL test
# tooling (never shipped); they are not built by make.

.RECIPEPREFIX := >

CC      := musl-gcc
CFLAGS  := -O2 -Wall -Wextra -std=c11 -static -fno-ident
LIBDIR  := ../state
LIB     := $(LIBDIR)/libstate.a
PKGDIR  := ../../cartographer/stage3_oracle

all: $(PKGDIR)/oracle

oracle_blob.h: gen_oracle_constants.py
>python3 gen_oracle_constants.py

$(PKGDIR)/oracle: oracle.c oracle_blob.h $(LIB) $(LIBDIR)/state.h
>mkdir -p $(PKGDIR)
>$(CC) $(CFLAGS) -I$(LIBDIR) oracle.c $(LIB) -o $@
>strip --strip-all $@
>objcopy --remove-section .comment $@ 2>/dev/null || true

# internal-only test tooling (never shipped)
test: all
>./test_stage3.sh

clean:
>rm -f $(PKGDIR)/oracle

.PHONY: all test clean
