from __future__ import annotations
import random


def generate_otp() -> str:
    # 6 xonali raqam (000000-999999 emas, 100000-999999 – 0 bilan boshlanmasin desak pastdagini ishlatamiz)
    # return f"{random.randint(100000, 999999)}"
    return f"{random.randint(0, 999999):06d}"
