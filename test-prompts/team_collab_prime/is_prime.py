import math


def is_prime(n: int) -> bool:
    """判断整数 n 是否为质数。

    质数定义为大于 1 且只能被 1 和自身整除的正整数，
    因此 n <= 1 时直接返回 False。
    """
    if n <= 1:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    limit = int(math.isqrt(n))
    for i in range(3, limit + 1, 2):
        if n % i == 0:
            return False
    return True
