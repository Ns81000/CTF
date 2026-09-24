# stage2_sheet -- musl static build; the carriers come from the generator.
.RECIPEPREFIX := >

CC      := musl-gcc
CFLAGS  := -O2 -Wall -Wextra -std=c11 -static -fno-ident
LIBDIR  := ../state
LIB     := $(LIBDIR)/libstate.a
PKGDIR  := ../../cartographer

all: $(PKGDIR)/stage2_sheet/sheet $(PKGDIR)/stage2_sheet/survey_frame.png \
     $(PKGDIR)/stage2_sheet/survey_tape.wav

$(LIB):
>$(MAKE) -C $(LIBDIR)

carriers_info.json: gen_carriers.py
>python3 gen_carriers.py .

$(PKGDIR)/stage2_sheet/survey_frame.png: gen_carriers.py
>mkdir -p $(PKGDIR)/stage2_sheet
>python3 gen_carriers.py $(PKGDIR)/stage2_sheet

$(PKGDIR)/stage2_sheet/survey_tape.wav: gen_carriers.py
>mkdir -p $(PKGDIR)/stage2_sheet
>python3 gen_carriers.py $(PKGDIR)/stage2_sheet

$(PKGDIR)/stage2_sheet/sheet: sheet.c s2_inflate.c s2_inflate.h $(LIB) $(LIBDIR)/state.h $(LIBDIR)/policy.h
>mkdir -p $(PKGDIR)/stage2_sheet
>$(CC) $(CFLAGS) -I$(LIBDIR) sheet.c s2_inflate.c $(LIB) -o $@
>strip --strip-all $@
>objcopy --remove-section .comment $@ 2>/dev/null || true

test: all
>bash test_stage2.sh

clean:
>rm -f $(PKGDIR)/stage2_sheet/sheet

.PHONY: all test clean
