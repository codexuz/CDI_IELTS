# bot/app/state.py
from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Dict, Tuple, Optional


@dataclass
class OtpEntry:
    code: str
    expires_at: float  # epoch seconds
    last_req_at: float  # oxirgi "so'rash" vaqti (rate-limit uchun)
    hits_window_start: float  # 10s oynaning boshlanishi
    hits_in_window: int  # shu oynadagi requestlar soni


# (telegram_id, purpose) -> OtpEntry
_otp_cache: Dict[Tuple[int, str], OtpEntry] = {}

# sozlamalar
OTP_TTL_SEC = 120  # 2 daqiqa
MIN_INTERVAL_SEC = 2  # har 2 soniyada 1 marotaba
WINDOW_SEC = 10  # 10 soniyalik oyna
MAX_HITS_IN_WINDOW = 5  # 10 sekundda 5 tadan ko‘p emas


def now() -> float:
    return time.time()


def get_active_otp(tg_id: int, purpose: str) -> Optional[OtpEntry]:
    key = (tg_id, purpose)
    entry = _otp_cache.get(key)
    if not entry:
        return None
    if entry.expires_at <= now():
        # muddati o‘tgan bo‘lsa o‘chirib yuboramiz
        _otp_cache.pop(key, None)
        return None
    return entry


def can_request(tg_id: int, purpose: str) -> Tuple[bool, float]:
    """
    Rate-limit tekshiruvi.
    Return: (allowed, wait_seconds_if_denied)
    """
    t = now()
    key = (tg_id, purpose)
    entry = _otp_cache.get(key)

    # Min interval
    if entry and (t - entry.last_req_at) < MIN_INTERVAL_SEC:
        return False, max(0.0, MIN_INTERVAL_SEC - (t - entry.last_req_at))

    # Sliding window
    if entry:
        if (t - entry.hits_window_start) > WINDOW_SEC:
            # yangi oyna
            entry.hits_window_start = t
            entry.hits_in_window = 0
        if entry.hits_in_window >= MAX_HITS_IN_WINDOW:
            return False, max(0.0, WINDOW_SEC - (t - entry.hits_window_start))
    return True, 0.0


def record_hit(tg_id: int, purpose: str) -> None:
    t = now()
    key = (tg_id, purpose)
    entry = _otp_cache.get(key)
    if entry:
        entry.last_req_at = t
        # oyna ichida hisoblash
        if (t - entry.hits_window_start) > WINDOW_SEC:
            entry.hits_window_start = t
            entry.hits_in_window = 1
        else:
            entry.hits_in_window += 1


def save_new_otp(
    tg_id: int, purpose: str, code: str, ttl_sec: int = OTP_TTL_SEC
) -> OtpEntry:
    t = now()
    entry = OtpEntry(
        code=code,
        expires_at=t + ttl_sec,
        last_req_at=t,
        hits_window_start=t,
        hits_in_window=1,
    )
    _otp_cache[(tg_id, purpose)] = entry
    return entry
