import os
import subprocess
from pathlib import Path

NGINX_HOME = Path(os.environ.get("NGINX_HOME", r"C:\nginx"))
NGINX_BIN = str(NGINX_HOME / "nginx.exe")
NGINX_CONF_FILE = Path(os.environ.get("NGINX_CONF_PATH", str(NGINX_HOME / "conf" / "nginx.conf")))


def build_nginx_conf(workers):
    lines = [
        "worker_processes  1;",
        "",
        "events {",
        "    worker_connections  1024;",
        "}",
        "",
        "http {",
        "    upstream ticket_workers {",
        "        least_conn;"
    ]

    if not workers:
        # Dummy server para que NGINX no falle si no hay workers reales
        lines.append("        server 127.0.0.1:5999 down;")
    else:
        for worker in workers:
            port = int(worker["port"])
            lines.append(f"        server 127.0.0.1:{port} max_fails=2 fail_timeout=5s;")

    lines.extend([
        "    }",
        "",
        "    server {",
        "        listen 8080;",
        "",
        "        location / {",
        "            proxy_pass http://ticket_workers;",
        "            proxy_connect_timeout 1s;",
        "            proxy_read_timeout 5s;",
        "            proxy_send_timeout 5s;",
        "",
        "            proxy_set_header Host $host;",
        "            proxy_set_header X-Real-IP $remote_addr;",
        "        }",
        "    }",
        "}"
    ])

    return "\n".join(lines)


def write_nginx_conf(workers):
    content = build_nginx_conf(workers)
    NGINX_CONF_FILE.write_text(content, encoding="utf-8")


def reload_nginx():
    try:
        result = subprocess.run(
            [
                NGINX_BIN,
                "-p", str(NGINX_HOME) + "\\",
                "-c", str(NGINX_CONF_FILE),
                "-s", "reload"
            ],
            capture_output=True,
            text=True
        )
    except FileNotFoundError:
        raise RuntimeError(
            f"No se encontró nginx.exe en: {NGINX_BIN}"
        )

    if result.returncode != 0:
        raise RuntimeError(
            f"No se pudo recargar NGINX.\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )