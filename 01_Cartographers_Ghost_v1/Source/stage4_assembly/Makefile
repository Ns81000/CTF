# stage4_assembly - Phase 5
# musl static build; links the Phase-0 shared state library (../state).
# Deliverable lands in the solver package: ../../cartographer/stage4_assembly/
#
# stage4_blob.h (expected-title digest + length + struck-draft decoy) is
# generated deterministically by gen_title_blob.py (INTERNAL, not shipped).
# test_stage4.sh / policy_patch4.py / verify.sh are INTERNAL tooling.
#
# NOTE: the deliverable runs FROM the package root (state path
# "./.cartographer_state"), like every other stage binary.

.RECIPEPREFIX := >

CC      := musl-gcc
CFLAGS  := -O2 -Wall -Wextra -std=c11 -static -fno-ident
LIBDIR  := ../state
LIB     := $(LIBDIR)/libstate.a
PKGDIR  := ../../cartographer/stage4_assembly

all: $(PKGDIR)/validate

stage4_blob.h: gen_title_blob.py
>python3 gen_title_blob.py

$(PKGDIR)/validate: validate.c stage4_blob.h $(LIB) $(LIBDIR)/state.h
>mkdir -p $(PKGDIR)
>$(CC) $(CFLAGS) -I$(LIBDIR) validate.c $(LIB) -o $@
>strip --strip-all $@
>objcopy --remove-section .comment $@ 2>/dev/null || true

test: all
>./test_stage4.sh

clean:
>rm -f $(PKGDIR)/validate

.PHONY: all test clean
