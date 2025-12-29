import argparse
import json
import socket
import sys
import time
import uuid

def send_frame(sock: socket.socket, obj: dict) -> None:
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    sock.sendall(len(data).to_bytes(4, "big") + data)

def recv_exact(sock: socket.socket, n: int) -> bytes:
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            return b""
        data += chunk
    return data

def recv_frame(sock: socket.socket) -> dict:
    header = recv_exact(sock, 4)
    if not header:
        raise ConnectionError("server closed connection")
    length = int.from_bytes(header, "big")
    payload = recv_exact(sock, length)
    if not payload:
        raise ConnectionError("server closed during payload")
    return json.loads(payload.decode("utf-8"))

def rpc_call(host: str, port: int, method: str, params: dict,
             timeout: float, retries: int) -> dict:
    request_id = str(uuid.uuid4())
    req = {
        "request_id": request_id,
        "method": method,
        "params": params,
        "timestamp": int(time.time()),
    }

    last_err = None

    for attempt in range(1, retries + 2):  # e.g. retries=2 => attempts: 1..3
        try:
            with socket.create_connection((host, port), timeout=timeout) as sock:
                sock.settimeout(timeout)
                send_frame(sock, req)
                resp = recv_frame(sock)

                # Validate matching request_id
                if resp.get("request_id") != request_id:
                    raise ValueError("Mismatched request_id in response")

                return resp

        except (socket.timeout, TimeoutError) as e:
            last_err = f"TIMEOUT (attempt {attempt}/{retries+1}): {e}"
        except (ConnectionError, OSError) as e:
            last_err = f"CONNECTION ERROR (attempt {attempt}/{retries+1}): {e}"
        except Exception as e:
            last_err = f"CLIENT ERROR (attempt {attempt}/{retries+1}): {type(e).__name__}: {e}"

        # Backoff before retry (small)
        if attempt <= retries + 1:
            time.sleep(0.2)

    return {
        "request_id": request_id,
        "status": "ERROR",
        "error": f"RPC failed after {retries+1} attempts. Last error: {last_err}",
    }

def main():
    parser = argparse.ArgumentParser(description="LAB1 RPC Client (timeouts, retries, request_id).")
    parser.add_argument("--host", required=True, help="Server public IP or hostname")
    parser.add_argument("--port", type=int, default=5000, help="Server port (default: 5000)")
    parser.add_argument("--timeout", type=float, default=2.0, help="Timeout seconds (default: 2.0)")
    parser.add_argument("--retries", type=int, default=2, help="Retries count (default: 2)")
    parser.add_argument("--method", required=True, choices=["add", "reverse_string", "get_time"], help="RPC method")
    parser.add_argument("--a", type=int, default=0, help="Param a (for add)")
    parser.add_argument("--b", type=int, default=0, help="Param b (for add)")
    parser.add_argument("--s", type=str, default="", help="Param s (for reverse_string)")
    args = parser.parse_args()

    if args.method == "add":
        params = {"a": args.a, "b": args.b}
    elif args.method == "reverse_string":
        params = {"s": args.s}
    else:
        params = {}

    resp = rpc_call(
        host=args.host,
        port=args.port,
        method=args.method,
        params=params,
        timeout=args.timeout,
        retries=args.retries,
    )

    if resp.get("status") == "OK":
        print(f"OK | request_id={resp.get('request_id')} | result={resp.get('result')}")
        sys.exit(0)
    else:
        print(f"ERROR | request_id={resp.get('request_id')} | error={resp.get('error')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
