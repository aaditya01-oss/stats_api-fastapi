"""
limiter.py — Shared rate limiter instance.

Defined here so it can be imported by both main.py and routers
without circular imports.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)