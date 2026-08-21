"""验证 is_prime 函数的正确性。"""
import sys
sys.path.insert(0, '.')
from is_prime import is_prime

# 1. 边界用例
assert is_prime(-10) is False, "负数应为 False"
assert is_prime(0) is False, "0 应为 False"
assert is_prime(1) is False, "1 应为 False"
assert is_prime(2) is True, "2 应为 True"
assert is_prime(3) is True, "3 应为 True"

# 2. 已知质数（前若干 + 较大质数）
known_primes = [
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47,
    53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113,
    7919, 104729, 1299709, 15485863,
]
for p in known_primes:
    assert is_prime(p) is True, f"{p} 应为质数"

# 3. 已知合数
known_composites = [
    4, 6, 8, 9, 10, 12, 14, 15, 16, 18, 20, 21, 22, 25, 27,
    49, 51, 91, 100, 121, 1234567, 104730, 1299711,
]
for c in known_composites:
    assert is_prime(c) is False, f"{c} 应为合数"

# 4. 完全平方数（因子在 sqrt 边界上）
for n in [4, 9, 25, 49, 121, 1681, 9409, 6724, 14884]:
    assert is_prime(n) is False, f"{n} 应为合数"

# 5. 与参考实现对照（遍历 0~20000 + 抽样大范围）
def reference_is_prime(n: int) -> bool:
    if n <= 1:
        return False
    i = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += 1
    return True

for n in range(0, 20001):
    assert is_prime(n) == reference_is_prime(n), f"n={n} 结果不一致"

import random
random.seed(42)
for _ in range(2000):
    n = random.randint(2, 10**8)
    assert is_prime(n) == reference_is_prime(n), f"n={n} 结果不一致"

print("所有测试通过 ✔")
