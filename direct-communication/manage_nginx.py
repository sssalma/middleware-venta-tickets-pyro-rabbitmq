import os
import sys
import subprocess
from pathlib import Path

NGINX_HOME = Path(os.environ.get("NGINX_HOME", r"C:\nginx"))
NGINX_BIN = str(NGINX_HOME / "nginx.exe")
NGINX_CONF_FILE = Path(
    os.environ.get("NGINX_CONF_PATH", str(NGINX_HOME / "conf" / "nginx.conf"))
)


def start_nginx():
    try:
        if os.name == "nt":
            subprocess.Popen(
                [
                    NGINX_BIN,
                    "-p", str(NGINX_HOME) + "\\",
                    "-c", str(NGINX_CONF_FILE)
                ],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            subprocess.Popen(
                [
                    NGINX_BIN,
                    "-p", str(NGINX_HOME),
                    "-c", str(NGINX_CONF_FILE)
                ]
            )

        print("NGINX lanzado correctamente.")
    except FileNotFoundError:
        print(f"No se encontró nginx.exe en: {NGINX_BIN}")
    except Exception as e:
        print(f"Error al iniciar NGINX: {e}")


def stop_nginx():
    try:
        result = subprocess.run(
            [
                NGINX_BIN,
                "-p", str(NGINX_HOME) + "\\",
                "-c", str(NGINX_CONF_FILE),
                "-s", "quit"
            ],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("NGINX detenido correctamente.")
        else:
            print("No se pudo detener NGINX.")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
    except FileNotFoundError:
        print(f"No se encontró nginx.exe en: {NGINX_BIN}")
    except Exception as e:
        print(f"Error al detener NGINX: {e}")


def help_msg():
    print("Uso:")
    print("  python manage_nginx.py start")
    print("  python manage_nginx.py stop")


def main():
    if len(sys.argv) != 2:
        help_msg()
        return

    cmd = sys.argv[1].lower()

    if cmd == "start":
        start_nginx()
    elif cmd == "stop":
        stop_nginx()
    else:
        help_msg()


if __name__ == "__main__":
    main()