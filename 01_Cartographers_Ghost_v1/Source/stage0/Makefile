# stage0_start - Phase 1
# musl static build; links the Phase-0 shared state library (../state).
# Deliverable lands in the solver package: ../../cartographer/stage0_start/

.RECIPEPREFIX := >

CC      := musl-gcc
CFLAGS  := -O2 -Wall -Wextra -std=c11 -static -fno-ident
LIBDIR  := ../state
LIB     := $(LIBDIR)/libstate.a
PKGDIR  := ../../cartographer/stage0_start

all: $(PKGDIR)/stage0_start

flag_blob.h: gen_flag_blob.py
>python3 gen_flag_blob.py

$(PKGDIR)/stage0_start: stage0.c flag_blob.h $(LIB) $(LIBDIR)/state.h
>mkdir -p $(PKGDIR)
>$(CC) $(CFLAGS) -I$(LIBDIR) stage0.c $(LIB) -o $@
>strip --strip-all $@
>objcopy --remove-section .comment $@ 2>/dev/null || true

test: $(PKGDIR)/stage0_start
>./test_stage0.sh

clean:
>rm -f $(PKGDIR)/stage0_start

.PHONY: all test clean
