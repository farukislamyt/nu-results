import base64
import json
import os
from http.cookies import SimpleCookie

import requests
from bs4 import BeautifulSoup
from flask import Response, jsonify, request

NU_URL = "https://results.nu.ac.bd/honours"


def _secret():
    return os.environ.get("SESSION_SIGNING_SECRET", "dev-only-change-me")


def _sign(payload: dict) -> str:
    import hashlib
    import hmac

    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(_secret().encode(), raw, hashlib.sha256).hexdigest()
    token = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return f"{token}.{sig}"


def handler(request):
    try:
        s = requests.Session()
        r = s.get(NU_URL, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        token_el = soup.find("input", {"name": "_token"})
        captcha_el = soup.select_one("span.fw-bold.fs-5")
        if not token_el or not captcha_el:
            return jsonify({"error": "NU result form structure could not be read."}), 502

        captcha = captcha_el.get_text(" ", strip=True)
        payload = {
            "csrf": token_el.get("value", ""),
            "cookies": s.cookies.get_dict(),
        }

        return jsonify({"captcha": captcha, "session": _sign(payload)})
    except requests.RequestException:
        return jsonify({"error": "Could not connect to National University result server."}), 502
    except Exception:
        return jsonify({"error": "Unexpected error while preparing the result search."}), 500
