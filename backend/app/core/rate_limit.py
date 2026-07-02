"""Rate limiting via slowapi (in-memory — fine for single-instance VPS).

Applied limits (PLAN.md §3.1):
- POST /auth/login:    5/minute per IP
- POST /auth/register: 3/minute per IP
- POST /auth/refresh:  10/minute per IP
- POST /imports/*:     5/hour per IP
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
