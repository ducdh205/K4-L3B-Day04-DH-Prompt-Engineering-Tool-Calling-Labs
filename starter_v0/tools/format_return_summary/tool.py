from __future__ import annotations

from typing import Any

from tools._shared import err


def format_return_summary(
    findings: list[dict[str, Any]] | None = None,
    template: str = "brief",
    incident_title: str = "Customer Return Summary"
) -> dict[str, Any]:
    try:
        items = findings or []
        formatted_lines = [f"=== {incident_title} ({template.upper()}) ==="]
        for f in items:
            label = f.get("label", "Info")
            detail = f.get("detail", "")
            status = f.get("status", "OK")
            formatted_lines.append(f"- [{status}] {label}: {detail}")

        return {
            "tool": "format_return_summary",
            "title": incident_title,
            "template": template,
            "report_text": "\n".join(formatted_lines),
            "findings_count": len(items)
        }
    except Exception as exc:
        return err("format_return_summary", exc)
