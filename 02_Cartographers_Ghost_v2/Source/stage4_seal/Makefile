# stage4_seal -- musl static build into the solver package.
.RECIPEPREFIX := >

CC      := musl-gcc
CFLAGS  := -O2 -Wall -Wextra -std=c11 -static -fno-ident
LIBDIR  := ../state
LIB     := $(LIBDIR)/libstate.a
PKGDIR  := ../../cartographer

all: $(PKGDIR)/stage4_seal/seal

seal_tables.h seal_blob.h: gen_seal.py
>python3 gen_seal.py seal_tables.h seal_blob.h

$(LIB):
>$(MAKE) -C $(LIBDIR)

$(PKGDIR)/stage4_seal/seal: seal.c seal_tables.h seal_blob.h $(LIB) $(LIBDIR)/state.h $(LIBDIR)/policy.h
>mkdir -p $(PKGDIR)/stage4_seal
>$(CC) $(CFLAGS) -I$(LIBDIR) -I. seal.c $(LIB) -o $@
>strip --strip-all $@
>objcopy --remove-section .comment $@ 2>/dev/null || true

# test-only: the intended attack over the public certificate; never shipped
mitm: mitm.c seal_tables.h
>$(CC) $(CFLAGS) -I. mitm.c -o $@

test: all mitm
>bash test_stage4.sh

clean:
>rm -f $(PKGDIR)/stage4_seal/seal mitm

.PHONY: all test clean
