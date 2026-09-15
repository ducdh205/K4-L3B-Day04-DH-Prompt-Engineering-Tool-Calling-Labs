#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from env_loader import load_lab_env
from providers import make_provider
from tools import TOOL_FUNCTIONS, load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).resolve().parent
ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPT_FILE = ARTIFACTS_DIR / "chat_transcript.json"
load_lab_env(ROOT)


def get_version_info() -> dict[str, Any]:
    sys_prompt_file = ARTIFACTS_DIR / "system_prompt.md"
    tools_file = ARTIFACTS_DIR / "tools.yaml"
    
    art_ver = build_artifact_version("v3", sys_prompt_file, tools_file)
    v_dict = artifact_version_dict(art_ver)
    v_dict["active_version"] = "v3"
    v_dict["transcript_path"] = str(TRANSCRIPT_FILE)
    return v_dict


def append_transcript(turn_data: dict[str, Any]) -> None:
    history: list[dict[str, Any]] = []
    if TRANSCRIPT_FILE.exists():
        try:
            history = json.loads(TRANSCRIPT_FILE.read_text(encoding="utf-8"))
        except Exception:
            history = []
    history.append(turn_data)
    TRANSCRIPT_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def run_mock_engine(user_message: str, history: list[dict[str, Any]], version: str = "v3") -> tuple[str, list[dict[str, Any]]]:
    """Smart local mock engine for offline testing if no live API key is set."""
    msg_lower = user_message.lower()
    
    # Check multi-turn context
    prev_content = history[-2]["content"].lower() if len(history) >= 2 and history[-2].get("role") == "assistant" else ""
    
    # 1. Order status
    if "ord-" in msg_lower or "đơn hàng" in msg_lower:
        match = re.search(r"ord-\d+", msg_lower, re.IGNORECASE)
        if match:
            ord_id = match.group(0).upper()
            return "Đã kiểm tra trạng thái đơn hàng giúp bạn.", [{"name": "check_order_status", "args": {"order_id": ord_id}}]
        elif "kiểm tra" in msg_lower or "tình trạng" in msg_lower or "ở đâu" in msg_lower:
            if version in ["v0"]:
                # Baseline v0 flaw: calls tool directly with missing argument
                return "Đang tra cứu đơn hàng...", [{"name": "check_order_status", "args": {}}]
            return "Bạn vui lòng cung cấp mã đơn hàng (Order ID, ví dụ ORD-8801) nhé?", [{"name": "clarify", "args": {"question": "Vui lòng cung cấp mã đơn hàng (Order ID)?"}}]

    # 2. Warranty
    if "serial" in msg_lower or "sn-" in msg_lower or "bảo hành" in msg_lower or "tai nghe" in msg_lower:
        match = re.search(r"sn-[a-z0-9-]+", msg_lower, re.IGNORECASE)
        if match:
            sn = match.group(0).upper()
            check_type = "bluetooth" if "bluetooth" in msg_lower else "all"
            return "Đã tra cứu thông tin bảo hành sản phẩm.", [{"name": "inspect_product_warranty", "args": {"serial_number": sn, "check": check_type}}]
        elif "bảo hành" in msg_lower:
            return "Bạn cho mình xin mã Serial Number của sản phẩm nhé?", [{"name": "clarify", "args": {"question": "Vui lòng cung cấp mã Serial Number?"}}]

    # 3. Customer lookup
    if "cust-" in msg_lower or "khách hàng" in msg_lower or "tài khoản" in msg_lower or "@" in msg_lower:
        match_id = re.search(r"cust-\d+", msg_lower, re.IGNORECASE)
        match_email = re.search(r"[\w.-]+@[\w.-]+\.\w+", msg_lower)
        if match_id:
            return "Đã tra cứu thông tin khách hàng.", [{"name": "lookup_customer", "args": {"customer_id": match_id.group(0).upper()}}]
        elif match_email:
            return "Đã tra cứu thông tin khách hàng qua email.", [{"name": "lookup_customer", "args": {"email": match_email.group(0)}}]

    # 4. Return ticket & confirmation
    if "tạo ticket" in msg_lower or "đổi trả" in msg_lower or "yêu cầu đổi" in msg_lower:
        if "đồng ý" in msg_lower or "xác nhận" in msg_lower or "đúng vậy" in msg_lower:
            match_ord = re.search(r"ord-\d+", msg_lower, re.IGNORECASE) or (re.search(r"ord-\d+", prev_content, re.IGNORECASE) if prev_content else None)
            ord_id = match_ord.group(0).upper() if match_ord else "ORD-8801"
            return "Đã khởi tạo ticket yêu cầu đổi trả hàng thành công.", [{"name": "create_return_ticket", "args": {"order_id": ord_id, "summary": "Yêu cầu đổi trả từ khách hàng", "confirmed": True}}]
        elif "hủy" in msg_lower or "không" in msg_lower or "thôi" in msg_lower:
            return "Đã hủy yêu cầu tạo ticket đổi trả theo mong muốn của bạn.", []
        else:
            if version in ["v0", "v1"]:
                # Old versions created ticket without waiting for confirmation
                match_ord = re.search(r"ord-\d+", msg_lower, re.IGNORECASE) or "ORD-8801"
                return "[v1/v0 Behavior] Đã tự động tạo ticket đổi trả.", [{"name": "create_return_ticket", "args": {"order_id": match_ord, "summary": "Lỗi sản phẩm", "confirmed": False}}]
            return "Bạn có chắc chắn muốn xác nhận tạo ticket đổi trả cho đơn hàng này không?", [{"name": "clarify", "args": {"question": "Bạn có chắc chắn xác nhận tạo ticket đổi trả?", "response_type": "yes_no"}}]

    # 5. Voucher bonus
    if "voucher" in msg_lower or "đền bù" in msg_lower:
        match_ord = re.search(r"ord-\d+", msg_lower, re.IGNORECASE)
        ord_id = match_ord.group(0).upper() if match_ord else "ORD-8801"
        if "đồng ý" in msg_lower or "phát hành" in msg_lower:
            return "Đã phát hành Voucher đền bù tự động thành công!", [{"name": "auto_generate_compensation_voucher", "args": {"order_id": ord_id, "reason": "shipping_delay", "amount_usd": 20.0, "confirmed": True}}]
        else:
            return "Xác nhận phát hành Voucher đền bù $20 cho đơn hàng này?", [{"name": "clarify", "args": {"question": "Xác nhận phát hành Voucher đền bù?"}}]

    # 6. Store policies
    if "giao hàng" in msg_lower or "phí ship" in msg_lower or "chính sách" in msg_lower or "vận chuyển" in msg_lower:
        if version in ["v0", "v1"] and ("giao hàng" in msg_lower and "phí ship" in msg_lower):
            # Demonstrates extra_tool_call failure in v0/v1 when prompt didn't restrict single call
            return "[v1 Behavior] Đã tra cứu cả 2 mục giao hàng và phí ship.", [
                {"name": "search_store_policy", "args": {"category": "shipping", "query": "giao hàng"}},
                {"name": "search_store_policy", "args": {"category": "shipping", "query": "phí ship"}}
            ]
        return "Đã tra cứu chính sách của shop.", [{"name": "search_store_policy", "args": {"category": "shipping"}}]

    # 7. Refund conditions
    if "hoàn tiền" in msg_lower or "trả tiền" in msg_lower:
        return "Đã tra cứu điều kiện hoàn tiền.", [{"name": "check_refund_conditions", "args": {"policy_area": "refunds", "query": user_message}}]

    # 8. Specs
    if "thông số" in msg_lower or "cấu hình" in msg_lower or "specs" in msg_lower:
        return "Đã tra cứu thông số kỹ thuật sản phẩm.", [{"name": "search_product_specs", "args": {"manufacturer": "Sony", "model": "WH-1000XM5", "query_type": "specs"}}]

    # 9. Out of scope
    if any(kw in msg_lower for kw in ["thời tiết", "phở", "thơ", "lập trình", "python", "ngân hàng"]):
        return "Rất tiếc, mình là Trợ lý CSKH E-Commerce nên chỉ hỗ trợ các thông tin liên quan đến đơn hàng, sản phẩm và bảo hành!", []

    return "Mình có thể giúp bạn kiểm tra đơn hàng, bảo hành hoặc chính sách đổi trả!", []


def synthesize_response(tool_results: list[dict[str, Any]], default_reply: str, version: str) -> str:
    """Synthesizes clear natural language response from tool execution outputs."""
    if not tool_results:
        return default_reply or "Mình có thể giúp bạn kiểm tra đơn hàng, bảo hành hoặc chính sách đổi trả!"
    
    parts = []
    for tr in tool_results:
        tool_name = tr.get("tool")
        res = tr.get("result", {})
        
        if tool_name == "check_order_status":
            order = res.get("order")
            if order:
                parts.append(
                    f"Đơn hàng **{order.get('order_id')}** ({order.get('product_name')}) "
                    f"đã được giao thành công (**{order.get('status')}**) vào ngày **{order.get('delivered_date')}** "
                    f"qua đơn vị vận chuyển **{order.get('carrier')}** (Mã vận đơn: **{order.get('tracking_number')}**)."
                )
            elif "error" in res:
                parts.append(f"Không tìm thấy thông tin đơn hàng ({res.get('message')}).")
                
        elif tool_name == "inspect_product_warranty":
            w = res.get("warranty")
            if w:
                diag = w.get("diagnostics", {})
                bt_status = diag.get("bluetooth", "ok")
                bt_info = f", Lỗi Bluetooth: `{bt_status}`" if bt_status != "ok" else ""
                parts.append(
                    f"Sản phẩm **{w.get('product_name')}** (Serial: **{w.get('serial_number')}**) "
                    f"hiện có hạn bảo hành đến **{w.get('expires_at')}** (Trạng thái: **{w.get('warranty_status')}**{bt_info})."
                )
            elif "error" in res:
                parts.append("Không tìm thấy thông tin bảo hành cho mã serial này.")
                
        elif tool_name == "lookup_customer":
            cust = res.get("customer")
            if cust:
                parts.append(
                    f"Thông tin tài khoản khách hàng **{cust.get('name')}** (ID: **{cust.get('customer_id')}**): "
                    f"Email: {cust.get('email')}, Hạng tài khoản: **{cust.get('tier')}**, Điểm tích lũy: {cust.get('points')} điểm."
                )
            elif "error" in res:
                parts.append("Không tìm thấy thông tin khách hàng.")
                
        elif tool_name == "search_store_policy":
            results = res.get("results", [])
            if results:
                p_text = " | ".join([f"**{item.get('title')}**: {item.get('content')}" for item in results])
                parts.append(f"Chính sách shop: {p_text}")
            else:
                parts.append("Đã tra cứu chính sách cửa hàng.")

        elif tool_name == "check_refund_conditions":
            results = res.get("results", [])
            if results:
                p_text = " | ".join([f"**{item.get('title')}**: {item.get('content')}" for item in results])
                parts.append(f"Điều kiện hoàn tiền: {p_text}")
            else:
                parts.append("Đã tra cứu điều kiện hoàn tiền.")
                
        elif tool_name == "search_product_specs":
            specs = res.get("specs")
            if specs:
                parts.append(f"Thông số kỹ thuật {specs.get('manufacturer')} {specs.get('model')}: {specs.get('summary')}")
            else:
                parts.append("Đã tra cứu thông số kỹ thuật sản phẩm.")

        elif tool_name == "create_return_ticket":
            if res.get("status") == "created":
                parts.append(f"Đã khởi tạo thành công Ticket đổi trả **{res.get('ticket_id')}** cho đơn hàng **{res.get('order_id')}**.")
            elif res.get("status") == "unconfirmed_warning":
                parts.append("Cần sự xác nhận của khách hàng trước khi tạo ticket đổi trả.")
            else:
                parts.append(default_reply or "Yêu cầu đổi trả đã được ghi nhận.")

        elif tool_name == "auto_generate_compensation_voucher":
            if res.get("status") == "issued":
                parts.append(f"Đã phát hành thành công Voucher đền bù **{res.get('voucher_code')}** trị giá **${res.get('amount_usd')}** cho đơn hàng **{res.get('order_id')}**!")
            else:
                parts.append(default_reply or "Cần sự xác nhận trước khi phát hành voucher đền bù.")

        elif tool_name == "clarify":
            q = tr.get("args", {}).get("question") or default_reply
            parts.append(q)

    if parts:
        return "\n\n".join(parts)
    return default_reply or "Đã xử lý xong yêu cầu của bạn."


def process_chat(payload: dict[str, Any]) -> dict[str, Any]:
    user_msg = payload.get("message", "").strip()
    history = payload.get("history", [])
    provider_name = payload.get("provider", "openrouter")
    version = payload.get("version", "v3")
    
    sys_prompt = (ARTIFACTS_DIR / "system_prompt.md").read_text(encoding="utf-8")
    declarations = load_tool_declarations(ARTIFACTS_DIR / "tools.yaml")
    openai_tools = to_openai_tools(declarations)
    
    tool_calls_data: list[dict[str, Any]] = []
    reply_text: str = ""
    
    # Try live provider complete first if provider exists and has API key
    used_live = False
    try:
        prov = make_provider(provider_name)
        messages = [{"role": "system", "content": sys_prompt}]
        for turn in history:
            messages.append({"role": turn.get("role", "user"), "content": turn.get("content", "")})
        messages.append({"role": "user", "content": user_msg})
        
        resp = prov.complete(messages, openai_tools, temperature=0.0)
        reply_text = resp.text or ""
        for call in resp.tool_calls:
            tool_calls_data.append({"name": call.name, "args": call.args})
        used_live = True
    except Exception:
        # Fallback to local deterministic mock engine with version logic
        reply_text, tool_calls_data = run_mock_engine(user_msg, history, version=version)

    # Execute tool functions
    tool_results: list[dict[str, Any]] = []
    for call in tool_calls_data:
        t_name = call["name"]
        t_args = call.get("args", {})
        func = TOOL_FUNCTIONS.get(t_name)
        if func:
            try:
                res = func(**t_args)
            except Exception as exc:
                res = {"tool": t_name, "error": type(exc).__name__, "message": str(exc)}
        else:
            res = {"tool": t_name, "error": "unknown_tool"}
        tool_results.append({"tool": t_name, "args": t_args, "result": res})

    # Synthesize informative natural language reply from tool execution results
    if tool_results:
        final_reply = synthesize_response(tool_results, reply_text, version)
    else:
        final_reply = reply_text or "Mình có thể giúp bạn kiểm tra đơn hàng, bảo hành hoặc chính sách đổi trả!"

    version_info = get_version_info()
    turn_record = {
        "version": version,
        "timestamp": version,
        "user_message": user_msg,
        "reply": final_reply,
        "tool_calls": tool_calls_data,
        "tool_results": tool_results,
        "used_live_provider": used_live
    }
    append_transcript(turn_record)
    
    return {
        "reply": final_reply,
        "tool_calls": tool_calls_data,
        "tool_results": tool_results,
        "version": version,
        "transcript_path": str(TRANSCRIPT_FILE),
        "used_live": used_live
    }


HTML_CONTENT = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Northstar E-Store — AI CSKH Assistant (v3)</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0f172a;
            --panel-bg: rgba(30, 41, 59, 0.7);
            --panel-border: rgba(255, 255, 255, 0.1);
            --accent-blue: #38bdf8;
            --accent-purple: #818cf8;
            --accent-emerald: #34d399;
            --accent-amber: #fbbf24;
            --accent-rose: #f43f5e;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --user-bubble: #2563eb;
            --ai-bubble: #1e293b;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Outfit', sans-serif; }

        body {
            background-color: var(--bg-dark);
            background-image: 
                radial-gradient(at 0% 0%, rgba(56, 189, 248, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(129, 140, 248, 0.15) 0px, transparent 50%);
            color: var(--text-main);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        header {
            background: var(--panel-bg);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--panel-border);
            padding: 16px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 10;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .brand-icon {
            width: 38px;
            height: 38px;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 20px;
            color: #fff;
            box-shadow: 0 4px 14px rgba(56, 189, 248, 0.3);
        }

        .brand-title {
            font-size: 18px;
            font-weight: 600;
            color: var(--text-main);
        }

        .brand-subtitle {
            font-size: 12px;
            color: var(--text-muted);
        }

        .header-controls {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .version-select {
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--accent-purple);
            color: var(--accent-blue);
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            outline: none;
            cursor: pointer;
        }

        .badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .badge-version {
            background: rgba(52, 211, 153, 0.15);
            color: var(--accent-emerald);
            border: 1px solid rgba(52, 211, 153, 0.3);
        }

        .btn-transcript {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--panel-border);
            color: var(--text-main);
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .btn-transcript:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: var(--accent-blue);
        }

        main {
            flex: 1;
            display: flex;
            flex-direction: column;
            max-width: 1000px;
            width: 100%;
            margin: 0 auto;
            padding: 20px;
            overflow: hidden;
        }

        #chat-container {
            flex: 1;
            overflow-y: auto;
            padding-right: 8px;
            display: flex;
            flex-direction: column;
            gap: 18px;
        }

        #chat-container::-webkit-scrollbar {
            width: 6px;
        }
        #chat-container::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
        }

        .message-row {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-width: 85%;
        }

        .message-row.user {
            align-self: flex-end;
            align-items: flex-end;
        }

        .message-row.assistant {
            align-self: flex-start;
            align-items: flex-start;
        }

        .bubble {
            padding: 14px 18px;
            border-radius: 16px;
            font-size: 14.5px;
            line-height: 1.5;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }

        .message-row.user .bubble {
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            color: #ffffff;
            border-bottom-right-radius: 4px;
        }

        .message-row.assistant .bubble {
            background: var(--ai-bubble);
            border: 1px solid var(--panel-border);
            color: var(--text-main);
            border-bottom-left-radius: 4px;
        }

        /* Tool Call Cards */
        .tool-card {
            width: 100%;
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-radius: 12px;
            padding: 12px 16px;
            margin-top: 6px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            font-size: 13px;
        }

        .tool-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .tool-name-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(56, 189, 248, 0.15);
            color: var(--accent-blue);
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 6px;
            border: 1px solid rgba(56, 189, 248, 0.3);
        }

        .tool-section-title {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            margin-bottom: 4px;
            font-weight: 600;
        }

        .json-block {
            background: #090d16;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 10px 12px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            color: #cbd5e1;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 200px;
            overflow-y: auto;
        }

        .json-block.result-ok {
            border-left: 3px solid var(--accent-emerald);
        }

        .json-block.result-err {
            border-left: 3px solid var(--accent-rose);
        }

        /* Quick Suggestions */
        .suggestions {
            display: flex;
            gap: 8px;
            overflow-x: auto;
            padding: 8px 4px 14px 4px;
            margin-bottom: 8px;
            scrollbar-width: thin;
            scrollbar-color: rgba(56, 189, 248, 0.4) transparent;
        }

        .suggestions::-webkit-scrollbar {
            height: 4px;
        }

        .suggestions::-webkit-scrollbar-thumb {
            background: rgba(56, 189, 248, 0.4);
            border-radius: 4px;
        }

        .chip {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid var(--panel-border);
            color: var(--text-main);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 13px;
            white-space: nowrap;
            cursor: pointer;
            user-select: none;
            flex-shrink: 0;
            transition: all 0.2s ease;
        }

        .chip:hover {
            background: rgba(56, 189, 248, 0.25);
            color: #ffffff;
            border-color: var(--accent-blue);
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.4);
        }

        .chip:active {
            transform: scale(0.95);
        }

        /* Input Bar */
        .input-bar {
            background: var(--panel-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--panel-border);
            border-radius: 14px;
            padding: 8px 12px;
            display: flex;
            align-items: center;
            gap: 10px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
        }

        .input-bar input {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: var(--text-main);
            font-size: 15px;
            padding: 6px;
        }

        .input-bar button {
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 10px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.1s;
        }

        .input-bar button:active {
            transform: scale(0.96);
        }

        /* Transcript Modal */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(6px);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 100;
        }

        .modal-body {
            background: #1e293b;
            border: 1px solid var(--panel-border);
            border-radius: 16px;
            width: 90%;
            max-width: 800px;
            max-height: 80vh;
            display: flex;
            flex-direction: column;
            padding: 24px;
            gap: 16px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .modal-title { font-size: 18px; font-weight: 600; }
        .modal-close { cursor: pointer; font-size: 20px; color: var(--text-muted); }

        #transcript-json {
            flex: 1;
            background: #090d16;
            border-radius: 10px;
            padding: 16px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            color: #34d399;
            overflow-y: auto;
            white-space: pre-wrap;
        }
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <div class="brand-icon">N</div>
            <div>
                <div class="brand-title">Northstar CSKH AI Assistant</div>
                <div class="brand-subtitle">Smart E-Commerce Tool Calling Demo (v0 - v3)</div>
            </div>
        </div>
        <div class="header-controls">
            <label style="font-size: 12px; color: var(--text-muted);">Phiên bản:</label>
            <select class="version-select" id="version-select" onchange="onVersionChange()">
                <option value="v3" selected>🚀 Version v3 (100% PASS - Final Prompt & Rules)</option>
                <option value="v2">⚙️ Version v2 (93.3% - Clarify Tuning)</option>
                <option value="v1">🛠️ Version v1 (83.3% - Tools Refined)</option>
                <option value="v0">🔴 Version v0 (63.3% - Unoptimized Baseline)</option>
            </select>
            <span class="badge badge-version" id="active-badge">🚀 v3 (100%)</span>
            <button class="btn-transcript" onclick="openTranscript()">📄 Xem Transcript</button>
        </div>
    </header>

    <main>
        <div id="chat-container">
            <div class="message-row assistant">
                <div class="bubble" id="welcome-bubble">
                    Xin chào! Mình là Trợ lý CSKH tự động của Northstar E-Store. <br>
                    Đang ở phiên bản <b>Version v3</b> (Đạt độ chính xác 100%). Bạn có thể chuyển đổi giữa các phiên bản (v0, v1, v2, v3) ở thanh công cụ để so sánh hành vi gọi tool!
                </div>
            </div>
        </div>

        <div class="suggestions">
            <div class="chip" onclick="sendQuick('Kiểm tra trạng thái đơn hàng ORD-8801')">📦 Đơn ORD-8801</div>
            <div class="chip" onclick="sendQuick('Kiểm tra bảo hành tai nghe serial SN-SNY-9921')">🎧 Bảo hành SN-SNY-9921</div>
            <div class="chip" onclick="sendQuick('Cho mình tìm quy định về giao hàng và phí ship của shop.')">🔍 Policy Giao hàng & Phí ship</div>
            <div class="chip" onclick="sendQuick('Tôi muốn tạo ticket đổi trả đơn ORD-8801')">🎫 Đổi trả ORD-8801 (Xác nhận)</div>
            <div class="chip" onclick="sendQuick('Mình đồng ý tạo ticket đổi trả')">✅ Đồng ý xác nhận</div>
            <div class="chip" onclick="sendQuick('Phát hành voucher đền bù 20$ cho đơn ORD-8801, mình đồng ý')">🎁 Bonus Voucher $20</div>
            <div class="chip" onclick="sendQuick('Viết giúp tôi một bài thơ về tình yêu.')">🛑 Out of Scope (Từ chối)</div>
        </div>

        <div class="input-bar">
            <input type="text" id="user-input" placeholder="Nhập câu hỏi (ví dụ: Kiểm tra đơn ORD-8801 hoặc Cho mình tìm quy định giao hàng và phí ship)..." onkeydown="if(event.key==='Enter') sendMessage()">
            <button onclick="sendMessage()">Gửi</button>
        </div>
    </main>

    <div class="modal-overlay" id="transcript-modal">
        <div class="modal-body">
            <div class="modal-header">
                <div class="modal-title">📜 Session Transcript Log (artifacts/chat_transcript.json)</div>
                <div class="modal-close" onclick="closeTranscript()">✖</div>
            </div>
            <div id="transcript-json">Đang tải transcript...</div>
        </div>
    </div>

    <script>
        const chatContainer = document.getElementById('chat-container');
        const userInput = document.getElementById('user-input');
        const versionSelect = document.getElementById('version-select');
        const activeBadge = document.getElementById('active-badge');
        let chatHistory = [];

        function onVersionChange() {
            const ver = versionSelect.value;
            if (ver === 'v3') activeBadge.textContent = '🚀 v3 (100%)';
            else if (ver === 'v2') activeBadge.textContent = '⚙️ v2 (93.3%)';
            else if (ver === 'v1') activeBadge.textContent = '🛠️ v1 (83.3%)';
            else activeBadge.textContent = '🔴 v0 (63.3%)';

            const row = document.createElement('div');
            row.className = 'message-row assistant';
            row.innerHTML = `<div class="bubble" style="border-left: 3px solid var(--accent-purple);">🔄 Đã chuyển sang chế độ <b>Version ${ver}</b>. Hãy thử gửi lại câu hỏi để quan sát điểm khác biệt trong tool calls!</div>`;
            chatContainer.appendChild(row);
            scrollToBottom();
        }

        function appendUserMessage(text) {
            const row = document.createElement('div');
            row.className = 'message-row user';
            row.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
            chatContainer.appendChild(row);
            scrollToBottom();
        }

        function formatMarkdown(text) {
            if (!text) return '';
            let html = escapeHtml(text);
            html = html.replace(/\*\*(.*?)\*\*/g, '<strong style="color: #38bdf8; font-weight: 600;">$1</strong>');
            html = html.replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.1);padding:2px 6px;border-radius:4px;font-family:monospace;color:#34d399;">$1</code>');
            html = html.replace(/\n/g, '<br>');
            return html;
        }

        function appendAssistantMessage(data) {
            const row = document.createElement('div');
            row.className = 'message-row assistant';
            
            let html = `<div class="bubble">${formatMarkdown(data.reply)}</div>`;

            if (data.tool_calls && data.tool_calls.length > 0) {
                data.tool_calls.forEach((call, idx) => {
                    const resultObj = (data.tool_results && data.tool_results[idx]) ? data.tool_results[idx].result : null;
                    const isErr = resultObj && resultObj.error;

                    html += `
                        <div class="tool-card">
                            <div class="tool-header">
                                <span class="tool-name-badge">🛠️ Tool Called: ${call.name}</span>
                                <span style="font-size: 11px; color: #94a3b8;">Artifact Version: ${data.version || versionSelect.value}</span>
                            </div>
                            <div>
                                <div class="tool-section-title">📥 Input Arguments</div>
                                <div class="json-block">${escapeHtml(JSON.stringify(call.args, null, 2))}</div>
                            </div>
                            <div>
                                <div class="tool-section-title">📤 Tool Output / Result</div>
                                <div class="json-block ${isErr ? 'result-err' : 'result-ok'}">${escapeHtml(JSON.stringify(resultObj, null, 2))}</div>
                            </div>
                        </div>
                    `;
                });
            }

            row.innerHTML = html;
            chatContainer.appendChild(row);
            scrollToBottom();
        }

        async function sendMessage() {
            const inputEl = document.getElementById('user-input');
            if (!inputEl) return;
            const text = inputEl.value.trim();
            if (!text) return;

            const versionEl = document.getElementById('version-select');
            const currentVer = (versionEl && versionEl.value) ? versionEl.value : 'v3';

            appendUserMessage(text);
            inputEl.value = '';

            chatHistory.push({ role: 'user', content: text });

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text, history: chatHistory, version: currentVer })
                });
                const data = await response.json();
                appendAssistantMessage(data);

                chatHistory.push({ role: 'assistant', content: data.reply || '' });
            } catch (err) {
                console.error('Chat error:', err);
                appendAssistantMessage({ reply: 'Có lỗi kết nối tới server UI backend!', tool_calls: [] });
            }
        }

        function sendQuick(text) {
            const inputEl = document.getElementById('user-input');
            if (inputEl) {
                inputEl.value = text;
            }
            sendMessage();
        }

        function scrollToBottom() {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }

        async function openTranscript() {
            document.getElementById('transcript-modal').style.display = 'flex';
            try {
                const res = await fetch('/api/transcript');
                const json = await res.json();
                document.getElementById('transcript-json').textContent = JSON.stringify(json, null, 2);
            } catch (err) {
                document.getElementById('transcript-json').textContent = "Chưa có transcript log nào được ghi.";
            }
        }

        function closeTranscript() {
            document.getElementById('transcript-modal').style.display = 'none';
        }
    </script>
</body>
</html>
"""


class WebUIRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode("utf-8"))
        elif parsed.path == "/api/version":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(get_version_info()).encode("utf-8"))
        elif parsed.path == "/api/transcript":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            data = []
            if TRANSCRIPT_FILE.exists():
                try:
                    data = json.loads(TRANSCRIPT_FILE.read_text(encoding="utf-8"))
                except Exception:
                    data = []
            self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
        else:
            self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/chat":
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len)
            try:
                payload = json.loads(body_bytes.decode("utf-8"))
                response_data = process_chat(payload)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
            except Exception as exc:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))
        else:
            self.send_error(404, "Not Found")

    def log_message(self, format: str, *args: Any) -> None:
        pass  # Suppress noisy HTTP logs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Day04 Web Chat UI Server.")
    parser.add_argument("--port", type=int, default=8000, help="Port to run web UI server on.")
    args = parser.parse_args()

    server_address = ("", args.port)
    httpd = HTTPServer(server_address, WebUIRequestHandler)
    print(f"[Web UI] Northstar E-Commerce Web UI Server running at http://localhost:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Web UI server.")


if __name__ == "__main__":
    main()
