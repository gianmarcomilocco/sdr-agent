import os
import requests

APOLLO_KEY = os.getenv("APOLLO_API_KEY", "")
BASE = "https://api.apollo.io/api/v1"

EMP_RANGES = {
    "1–10":    ["1,10"],
    "11–50":   ["11,20", "21,50"],
    "51–200":  ["51,100", "101,200"],
    "201–500": ["201,500"],
    "500+":    ["501,1000", "1001,2000", "2001,5000", "5001,10000", "10001,"],
}

SENIORITY_MAP = {
    "C-Suite / Founder": ["c_suite", "founder", "owner"],
    "VP / Head":         ["vp", "head"],
    "Director":          ["director"],
    "Manager":           ["manager"],
    "Senior IC":         ["senior"],
}

def configured():
    return bool(APOLLO_KEY)

def search_people(titles=None, keywords=None, person_locations=None, org_locations=None,
                  emp_ranges=None, seniorities=None, page=1, per_page=25):
    if not APOLLO_KEY:
        raise ValueError("APOLLO_API_KEY non configurata")

    headers = {
        "x-api-key": APOLLO_KEY,
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }
    payload = {"page": page, "per_page": per_page}
    if titles:           payload["person_titles"]                     = titles
    if keywords:         payload["q_keywords"]                        = keywords
    if person_locations: payload["person_locations"]                  = person_locations
    if org_locations:    payload["organization_locations"]            = org_locations
    if emp_ranges:       payload["organization_num_employees_ranges"] = emp_ranges
    if seniorities:      payload["person_seniorities"]                = seniorities

    r = requests.post(f"{BASE}/mixed_people/api_search",
                      headers=headers, json=payload, timeout=20)
    r.raise_for_status()
    return r.json()
