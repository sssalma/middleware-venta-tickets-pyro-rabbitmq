import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATE_FILE = BASE_DIR / "worker_state.json"
BASE_PORT = 5001
REST_SERVER_PATH = BASE_DIR / "rest_server.py"

def load_state():
    if not STATE_FILE.exists():
        return {"workers": []}

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if "workers" not in data or not isinstance(data["workers"], list):
            return {"workers": []}
        return data
    except Exception:
        return {"workers": []}


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, indent=2),
        encoding="utf-8"
    )


def get_workers():
    state = load_state()
    workers = state.get("workers", [])
    workers = sorted(workers, key=lambda w: int(w["port"]))
    return workers


def get_next_port(workers):
    if not workers:
        return BASE_PORT
    return max(int(w["port"]) for w in workers) + 1


def get_last_worker(workers):
    if not workers:
        return None
    return max(workers, key=lambda w: int(w["port"]))


def is_port_open(port, host="127.0.0.1", timeout=0.5):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, int(port))) == 0


def wait_for_port(port, timeout_seconds=10):
    start = time.time()
    while time.time() - start < timeout_seconds:
        if is_port_open(port):
            return True
        time.sleep(0.2)
    return False


def start_worker_process(port):
    env = os.environ.copy()
    env["PORT"] = str(port)

    if not REST_SERVER_PATH.exists():
        raise FileNotFoundError(f"No se encontró {REST_SERVER_PATH.resolve()}")

    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_CONSOLE  # type: ignore[attr-defined]
        process = subprocess.Popen(
            [sys.executable, str(REST_SERVER_PATH)],
            env=env,
            creationflags=creationflags
        )
    else:
        process = subprocess.Popen(
            [sys.executable, str(REST_SERVER_PATH)],
            env=env
        )

    return process


def stop_worker_process(pid):
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            check=False,
            capture_output=True,
            text=True
        )
    else:
        try:
            os.kill(int(pid), signal.SIGTERM)
        except ProcessLookupError:
            pass


def add_worker_to_state(port, pid):
    state = load_state()
    workers = state.get("workers", [])

    workers.append({
        "port": int(port),
        "pid": int(pid)
    })

    state["workers"] = sorted(workers, key=lambda w: int(w["port"]))
    save_state(state)


def remove_worker_from_state(port):
    state = load_state()
    workers = state.get("workers", [])
    new_workers = [w for w in workers if int(w["port"]) != int(port)]
    state["workers"] = sorted(new_workers, key=lambda w: int(w["port"]))
    save_state(state)