import json
import sys
import time
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:8000"


def request_json(method: str, path: str, payload=None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"detail": body}
        return exc.code, parsed


def wait_for_server(timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            status, body = request_json("GET", "/health")
            if status == 200:
                print("Server is ready.")
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def main():
    print("Waiting for server...")
    if not wait_for_server():
        print("Server did not start in time.")
        return 1

    status, logs = request_json("GET", "/api/logs")
    print("GET /api/logs ->", status, logs)

    payload = {
        "task_name": "smoke test",
        "user_prompt": "Return a short acknowledgement that the API is working.",
    }
    status, result = request_json("POST", "/api/run-automation", payload)
    print("POST /api/run-automation ->", status, result)

    return 0 if status == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
