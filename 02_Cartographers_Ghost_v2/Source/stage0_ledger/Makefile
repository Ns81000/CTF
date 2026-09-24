# stage0_ledger -- musl static build into the solver package.
.RECIPEPREFIX := >

CC      := musl-gcc
CFLAGS  := -O2 -Wall -Wextra -std=c11 -static -fno-ident
LIBDIR  := ../state
LIB     := $(LIBDIR)/libstate.a
PKGDIR  := ../../cartographer

all: $(PKGDIR)/stage0_ledger/ledger

$(LIB):
>$(MAKE) -C $(LIBDIR)

$(PKGDIR)/stage0_ledger/ledger: ledger.c $(LIB) $(LIBDIR)/state.h $(LIBDIR)/policy.h
>mkdir -p $(PKGDIR)/stage0_ledger
>$(CC) $(CFLAGS) -I$(LIBDIR) ledger.c $(LIB) -o $@
>strip --strip-all $@
>objcopy --remove-section .comment $@ 2>/dev/null || true

test: all
>bash test_stage0.sh

clean:
>rm -f $(PKGDIR)/stage0_ledger/ledger

.PHONY: all test clean
