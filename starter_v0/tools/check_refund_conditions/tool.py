from __future__ import annotations

import json
from typing import Any

from tools._shared import ROOT, err, terms


POLICY_FILE = ROOT / "ecommerce_data" / "policies.json"


def check_refund_conditions(query: str = "", policy_area: str = "all", top_k: int = 3) -> dict[str, Any]:
    try:
        data = json.loads(POLICY_FILE.read_text(encoding="utf-8"))
        query_terms = terms(query)
        scored: list[tuple[int, dict[str, Any]]] = []

        for p in data["policies"]:
            if policy_area != "all" and p.get("category") != policy_area:
                continue
            text = f"{p.get('title', '')} {p.get('content', '')}"
            p_terms = terms(text)
            match_score = len(query_terms & p_terms)
            scored.append((match_score, p))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [item[1] for item in scored[:top_k]]
        return {
            "tool": "check_refund_conditions",
            "query": query,
            "policy_area": policy_area,
            "results": results,
            "snapshot_at": data["snapshot_at"]
        }
    except Exception as exc:
        return err("check_refund_conditions", exc)
