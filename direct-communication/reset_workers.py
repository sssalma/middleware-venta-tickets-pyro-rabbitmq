from nginx_utils import write_nginx_conf, reload_nginx
from scaling_utils import load_state, save_state, stop_worker_process


def main():
    state = load_state()
    workers = state.get("workers", [])

    for worker in workers:
        pid = int(worker["pid"])
        stop_worker_process(pid)

    save_state({"workers": []})
    write_nginx_conf([])
    reload_nginx()

    print("Estado reiniciado correctamente.")
    print("Todos los workers eliminados del estado.")
    print("NGINX actualizado sin workers.")


if __name__ == "__main__":
    main()