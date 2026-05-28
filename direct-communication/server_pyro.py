import sys
import os
import Pyro4
import time

Pyro4.config.SERVERTYPE = "thread"
Pyro4.config.THREADPOOL_SIZE = 100
Pyro4.config.THREADPOOL_SIZE_MIN = 20

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from base.tickets import tickets
from base.redis_logica import RedisRepository


@Pyro4.expose
class TicketWorker(object):
    def __init__(self, worker_id):
        # guardamos el id del worker para poder distinguirlo en los logs
        self.worker_id = worker_id
        self.request_count = 0

        # conectamos con la logica de tickets usando redis como backend
        repo = RedisRepository()
        self.servicio = tickets(repo)

        print(f"Worker {self.worker_id} inicializado y conectado a Redis.")

    def comprar(self, client_id, request_id, seat_id=None):
        # metodo remoto que llama el frontend cuando quiere procesar una compra
        try:
            self.request_count += 1

            # si no viene asiento, es una compra no numerada
            if seat_id is None:
                resultado = self.servicio.comprar_no_numerada(client_id, request_id)

            # si viene asiento, se trata de una compra numerada
            else:
                seat_id = int(seat_id)
                resultado = self.servicio.comprar_numerada(client_id, seat_id, request_id)

            # cada cierto numero de peticiones imprimimos algo para ver que sigue vivo
            if self.request_count % 500 == 0:
                print(
                    f"[Worker {self.worker_id}] "
                    f"procesadas={self.request_count} "
                    f"última={request_id} "
                    f"ok={resultado.ok}",
                    flush=True
                )

            return resultado.ok

        except Exception as e:
            # si algo falla, no tiramos el worker entero
            print(f"[Worker {self.worker_id}] ERROR: {e}", flush=True)
            return False


def main():
    # cada worker necesita un id para registrarse como tickets.worker.X
    if len(sys.argv) < 2:
        print("Uso: python server_pyro.py <ID_DEL_WORKER>")
        sys.exit(1)

    worker_id = sys.argv[1]

    try:
        # el daemon escucha peticiones pyro desde fuera de la maquina
        daemon = Pyro4.Daemon(host="0.0.0.0", nathost="192.168.1.131")

        # localizamos el name server del portatil/host
        ns = Pyro4.locateNS(host="192.168.1.131")

        worker = TicketWorker(worker_id)
        uri = daemon.register(worker)

        nombre_servidor = f"tickets.worker.{worker_id}"

        # si habia un registro viejo con el mismo nombre, lo quitamos
        try:
            ns.remove(nombre_servidor)
        except Exception:
            pass

        # registramos el worker para que el frontend lo pueda encontrar
        ns.register(nombre_servidor, uri)

        print(f"Worker Pyro listo: {nombre_servidor}")
        print(f"URI: {uri}")

        # aqui se queda esperando llamadas del frontend
        daemon.requestLoop()

    except Exception as e:
        print(f"Error arrancando el worker: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()