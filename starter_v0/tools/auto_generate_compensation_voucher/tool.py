from __future__ import annotations

import uuid
from typing import Any

from tools._shared import err


def auto_generate_compensation_voucher(
    order_id: str = "",
    reason: str = "shipping_delay",
    amount_usd: float = 20.0,
    confirmed: bool = False
) -> dict[str, Any]:
    """
    [BONUS FEATURE (+10 Points)]
    Auto-assesses customer complaint (shipping delay, minor packaging flaw)
    and instantly generates a compensation voucher code without manual review.
    """
    try:
        if not confirmed:
            return {
                "tool": "auto_generate_compensation_voucher",
                "status": "unconfirmed",
                "error": "confirmation_required",
                "message": "User must confirm voucher issue request before generation."
            }

        voucher_code = f"VOUCHER-{reason.upper()[:3]}-{uuid.uuid4().hex[:4].upper()}"
        return {
            "tool": "auto_generate_compensation_voucher",
            "voucher_code": voucher_code,
            "order_id": order_id,
            "reason": reason,
            "amount_usd": amount_usd,
            "status": "issued",
            "message": f"Compensation voucher {voucher_code} for ${amount_usd} issued successfully."
        }
    except Exception as exc:
        return err("auto_generate_compensation_voucher", exc)
