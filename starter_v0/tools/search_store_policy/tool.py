from __future__ import annotations

import json
from typing import Any

from tools._shared import ROOT, err, terms


POLICY_FILE = ROOT / "ecommerce_data" / "policies.json"


def search_store_policy(query: str = "", category: str = "all", top_k: int = 3) -> dict[str, Any]:
    try:
        data = json.loads(POLICY_FILE.read_text(encoding="utf-8"))
        query_terms = terms(query)
        scored: list[tuple[int, dict[str, Any]]] = []

        for p in data["policies"]:
            if category != "all" and p.get("category") != category:
                continue
            text = f"{p.get('title', '')} {p.get('content', '')}"
            p_terms = terms(text)
            match_score = len(query_terms & p_terms)
            scored.append((match_score, p))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [item[1] for item in scored[:top_k]]
        return {
            "tool": "search_store_policy",
            "query": query,
            "category": category,
            "results": results,
            "snapshot_at": data["snapshot_at"]
        }
    except Exception as exc:
        return err("search_store_policy", exc)
