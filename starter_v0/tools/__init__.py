from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .clarify.tool import ask_user
from .check_order_status.tool import check_order_status
from .create_return_ticket.tool import create_return_ticket
from .format_return_summary.tool import format_return_summary
from .inspect_product_warranty.tool import inspect_product_warranty
from .lookup_customer.tool import lookup_customer
from .check_refund_conditions.tool import check_refund_conditions
from .search_store_policy.tool import search_store_policy
from .search_product_specs.tool import search_product_specs
from .auto_generate_compensation_voucher.tool import auto_generate_compensation_voucher


TOOL_FUNCTIONS = {
    "clarify": ask_user,
    "search_store_policy": search_store_policy,
    "search_product_specs": search_product_specs,
    "check_order_status": check_order_status,
    "inspect_product_warranty": inspect_product_warranty,
    "lookup_customer": lookup_customer,
    "format_return_summary": format_return_summary,
    "check_refund_conditions": check_refund_conditions,
    "create_return_ticket": create_return_ticket,
    "auto_generate_compensation_voucher": auto_generate_compensation_voucher,
}


def load_tool_declarations(path: Path) -> list[dict[str, Any]]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))["tools"]


def to_openai_tools(declarations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "type": "function",
        "function": {
            "name": item["name"],
            "description": item.get("description", ""),
            "parameters": item.get("parameters", {"type": "object", "properties": {}}),
        },
    } for item in declarations]
