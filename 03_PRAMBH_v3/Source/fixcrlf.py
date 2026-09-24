import pathlib

root = pathlib.Path('/home/ns8pc/prambh-build')
exts = {'.sh', '.py', '.c', '.h', '.md', '.txt'}
names = {'Makefile'}
count = 0
for p in root.rglob('*'):
    if p.is_file() and (p.suffix in exts or p.name in names):
        b = p.read_bytes()
        if b'\r' in b:
            p.write_bytes(b.replace(b'\r', b''))
            count += 1
print('CRLF STRIP DONE (%d files fixed)' % count)
