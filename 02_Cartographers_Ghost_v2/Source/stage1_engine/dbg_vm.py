import sys
sys.path.insert(0, ".")
import vm_spec as V
import model_vm as M

first = V.build_image()
raw = {}
for name in V.BASE:
    try:
        raw[name] = V.simulate(first, name)
        print("%s pass1 steps=%d out=%s" % (name, raw[name][0],
                                            raw[name][1].hex()))
    except Exception as exc:  # noqa
        print("%s pass1 CRASH %r" % (name, exc))

fixups = {n: bytes(a ^ b for a, b in zip(raw[n][1], V.K_ENGINE)) for n in raw}
second = V.build_image(fixups)
for name in V.BASE:
    vm = M.Vm(second, V.OPB, entry=V.BASE[name])
    try:
        steps = vm.run()
        print("%s pass2 steps=%d out=%s match=%s" %
              (name, steps, vm.outputs().hex(), vm.outputs() == V.K_ENGINE))
    except Exception as exc:  # noqa
        print("%s pass2 CRASH %r at step=%d pc=0x%x sp=%d" %
              (name, exc, vm.steps, vm.pc, vm.sp))
        lo = max(0, vm.pc - 8)
        print("   code around pc:", bytes(vm.code[lo:vm.pc + 8]).hex())
        print("   last ops:", [M.ISA[vm.inv.get(b, 0)][0]
                               for b in vm.code[lo:vm.pc + 8]])
