# stage5_title -- musl static build into the solver package.
.RECIPEPREFIX := >

CC      := musl-gcc
CFLAGS  := -O2 -Wall -Wextra -std=c11 -static -fno-ident
LIBDIR  := ../state
LIB     := $(LIBDIR)/libstate.a
PKGDIR  := ../../cartographer

all: $(PKGDIR)/stage5_title/validate

$(LIB):
>$(MAKE) -C $(LIBDIR)

$(PKGDIR)/stage5_title/validate: validate.c $(LIB) $(LIBDIR)/state.h $(LIBDIR)/policy.h $(LIBDIR)/carto_sha256.h
>mkdir -p $(PKGDIR)/stage5_title
>$(CC) $(CFLAGS) -I$(LIBDIR) validate.c $(LIB) -o $@
>strip --strip-all $@
>objcopy --remove-section .comment $@ 2>/dev/null || true

# test-only: ring seeder so the chain gate can be exercised; never shipped
seed5: seed5.c $(LIB)
>$(CC) $(CFLAGS) -I$(LIBDIR) seed5.c $(LIB) -o $@

test: all seed5
>bash test_stage5.sh

clean:
>rm -f $(PKGDIR)/stage5_title/validate seed5

.PHONY: all test clean
