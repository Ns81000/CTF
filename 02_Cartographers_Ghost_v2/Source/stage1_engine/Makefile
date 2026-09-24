# stage1_engine -- musl static build into the solver package.
.RECIPEPREFIX := >

CC      := musl-gcc
CFLAGS  := -O2 -Wall -Wextra -std=c11 -static -fno-ident
LIBDIR  := ../state
LIB     := $(LIBDIR)/libstate.a
PKGDIR  := ../../cartographer

all: $(PKGDIR)/stage1_engine/engine $(PKGDIR)/stage1_engine/profile.notes

# The image, the opcode bytes and the side records all come from the
# deterministic generator; stage1_program.json is what the model reads.
stage1_blob.h: vm_spec.py model_vm.py
>python3 vm_spec.py

stage1_program.json: vm_spec.py model_vm.py
>python3 vm_spec.py

$(LIB):
>$(MAKE) -C $(LIBDIR)

$(PKGDIR)/stage1_engine/engine: engine.c stage1_blob.h $(LIB) $(LIBDIR)/state.h $(LIBDIR)/policy.h
>mkdir -p $(PKGDIR)/stage1_engine
>$(CC) $(CFLAGS) -I$(LIBDIR) engine.c $(LIB) -o $@
>strip --strip-all $@
>objcopy --remove-section .comment $@ 2>/dev/null || true

# The clerk's door card: an authoritative-looking note with the wrong counts.
$(PKGDIR)/stage1_engine/profile.notes: profile.notes
>mkdir -p $(PKGDIR)/stage1_engine
>cp profile.notes $@

test: all
>bash test_stage1.sh

clean:
>rm -f $(PKGDIR)/stage1_engine/engine

.PHONY: all test clean
