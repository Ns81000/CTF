# stage2_stego - Phase 3
# musl static build; links the Phase-0 shared state library (../state).
# Deliverable lands in the solver package: ../../cartographer/stage2_stego/
# along with the two carriers it audits (survey_frame.png, survey_tape.wav).

.RECIPEPREFIX := >

CC      := musl-gcc
CFLAGS  := -O2 -Wall -Wextra -std=c11 -static -fno-ident
LIBDIR  := ../state
LIB     := $(LIBDIR)/libstate.a
PKGDIR  := ../../cartographer/stage2_stego

all: $(PKGDIR)/stage2_stego $(PKGDIR)/survey_frame.png $(PKGDIR)/survey_tape.wav

# The carriers, the press formula and the generated constant header all come
# from one deterministic generator (byte-identical on every re-run).
stage2_blob.h: gen_carriers.py
>python3 gen_carriers.py

$(PKGDIR)/survey_frame.png: gen_carriers.py
>python3 gen_carriers.py

$(PKGDIR)/survey_tape.wav: gen_carriers.py
>python3 gen_carriers.py

$(PKGDIR)/stage2_stego: stage2_stego.c s2_inflate.c s2_inflate.h stage2_blob.h $(LIB) $(LIBDIR)/state.h
>mkdir -p $(PKGDIR)
>$(CC) $(CFLAGS) -I$(LIBDIR) stage2_stego.c s2_inflate.c $(LIB) -o $@
>strip --strip-all $@
>objcopy --remove-section .comment $@ 2>/dev/null || true

# internal-only build used by test_stage2.sh (never shipped)
test_inflate: s2_inflate.c s2_inflate.h test_inflate.c
>$(CC) $(CFLAGS) -o test_inflate s2_inflate.c test_inflate.c

test: all test_inflate
>./test_stage2.sh

clean:
>rm -f test_inflate $(PKGDIR)/stage2_stego

.PHONY: all test clean