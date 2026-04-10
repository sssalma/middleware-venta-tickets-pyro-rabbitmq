from nginx_utils import reload_nginx, write_nginx_conf
from scaling_utils import (
    add_worker_to_state,
    get_next_port,
    get_workers,
    start_worker_process,
    wait_for_port
)


def main():
    workers = get_workers()
    new_port = get_next_port(workers)

    print(f"Iniciando nuevo worker en el puerto {new_port}...")
    process = start_worker_process(new_port)

    if not wait_for_port(new_port, timeout_seconds=10):
        print(f"ERROR: el worker del puerto {new_port} no respondió a tiempo.")
        print("No se modificará ni el estado ni NGINX.")
        return

    add_worker_to_state(new_port, process.pid)
    updated_workers = get_workers()

    write_nginx_conf(updated_workers)
    reload_nginx()

    print("Worker añadido correctamente.")
    print(f"Puerto: {new_port}")
    print(f"PID: {process.pid}")
    print(f"Workers activos: {[w['port'] for w in updated_workers]}")


if __name__ == "__main__":
    main()