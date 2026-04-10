from nginx_utils import reload_nginx, write_nginx_conf
from scaling_utils import (
    get_last_worker,
    get_workers,
    remove_worker_from_state,
    stop_worker_process
)


def main():
    workers = get_workers()

    if not workers:
        print("No hay workers activos para eliminar.")
        return

    worker_to_remove = get_last_worker(workers)
    port = int(worker_to_remove["port"])
    pid = int(worker_to_remove["pid"])

    print(f"Eliminando worker del puerto {port} con PID {pid}...")

    # 1. Eliminar del estado
    remove_worker_from_state(port)

    # 2. Parar el proceso REAL
    stop_worker_process(pid)

    # 3. Obtener estado actualizado
    updated_workers = get_workers()

    # 4. Reescribir nginx.conf
    write_nginx_conf(updated_workers)

    # 5. Recargar NGINX
    reload_nginx()

    print("Worker eliminado correctamente.")
    print(f"Puerto eliminado: {port}")
    print(f"PID eliminado: {pid}")
    print(f"Workers activos: {[w['port'] for w in updated_workers]}")


if __name__ == "__main__":
    main()