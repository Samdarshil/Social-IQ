"""MOCK Gemini REST server for testing. This is NOT Gemini and says so in every answer ("[MOCK-GEMINI]").

It speaks the real `models/{model}:generateContent` wire format so the REAL google-genai SDK and SocialIQ's real
tool loop run end to end. It validates what the SDK sends (API-key header, 13 function declarations, system
instruction, function responses, thought-signature echo) and picks tools with simple keyword rules.
It proves our integration code; it does NOT prove how real Gemini chooses tools.

Run standalone:  python tests/mock_gemini_server.py --port 9099
"""
from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SIG = "c2lnLTEyMw=="  # base64("sig-123"): a fake thought signature that must be echoed back unchanged
EXPECTED_TOOLS = {"get_channel_summary", "get_platform_metrics", "get_top_content", "get_content_details", "compare_platforms", "compare_periods",
                  "analyze_engagement", "find_best_publish_time", "analyze_categories", "detect_anomalies", "predict_content_performance",
                  "get_creator_profile", "generate_content_strategy"}


def pick_tool(text: str) -> tuple[str, dict]:
    t = text.lower()
    if "engagement" in t and any(k in t for k in ("why", "drop", "fell", "decline")):
        return "analyze_engagement", {"days": 28.0}          # float on purpose: real models often send 28.0
    if "post next" in t or "what should i post" in t or "strategy" in t:
        return "generate_content_strategy", {}
    if "best-performing" in t or "top content" in t or "best performing" in t:
        return "get_top_content", {"n": 5.0}
    if "platform" in t or "compare" in t:
        return "compare_platforms", {"days": 30.0}
    return "get_channel_summary", {"days": 30.0}


def summarize(frs: list[dict]) -> str:
    bits = []
    for fr in frs:
        res = fr["response"]
        if "error" in res:
            bits.append(f"{fr['name']} failed ({res['error']})")
            continue
        r = res.get("result", {})
        if fr["name"] == "analyze_engagement" and r.get("available"):
            bits.append(f"engagement changed {r['change_pct']:.1f}% (significant={r['significant']})")
        else:
            bits.append(f"{fr['name']} returned {len(r)} fields")
    return "Based on the tool results: " + "; ".join(bits) + "."


class Handler(BaseHTTPRequestHandler):
    server: "MockGemini"

    def log_message(self, *a):  # quiet
        pass

    def _send(self, code: int, body: dict):
        raw = json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(raw))); self.end_headers()
        self.wfile.write(raw)

    def _err(self, code: int, status: str, msg: str):
        self._send(code, {"error": {"code": code, "message": msg, "status": status}})

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        srv = self.server
        srv.log.append(dict(path=self.path, key=self.headers.get("x-goog-api-key"), body=body))
        if not self.path.endswith(":generateContent"):
            return self._err(404, "NOT_FOUND", "unknown method")
        if not self.headers.get("x-goog-api-key"):
            return self._err(401, "UNAUTHENTICATED", "missing key")
        mode = srv.mode
        if mode == "forbidden":
            return self._err(403, "PERMISSION_DENIED", "API key not valid")
        if mode == "http500":
            return self._err(500, "INTERNAL", "boom")
        if mode == "slow":
            time.sleep(3.5)
        if mode == "empty":
            return self._send(200, {"candidates": []})

        decls = [d["name"] for d in (body.get("tools") or [{}])[0].get("functionDeclarations", [])]
        if set(decls) != EXPECTED_TOOLS or len(decls) != 13:
            return self._err(400, "INVALID_ARGUMENT", f"unexpected tool set: {sorted(decls)}")
        if not (body.get("systemInstruction") or {}).get("parts"):
            return self._err(400, "INVALID_ARGUMENT", "missing system instruction")
        if body.get("tools") and any("functionDeclarations" not in t for t in body["tools"]):
            return self._err(400, "INVALID_ARGUMENT", "bad tools")

        contents = body["contents"]
        last = contents[-1]
        frs = [p["functionResponse"] for p in last.get("parts", []) if "functionResponse" in p]
        if frs:
            prev = contents[-2]
            sigs = [p.get("thoughtSignature") for p in prev.get("parts", []) if "functionCall" in p]
            if prev.get("role") != "model" or not sigs or any(s != SIG for s in sigs):
                return self._err(400, "INVALID_ARGUMENT", "thought signature was not echoed back unchanged")
            if mode == "badtool" and any("error" in f["response"] for f in frs):
                call = {"functionCall": {"name": "compare_platforms", "args": {"days": 30.0}}, "thoughtSignature": SIG}
                return self._send(200, {"candidates": [{"content": {"role": "model", "parts": [call]}, "finishReason": "STOP"}]})
            return self._send(200, {"candidates": [{"content": {"role": "model", "parts": [{"text": "[MOCK-GEMINI] " + summarize(frs)}]}, "finishReason": "STOP"}]})

        user_text = " ".join(p.get("text", "") for p in last.get("parts", []))
        if mode == "notool":
            return self._send(200, {"candidates": [{"content": {"role": "model", "parts": [{"text": "[MOCK-GEMINI] Your engagement is great, trust me."}]}, "finishReason": "STOP"}]})
        name, args = ("delete_everything", {}) if mode == "badtool" else pick_tool(user_text)
        call = {"functionCall": {"name": name, "args": args}, "thoughtSignature": SIG}
        return self._send(200, {"candidates": [{"content": {"role": "model", "parts": [call]}, "finishReason": "STOP"}]})


class MockGemini(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):  # client hung up (e.g. timeout test): not an error here
        pass

    def __init__(self, port: int = 0):
        super().__init__(("127.0.0.1", port), Handler)
        self.mode = "normal"
        self.log: list[dict] = []

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}"

    def start(self) -> "MockGemini":
        threading.Thread(target=self.serve_forever, daemon=True).start()
        return self


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=9099); ap.add_argument("--mode", default="normal")
    a = ap.parse_args()
    s = MockGemini(a.port); s.mode = a.mode
    print(f"MOCK Gemini (not real Gemini) listening on {s.url} mode={s.mode}", flush=True)
    s.serve_forever()
