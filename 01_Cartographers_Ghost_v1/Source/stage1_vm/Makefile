# stage1_vm - Phase 2
# musl static build; links the Phase-0 shared state library (../state).
# Deliverable lands in the solver package: ../../cartographer/stage1_vm/

.RECIPEPREFIX := >

CC      := musl-gcc
CFLAGS  := -O2 -Wall -Wextra -std=c11 -static -fno-ident
LIBDIR  := ../state
LIB     := $(LIBDIR)/libstate.a
PKGDIR  := ../../cartographer/stage1_vm

all: $(PKGDIR)/stage1_vm

vm_tables.h vm_program.h vm_layout.json: vm_spec.py
>python3 vm_spec.py --listing

decoy_blob.h: gen_decoys.py
>python3 gen_decoys.py

$(PKGDIR)/stage1_vm: stage1_vm.c vm.c vm.h vm_tables.h vm_program.h decoy_blob.h $(LIB) $(LIBDIR)/state.h
>mkdir -p $(PKGDIR)
>$(CC) $(CFLAGS) -I$(LIBDIR) stage1_vm.c vm.c $(LIB) -o $@
>strip --strip-all $@
>objcopy --remove-section .comment $@ 2>/dev/null || true

# internal-only builds used by test_stage1.sh (never shipped)
test_detect: test_detect.c vm_debug.h
>$(CC) $(CFLAGS) -o test_detect test_detect.c

stage1_vm.dbg: stage1_vm.c vm.c vm.h vm_tables.h vm_program.h decoy_blob.h $(LIB) $(LIBDIR)/state.h
>$(CC) -O0 -g -Wall -Wextra -std=c11 -static -fno-ident -I$(LIBDIR) stage1_vm.c vm.c $(LIB) -o $@

test: all test_detect stage1_vm.dbg
>./test_detect
>./test_stage1.sh

clean:
>rm -f $(PKGDIR)/stage1_vm test_detect stage1_vm.dbg

.PHONY: all test clean