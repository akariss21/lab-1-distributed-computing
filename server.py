import argparse
import json
import logging
import random
import socket
import threading
import time
from datetime import datetime, timezone

def add(a: int, b: int) -> int:
    return a + b

def reverse_string(s: str) -> str:
    return s[::-1]

def get_time() -> str:
    return datetime.now(timezone.utc).isoformat()

METHODS = {
    "add": add,
    "reverse_string": reverse_string,
    "get_time": get_time,
}

def recv_exact(conn: socket.socket, n: int) -> bytes:
    data = b""
    while len(data) < n:
        chunk = conn.recv(n - len(data))
        if not chunk:
            return b""
        data += chunk
    return data

def recv_frame(conn: socket.socket) -> dict:
    header = recv_exact(conn, 4)
    if not header:
        raise ConnectionError("client disconnected")
    length = int.from_bytes(header, "big")
    payload = recv_exact(conn, length)
    if not payload:
        raise ConnectionError("client disconnected during payload")
    return json.loads(payload.decode("utf-8"))

def send_frame(conn: socket.socket, obj: dict) -> None:
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    conn.sendall(len(data).to_bytes(4, "big") + data)

class RequestCache:
    """
    If enabled: returns the same response for repeated request_id,
    preventing duplicate side effects (at-most-once behavior for deterministic methods).
    """
    def __init__(self, enabled: bool):
        self.enabled = enabled
        self._lock = threading.Lock()
        self._cache = {}  # request_id -> response dict

    def get(self, request_id: str):
        if not self.enabled:
            return None
        with self._lock:
            return self._cache.get(request_id)

    def put(self, request_id: str, response: dict):
        if not self.enabled:
            return
        with self._lock:
            self._cache[request_id] = response

def handle_client(conn: socket.socket, addr, args, cache: RequestCache):
    logging.info("Client connected: %s:%s", addr[0], addr[1])
    with conn:
        while True:
            try:
                req = recv_frame(conn)
                request_id = str(req.get("request_id", ""))
                method = str(req.get("method", ""))
                params = req.get("params", {}) or {}

                logging.info("REQ id=%s method=%s params=%s", request_id, method, params)

                # If caching enabled and repeated request_id: return cached response
                cached = cache.get(request_id)
                if cached is not None:
                    logging.info("CACHE HIT id=%s", request_id)
                    send_frame(conn, cached)
                    continue

                # Artificial delay (for timeout/retry demo)
                if args.delay_seconds > 0:
                    logging.warning("Artificial delay: sleep %ss", args.delay_seconds)
                    time.sleep(args.delay_seconds)

                # Optional: randomly drop response (simulate packet loss)
                if args.drop_rate > 0 and random.random() < args.drop_rate:
                    logging.warning("Dropping response intentionally (drop_rate=%.2f)", args.drop_rate)
                    # do not send anything -> client timeout + retry
                    continue

                if method not in METHODS:
                    resp = {
                        "request_id": request_id,
                        "status": "ERROR",
                        "error": f"Unknown method: {method}",
                    }
                    cache.put(request_id, resp)
                    send_frame(conn, resp)
                    continue

                # Execute method
                try:
                    if method == "add":
                        result = METHODS[method](int(params.get("a")), int(params.get("b")))
                    elif method == "reverse_string":
                        result = METHODS[method](str(params.get("s", "")))
                    elif method == "get_time":
                        result = METHODS[method]()
                    else:
                        # fallback (not used here)
                        result = METHODS[method](**params)
                    resp = {
                        "request_id": request_id,
                        "status": "OK",
                        "result": result,
                    }
                except Exception as e:
                    resp = {
                        "request_id": request_id,
                        "status": "ERROR",
                        "error": f"Execution error: {type(e).__name__}: {e}",
                    }

                cache.put(request_id, resp)
                send_frame(conn, resp)

            except (ConnectionError, OSError) as e:
                logging.info("Client disconnected: %s (%s)", addr, e)
                break
            except Exception as e:
                logging.exception("Unexpected server error: %s", e)
                break

def main():
    parser = argparse.ArgumentParser(description="LAB1 RPC Server (TCP, JSON, retries-friendly).")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5000, help="Bind port (default: 5000)")
    parser.add_argument("--delay-seconds", type=float, default=0.0, help="Artificial delay before responding")
    parser.add_argument("--drop-rate", type=float, default=0.0, help="Drop responses probability [0..1]")
    parser.add_argument("--at-most-once", action="store_true", help="Enable request_id cache (at-most-once)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    cache = RequestCache(enabled=args.at_most_once)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((args.host, args.port))
        s.listen(50)
        logging.info("RPC Server listening on %s:%d", args.host, args.port)
        logging.info("Options: delay_seconds=%.2f drop_rate=%.2f at_most_once=%s",
                     args.delay_seconds, args.drop_rate, args.at_most_once)

        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr, args, cache), daemon=True)
            t.start()

if __name__ == "__main__":
    main()
