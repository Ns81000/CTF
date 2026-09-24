import sys
sys.path.insert(0, ".")
import vm_spec as V
import model_vm as M

name = "coast"
img = V.build_image()
vm = M.Vm(img, V.OPB, entry=V.BASE[name])

print("block at 0x498 before:", bytes(vm.code[0x498:0x4AC]).hex())
print("stream words         :", [hex(w) for w in V.smc_words(name)])

# walk the prologue and show every instruction up to the loop body
pc = V.BASE[name]
for i in range(130):
    vm.pc = pc
    fr = vm.fetch()
    if fr is None:
        print("0x%03x  <bad byte 0x%02x>" % (pc, vm.code[pc]))
        break
    nam, ops, size = fr
    if nam in ("MOVI", "SMXX", "CALL", "LDIND", "STIND", "JNZ"):
        print("0x%03x  %-8s %s" % (pc, nam, [hex(x) for x in ops]))
    pc += size
    if nam == "CALL":
        break

vm2 = M.Vm(img, V.OPB, entry=V.BASE[name])
for _ in range(112):
    if vm2.halt:
        break
    vm2.step()
print("r1=0x%08x r2=0x%08x r3=0x%08x sp=%d pc=0x%x" %
      (vm2.r[1], vm2.r[2], vm2.r[3], vm2.sp, vm2.pc))
print("block after 112 steps:", bytes(vm2.code[0x498:0x4AC]).hex())
