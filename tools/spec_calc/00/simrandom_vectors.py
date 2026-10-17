#!/usr/bin/env python3
"""SimRandom 参考实现（docs/spec/00_core.md 第 3.3 节），用于生成测试向量。

算法：PCG32（XSH-RR，64 位状态）+ SplitMix64 播种 + FNV-1a 64 子流名哈希。
运行：python3 simrandom_vectors.py
"""
M64 = (1 << 64) - 1
M32 = (1 << 32) - 1

PCG_MULT = 6364136223846793005
SM_GAMMA = 0x9E3779B97F4A7C15
FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3


def fnv1a64(data: bytes) -> int:
    h = FNV_OFFSET
    for b in data:
        h ^= b
        h = (h * FNV_PRIME) & M64
    return h


def splitmix64_next(x: int):
    """返回 (新状态, 输出)。"""
    x = (x + SM_GAMMA) & M64
    z = x
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
    return x, z ^ (z >> 31)


class Pcg32:
    def __init__(self, initstate: int, initseq: int):
        # 与 pcg32_srandom_r 完全一致
        self.state = 0
        self.inc = ((initseq << 1) | 1) & M64
        self.next_u32()
        self.state = (self.state + initstate) & M64
        self.next_u32()

    def next_u32(self) -> int:
        old = self.state
        self.state = (old * PCG_MULT + self.inc) & M64
        xorshifted = (((old >> 18) ^ old) >> 27) & M32
        rot = old >> 59
        return ((xorshifted >> rot) | (xorshifted << ((-rot) & 31))) & M32


class SimRandom:
    def __init__(self, seed: int):
        self.seed = seed & M64
        x, initstate = splitmix64_next(self.seed)
        x, initseq = splitmix64_next(x)
        self.pcg = Pcg32(initstate, initseq)

    def next_u32(self):
        return self.pcg.next_u32()

    def next_u64(self):
        hi = self.next_u32()
        lo = self.next_u32()
        return (hi << 32) | lo

    def next_double(self):
        return (self.next_u64() >> 11) * (1.0 / (1 << 53))

    def next_int(self, lo: int, hi: int):
        """[lo, hi)，无偏差（拒绝采样）。"""
        assert hi > lo
        rng = hi - lo
        assert rng <= M32
        threshold = ((1 << 32) - rng) % rng
        while True:
            r = self.next_u32()
            if r >= threshold:
                return lo + (r % rng)

    @staticmethod
    def child_seed(parent_seed: int, name: str) -> int:
        _, out = splitmix64_next(parent_seed ^ fnv1a64(name.encode("utf-8")))
        return out

    def derive(self, name: str) -> "SimRandom":
        return SimRandom(SimRandom.child_seed(self.seed, name))


def night_seed(run_seed: int, level_id: str, night: int) -> int:
    key = f"night:{level_id}:{night}"
    _, out = splitmix64_next(run_seed ^ fnv1a64(key.encode("utf-8")))
    return out


def hx(v, w=16):
    return "0x" + format(v, "0%dX" % w)


if __name__ == "__main__":
    # 0) 自检：PCG32 官方示例 pcg32_srandom_r(42, 54) 的前 6 个输出
    p = Pcg32(42, 54)
    ref = [0xA15C02B7, 0x7B47F409, 0xBA1D3330, 0x83D2F293, 0xBFA4784B, 0xCBED606E]
    got = [p.next_u32() for _ in range(6)]
    assert got == ref, [hex(g) for g in got]
    print("PCG32 reference (42,54) OK:", [hx(g, 8) for g in got])

    # SplitMix64 自检：种子 0 的第一个输出 = 0xE220A8397B1DCDAF
    _, o = splitmix64_next(0)
    assert o == 0xE220A8397B1DCDAF
    print("SplitMix64(0) first =", hx(o))

    print("\nFNV-1a 64:")
    for s in ["", "a", "spawn", "intercept"]:
        print(f"  {s!r}: {hx(fnv1a64(s.encode()))}")

    print("\nSeed -> PCG init (initstate, initseq) and first 5 NextUInt32:")
    for seed in [0, 1, 42, 0xDEADBEEF, M64]:
        r = SimRandom(seed)
        x, a = splitmix64_next(seed)
        x, b = splitmix64_next(x)
        outs = [r.next_u32() for _ in range(5)]
        print(f"  seed={hx(seed)} initstate={hx(a)} initseq={hx(b)}")
        print("    u32:", ", ".join(hx(v, 8) for v in outs))

    print("\nFirst 3 NextDouble (repr, 17 sig digits):")
    for seed in [0, 1, 42]:
        r = SimRandom(seed)
        print(f"  seed={seed}:", ", ".join(repr(r.next_double()) for _ in range(3)))
        r = SimRandom(seed)
        print(f"    raw u64:", ", ".join(hx(r.next_u64()) for _ in range(3)))

    print("\nFirst 10 NextInt(0, 10) / NextInt(-5, 5) / NextInt(0, 3):")
    for seed in [0, 1, 42]:
        r = SimRandom(seed)
        a = [r.next_int(0, 10) for _ in range(10)]
        r = SimRandom(seed)
        b = [r.next_int(-5, 5) for _ in range(10)]
        r = SimRandom(seed)
        c = [r.next_int(0, 3) for _ in range(10)]
        print(f"  seed={seed}: {a} | {b} | {c}")

    print("\nchild seeds from root seed 1 and first 3 u32 of each stream:")
    names = ["spawn", "movement", "sensor", "fusion", "ew", "emission", "engagement",
             "intercept", "support", "impact", "exposure", "enemy_ai", "scoring",
             "command", "civil", "environment"]
    root = SimRandom(1)
    for n in names:
        c = root.derive(n)
        print(f"  {n:12s} seed={hx(c.seed)} u32: " + ", ".join(hx(c.next_u32(), 8) for _ in range(3)))

    print("\nnested derive: SimRandom(1).derive('intercept').derive('e42'):")
    c = SimRandom(1).derive("intercept").derive("e42")
    print(f"  seed={hx(c.seed)} u32: " + ", ".join(hx(c.next_u32(), 8) for _ in range(3)))

    print("\nnight seeds:")
    for (rs, lv, n) in [(0, "test_01", 1), (1, "test_01", 1), (1, "test_01", 2), (12345, "l07", 3)]:
        print(f"  NightSeed({rs}, {lv!r}, {n}) = {hx(night_seed(rs, lv, n))}")

    # 独立性：消耗 spawn 流不影响 intercept 流
    root = SimRandom(1)
    s = root.derive("spawn")
    for _ in range(1000):
        s.next_u32()
    i1 = root.derive("intercept").next_u32()
    i2 = SimRandom(1).derive("intercept").next_u32()
    assert i1 == i2
    print("\nstream independence OK")
