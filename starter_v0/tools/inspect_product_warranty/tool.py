from __future__ import annotations

import json
from typing import Any

from tools._shared import ROOT, err


WARRANTY_FILE = ROOT / "ecommerce_data" / "warranties.json"


def inspect_product_warranty(serial_number: str = "", check: str = "all") -> dict[str, Any]:
    try:
        data = json.loads(WARRANTY_FILE.read_text(encoding="utf-8"))
        wanted_sn = (serial_number or "").strip().upper()
        item = next((w for w in data["warranties"] if w["serial_number"] == wanted_sn), None)
        if item is None:
            return {"tool": "inspect_product_warranty", "serial_number": wanted_sn, "error": "warranty_record_not_found"}
        return {
            "tool": "inspect_product_warranty",
            "serial_number": wanted_sn,
            "warranty": item,
            "check": check,
            "snapshot_at": data["snapshot_at"]
        }
    except Exception as exc:
        return err("inspect_product_warranty", exc)
