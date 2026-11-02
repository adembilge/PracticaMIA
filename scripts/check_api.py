"""Run the health checks, including a live server."""
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / "backend" / ".venv"
PYTHON = VENV / "Scripts" / "python.exe" if sys.platform == "win32" else VENV / "bin" / "python"
if PYTHON.is_file() and Path(sys.executable).resolve() != PYTHON.resolve():
    raise SystemExit(subprocess.call([str(PYTHON), *sys.argv]))

HOST = "127.0.0.1"
PORT = 8000


def call(method, path):
    request = urllib.request.Request("http://%s:%s%s" % (HOST, PORT, path), method=method)
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def expect(method, path, status, body=None, contains=None):
    got, payload = call(method, path)
    if got != status:
        sys.exit("%s %s returned %s" % (method, path, got))
    if body is not None and json.loads(payload) != body:
        sys.exit("%s %s returned %s" % (method, path, payload.decode()))
    if contains is not None and contains.encode() not in payload:
        sys.exit("%s %s did not contain %s" % (method, path, contains))


def port_free():
    probe = socket.socket()
    try:
        probe.bind((HOST, PORT))
    except OSError:
        return False
    finally:
        probe.close()
    return True


def wait_until_up(proc):
    deadline = time.time() + 15
    while time.time() < deadline:
        if proc.poll() is not None:
            sys.exit("uvicorn exited")
        try:
            with socket.create_connection((HOST, PORT), timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    sys.exit("uvicorn did not accept a connection")


def live():
    if not port_free():
        sys.exit("port 8000 is in use")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--host", HOST, "--port", str(PORT)],
        cwd=ROOT / "backend",
    )
    try:
        wait_until_up(proc)
        ok = {"status": "ok"}
        expect("GET", "/health", 200, ok)
        expect("GET", "/v1/health", 200, ok)
        expect("POST", "/health", 405, {"code": "method_not_allowed", "message": "Method not allowed."})
        expect("GET", "/missing", 404, {"code": "not_found", "message": "Not found."})
        expect("GET", "/docs", 200, contains="swagger-ui")
        status, payload = call("GET", "/openapi.json")
        if status != 200 or "/health" not in json.loads(payload)["paths"]:
            sys.exit("openapi did not list /health")
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def main():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(ROOT / "backend" / "test_health.py"), "-q"],
        cwd=ROOT,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)
    live()
    print("api ok")


if __name__ == "__main__":
    main()
