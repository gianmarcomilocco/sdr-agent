import os
import requests

HUNTER_KEY = os.getenv("HUNTER_API_KEY", "")
BASE = "https://api.hunter.io/v2"

def configured():
    return bool(HUNTER_KEY)

def find_email(first_name, last_name, company=None, domain=None):
    """Find the professional email of a person. Returns the data dict."""
    if not HUNTER_KEY:
        raise ValueError("HUNTER_API_KEY non configurata")
    params = {"api_key": HUNTER_KEY, "first_name": first_name, "last_name": last_name}
    if domain:
        params["domain"] = domain
    elif company:
        params["company"] = company
    else:
        raise ValueError("Fornire domain o company")
    r = requests.get(f"{BASE}/email-finder", params=params, timeout=15)
    r.raise_for_status()
    return r.json().get("data", {})

def domain_search(domain, limit=10):
    """Return all emails found at a given domain."""
    if not HUNTER_KEY:
        raise ValueError("HUNTER_API_KEY non configurata")
    params = {"api_key": HUNTER_KEY, "domain": domain, "limit": limit}
    r = requests.get(f"{BASE}/domain-search", params=params, timeout=15)
    r.raise_for_status()
    return r.json().get("data", {})

def verify_email(email):
    """Verify whether an email address is valid."""
    if not HUNTER_KEY:
        raise ValueError("HUNTER_API_KEY non configurata")
    params = {"api_key": HUNTER_KEY, "email": email}
    r = requests.get(f"{BASE}/email-verifier", params=params, timeout=15)
    r.raise_for_status()
    return r.json().get("data", {})
