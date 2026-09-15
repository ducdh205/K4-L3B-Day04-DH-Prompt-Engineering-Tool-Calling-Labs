from __future__ import annotations

import json
from typing import Any

from tools._shared import ROOT, err


CUSTOMER_FILE = ROOT / "ecommerce_data" / "customers.json"


def lookup_customer(customer_id: str = "", email: str = "") -> dict[str, Any]:
    try:
        data = json.loads(CUSTOMER_FILE.read_text(encoding="utf-8"))
        wanted_id = (customer_id or "").strip().upper()
        wanted_email = (email or "").strip().lower()

        customer = None
        for item in data["customers"]:
            if wanted_id and item["customer_id"] == wanted_id:
                customer = item
                break
            if wanted_email and item["email"].lower() == wanted_email:
                customer = item
                break

        if customer is None:
            return {"tool": "lookup_customer", "customer_id": wanted_id or wanted_email, "error": "customer_not_found"}
        return {"tool": "lookup_customer", "customer": customer, "snapshot_at": data["snapshot_at"]}
    except Exception as exc:
        return err("lookup_customer", exc)
