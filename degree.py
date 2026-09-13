"""Compatibility shim for Vercel's Python function import path.

The FastAPI entrypoint lives under api/, while Vercel may not put that
folder itself on sys.path. Re-export the Degree adapter from its canonical
location so `from degree import ...` works in both local and Vercel runtimes.
"""

from api.degree import DEGREE_CAPTCHA_REFRESH_URL, DEGREE_EXAMINATIONS, DEGREE_URL, parse_degree_result

__all__ = [
    "DEGREE_CAPTCHA_REFRESH_URL",
    "DEGREE_EXAMINATIONS",
    "DEGREE_URL",
    "parse_degree_result",
]
