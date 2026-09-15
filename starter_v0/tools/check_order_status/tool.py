from __future__ import annotations

import json
from typing import Any

from tools._shared import ROOT, err


ORDER_FILE = ROOT / "ecommerce_data" / "orders.json"


def check_order_status(order_id: str = "") -> dict[str, Any]:
    try:
        data = json.loads(ORDER_FILE.read_text(encoding="utf-8"))
        wanted_id = (order_id or "").strip().upper()
        order = next((item for item in data["orders"] if item["order_id"] == wanted_id), None)
        if order is None:
            return {"tool": "check_order_status", "order_id": wanted_id, "error": "order_not_found"}
        return {"tool": "check_order_status", "order": order, "snapshot_at": data["snapshot_at"]}
    except Exception as exc:
        return err("check_order_status", exc)
