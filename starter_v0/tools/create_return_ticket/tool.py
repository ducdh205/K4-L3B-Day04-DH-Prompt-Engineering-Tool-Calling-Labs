from __future__ import annotations

import uuid
from typing import Any

from tools._shared import err


def create_return_ticket(
    summary: str = "",
    priority: str = "medium",
    order_id: str = "",
    confirmed: bool = False
) -> dict[str, Any]:
    try:
        if not confirmed:
            return {
                "tool": "create_return_ticket",
                "status": "unconfirmed",
                "error": "confirmation_required",
                "message": "User must confirm return ticket creation before proceeding."
            }

        ticket_id = f"RET-{uuid.uuid4().hex[:6].upper()}"
        return {
            "tool": "create_return_ticket",
            "ticket_id": ticket_id,
            "order_id": order_id,
            "summary": summary,
            "priority": priority,
            "status": "created",
            "message": f"Return ticket {ticket_id} created successfully."
        }
    except Exception as exc:
        return err("create_return_ticket", exc)
