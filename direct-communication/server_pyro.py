import sys
import os
import Pyro4
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from base.tickets import tickets
from base.redis_logica import RedisRepository


@Pyro4.expose
class TicketWorker(object):
    def __init__(self, worker_id):
        self.worker_id = worker_id
        self.request_count = 0

        repo = RedisRepository()
        self.servicio = tickets(repo)
        print(f"Worker {self.worker_id} inicializado y conectado a Redis.")

    def comprar(self, client_id, request_id, seat_id=None):
        self.request_count += 1

        # Retardo artificial para hacer visible el escalado dinámico
        time.sleep(0.01)

        if seat_id is None:
            resultado = self.servicio.comprar_no_numerada(client_id, request_id)
        else:
            resultado = self.servicio.comprar_numerada(client_id, seat_id, request_id)

        if self.request_count % 500 == 0:
            print(
                f"[Worker {self.worker_id}] "
                f"peticiones procesadas: {self.request_count} | "
                f"última request: {request_id} | "
                f"ok={resultado.ok}"
            )

        return resultado.ok

    def ping(self):
        return f"pong from worker {self.worker_id}"


def main():
    if len(sys.argv) < 2:
        print("Uso: python server_pyro.py <ID_DEL_WORKER>")
        sys.exit(1)

    worker_id = sys.argv[1]

    try:
        daemon = Pyro4.Daemon(host="0.0.0.0", nathost="127.0.0.1")
        ns = Pyro4.locateNS(host="127.0.0.1")

        worker = TicketWorker(worker_id)
        uri = daemon.register(worker)

        nombre_servidor = f"tickets.worker.{worker_id}"
        try:
            ns.remove(nombre_servidor)
        except Exception:
            pass

        ns.register(nombre_servidor, uri)

        print(f"Worker Pyro listo: {nombre_servidor}")
        print(f"URI: {uri}")

        daemon.requestLoop()

    except Exception as e:
        print(f"Error arrancando el worker: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()