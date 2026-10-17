# 独立实现（仅依据 docs/spec/00_core.md 3.1 / 3.7.1 文字描述），核对 T-00-01..10、T-00-24
M64 = (1 << 64) - 1
M32 = (1 << 32) - 1
PCG_MUL = 6364136223846793005
GAMMA = 0x9E3779B97F4A7C15
MUL1 = 0xBF58476D1CE4E5B9
MUL2 = 0x94D049BB133111EB
FNV_OFF = 0xCBF29CE484222325
FNV_PRIME = 0x00000100000001B3
import struct

def splitmix(x):
    x = (x + GAMMA) & M64
    z = x
    z = ((z ^ (z >> 30)) * MUL1) & M64
    z = ((z ^ (z >> 27)) * MUL2) & M64
    return x, z ^ (z >> 31)

def fnv(data: bytes, h=FNV_OFF):
    for b in data:
        h ^= b
        h = (h * FNV_PRIME) & M64
    return h

class R:
    def __init__(self, seed=None, pcg=None):
        if pcg is None:
            self.seed = seed
            x = seed
            x, init_state = splitmix(x)
            x, init_seq = splitmix(x)
        else:
            self.seed = None
            init_state, init_seq = pcg
        self.init = (init_state, init_seq)
        self.state = 0
        self.inc = ((init_seq << 1) | 1) & M64
        self.u32()
        self.state = (self.state + init_state) & M64
        self.u32()
    def u32(self):
        old = self.state
        self.state = (old * PCG_MUL + self.inc) & M64
        xs = (((old >> 18) ^ old) >> 27) & M32
        rot = old >> 59
        return ((xs >> rot) | (xs << ((-rot) & 31))) & M32
    def u64(self):
        hi = self.u32(); lo = self.u32(); return (hi << 32) | lo
    def dbl(self):
        return (self.u64() >> 11) * (1.0 / 9007199254740992.0)
    def nextint(self, lo, hi):
        rng = (hi - lo) & M32
        v, n = bounded(rng, self.u32)
        return lo + v, n
    def derive(self, name):
        return R(child_seed(self.seed, name))

def bounded(rng, nxt):
    th = ((0 - rng) & M32) % rng
    n = 0
    while True:
        r = nxt(); n += 1
        if r >= th:
            return r % rng, n

def child_seed(parent, name):
    x = parent ^ fnv(name.encode('utf-8'))
    _, out = splitmix(x)
    return out

def night_seed(run, level, idx):
    x = run ^ fnv(f"night:{level}:{idx}".encode())
    return splitmix(x)[1]

H = lambda v: f"0x{v:08X}" if v <= M32 else f"0x{v:016X}"
fails = 0
def check(name, got, exp):
    global fails
    ok = got == exp
    if not ok: fails += 1
    print(("OK  " if ok else "FAIL"), name, "got", got, "exp", exp)

# T-00-01
r = R(pcg=(42, 54))
check("T01", [H(r.u32()) for _ in range(6)], ["0xA15C02B7","0x7B47F409","0xBA1D3330","0x83D2F293","0xBFA4784B","0xCBED606E"])
# T-00-02
x, a = splitmix(0); x, b = splitmix(x)
check("T02 splitmix", [H(a), H(b)], ["0xE220A8397B1DCDAF","0x6E789E6AA1B965F4"])
check("T02 fnv", [H(fnv(s.encode())) for s in ["", "a", "spawn", "intercept"]],
      ["0xCBF29CE484222325","0xAF63DC4C8601EC8C","0x4328F78AB20E1F98","0x708A838B1F6CE3B5"])
# T-00-03
T03 = {0:["0x90644221","0x4618E85F","0x8F5BD9CD","0xAF2C0306","0xF6CD0B71"],
       1:["0x5249C5DC","0x01959430","0xE7976769","0x57D21847","0xEC099420"],
       42:["0xD11DD51F","0xA9B04C45","0xB5D97AA9","0xA9EAB6CE","0xF63FD201"],
       0xDEADBEEF:["0x249C431B","0xCF8CB18E","0xAF46EBC6","0x1CA90B3E","0x60A23D17"],
       M64:["0x4DF7FDF8","0x74675B30","0xA2F72031","0x21AFFDBD","0x328CC5C3"]}
for s, exp in T03.items():
    r = R(s); check(f"T03 seed {s:#x}", [H(r.u32()) for _ in range(5)], exp)
r = R(1); check("T03 mid", [H(r.init[0]), H(r.init[1])], ["0x910A2DEC89025CC1","0xBEEB8DA1658EEC67"])
# T-00-04
T04 = {0:(["0x906442214618E85F","0x8F5BD9CDAF2C0306","0xF6CD0B71A19AB615"],[0.5640298205599695,0.5599952819022036,0.964066233865746]),
       1:(["0x5249C5DC01959430","0xE797676957D21847","0xEC0994207EFB0D93"],[0.3214381849407657,0.9046539909539394,0.922021158155058]),
       42:(["0xD11DD51FA9B04C45","0xB5D97AA9A9EAB6CE","0xF63FD2019D8FEFEB"],[0.8168614580442305,0.7103497184961423,0.9619113210624729])}
for s,(u,d) in T04.items():
    r = R(s); check(f"T04 u64 {s}", [H(r.u64()) for _ in range(3)], u)
    r = R(s); check(f"T04 dbl {s}", [r.dbl() for _ in range(3)], d)
# T-00-05
T05 = {0:([3,1,1,8,5,3,4,5,5,1],[-2,-4,-4,3,0,-2,-1,0,0,-4],[1,1,2,0,2,2,2,2,0,1]),
       1:([2,6,5,7,0,7,8,3,5,7],[-3,1,0,2,-5,2,3,-2,0,2],[2,1,2,2,2,0,2,1,2,2]),
       42:([7,5,9,6,5,9,1,8,1,7],[2,0,4,1,0,4,-4,3,-4,2],[2,1,2,2,1,0,1,0,0,1])}
for s,(a,b,c) in T05.items():
    for (lo,hi),exp in zip([(0,10),(-5,5),(0,3)],[a,b,c]):
        r = R(s); check(f"T05 {s} [{lo},{hi})", [r.nextint(lo,hi)[0] for _ in range(10)], exp)
# T-00-06
def seq(vals):
    it = iter(vals); return lambda: next(it)
check("T06 a", bounded(3, seq([0,1])), (1,2))
check("T06 b", bounded(10, seq([5,6])), (6,2))
check("T06 c", bounded(1, seq([0xFFFFFFFF])), (0,1))
# T-00-07
r = R(1); v,_ = r.nextint(5,6); check("T07 nextint(5,6)", (v, H(r.u32())), (5, "0x01959430"))
r = R(1); c0 = r.dbl() < 0; c1 = r.dbl() < 1; check("T07 chance", (c0, c1, H(r.u64())), (False, True, "0xEC0994207EFB0D93"))
# T-00-08
T08 = [("setup","0x83016B1BF7A6CC04",["0x75A09F26","0xF09090BC","0xA77AF880"]),
("command","0xC4D789363E64FADD",["0xD868D361","0xFD7B5DEF","0x7D0F991A"]),
("spawn","0x247FD80E4FD86BD1",["0x3F223FCE","0x72F5159C","0xAB0AC575"]),
("movement","0x793B80FD5AE18AC6",["0xCF5A9749","0x5B539D73","0x03221EC2"]),
("sensor","0xEDA6E1A5EBB04BFC",["0xEBD79AFA","0x29F41534","0xE6FB224E"]),
("fusion","0x96BC36F0E16CCB80",["0xF69CD22D","0x4BB10F87","0x6DCC86FA"]),
("ew","0xB367DB5DFA5E020B",["0xAC0F589E","0x71C7CD73","0x3B41E853"]),
("emission","0xD2942CAECC22C8AA",["0xC8F4D9F5","0x9C717F9A","0x5698AB4E"]),
("engagement","0xA32E81D369DE6FE5",["0x5098CDE5","0x45DC9F1C","0xC2ADC3F8"]),
("intercept","0x3FCF8184E343749C",["0xC4B39A4F","0x0731B85D","0x8312946F"]),
("support","0x2484FDDC722E8093",["0x97D30FBE","0xD60CC280","0x0B187A53"]),
("impact","0xD87469420706C63D",["0xC07EB9FA","0xFD8437EF","0x4F5F6421"]),
("exposure","0xF88583C05CF5FFCA",["0x7BC2CD37","0x1D488B45","0xFF431DC2"]),
("enemy_ai","0xD3DFA39460ABC9A1",["0x64D978DC","0x781860D1","0x55A0C437"]),
("scoring","0x75D4D178DA2D89C3",["0x4258D618","0x89EDD2A4","0x4002CDB5"]),
("civil","0xCEA91EEB942D54E9",["0xE5EDFFC0","0x6ACCAE05","0xACAA8BE8"]),
("environment","0x1E3144E56455EE94",["0xB7C590F2","0x8E19A029","0x08CEEDEA"]),
("crew","0x205BA603E1FCB805",["0x7BE1DBCA","0xD8835427","0xA152C83A"])]
for name, cs, outs in T08:
    c = child_seed(1, name); r = R(c)
    check(f"T08 {name}", (H(c), [H(r.u32()) for _ in range(3)]), (cs, outs))
n = R(1).derive("intercept").derive("e42")
check("T08 nested", (H(n.seed), [H(n.u32()) for _ in range(3)]), ("0xCB468B9271533E47", ["0x0869DFE2","0x1F3EE24C","0x3A0BBDB0"]))
# T-00-10
check("T10", [H(night_seed(0,"test_01",1)), H(night_seed(1,"test_01",1)), H(night_seed(1,"test_01",2)), H(night_seed(12345,"l07",3))],
      ["0x3ED2DE67F24D80CD","0x6DD180096484586D","0x92C4A19D40D3C63D","0x7B78FE8FA9400AAF"])
# T-00-24 StateHasher
def w_int(v): return struct.pack('<i', v)
def w_dbl(v):
    if v == 0.0: v = 0.0
    return struct.pack('<d', v)
def w_str(s):
    if s is None: return w_int(-1)
    b = s.encode(); return w_int(len(b)) + b
cases = [("none", b"", "0xCBF29CE484222325"),
         ("7", w_int(7), "0x6D3572669B2CDE42"),
         ("1.5", w_dbl(1.5), "0xAA95E93229A27C80"),
         ("-0.0", w_dbl(-0.0), "0xA8C7F832281A39C5"),
         ("ab", w_str("ab"), "0x9254FD600693E9A0"),
         ("null", w_str(None), "0x994F76653E2A3951"),
         ("combo", w_int(7)+w_dbl(1.5)+w_str("ab")+b"\x01"+struct.pack('<Q',0xDEADBEEF), "0x461DC66E88FEC47B")]
for nm, by, exp in cases:
    check(f"T24 {nm}", H(fnv(by)), exp)
print("combo bytes", (w_int(7)+w_dbl(1.5)+w_str("ab")+b"\x01"+struct.pack('<Q',0xDEADBEEF)).hex())
print("FAILS:", fails)
