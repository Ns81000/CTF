import sys
sys.path.insert(0, ".")
import vm_spec as V
import model_vm as M

name = "coast"
code, smc_addr, blen = V.build(name, None)
off = smc_addr - V.BASE[name]
plain = code[off:off + blen]
img = V.build_image()
got = img[smc_addr:smc_addr + blen]
stream = V.smc_stream(name)[:blen]
print("program bytes      %d (block offset %d, block %d bytes)" %
      (len(code), off, blen))
print("plain block        %s" % plain.hex())
print("image block        %s" % got.hex())
print("stream             %s" % stream.hex())
print("image ^ stream     %s" % bytes(a ^ b for a, b in zip(got, stream)).hex())
print("words              %s" % [hex(w) for w in V.smc_words(name)])
first = img[:len(code)]
print("prologue len       %d" % (len(first) - (len(code) - off)))
