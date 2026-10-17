#!/usr/bin/env python3
"""StateHasher 测试向量（docs/spec/00_core.md 第 8 节）：FNV-1a 64，小端编码。"""
import struct
M64=(1<<64)-1
def fnv(data, h=0xCBF29CE484222325):
    for b in data:
        h ^= b; h = (h*0x100000001B3) & M64
    return h
def i32(v): return struct.pack('<i', v)
def i64(v): return struct.pack('<q', v)
def u64(v): return struct.pack('<Q', v)
def f64(v):
    if v == 0.0: v = 0.0   # -0.0 归一为 +0.0
    return struct.pack('<d', v)
def b(v): return bytes([1 if v else 0])
def s(v):
    if v is None: return i32(-1)
    e=v.encode('utf-8'); return i32(len(e))+e
cases = {
 'empty': b'',
 'int32 7': i32(7),
 'double 1.5': f64(1.5),
 'double -0.0': f64(-0.0),
 'string "ab"': s('ab'),
 'null string': s(None),
 'seq: int32 7, double 1.5, string "ab", bool true, uint64 0xDEADBEEF': i32(7)+f64(1.5)+s('ab')+b(True)+u64(0xDEADBEEF),
}
for k,v in cases.items():
    print(f"{k:70s} bytes={v.hex()} hash=0x{fnv(v):016X}")
