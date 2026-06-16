import sys
import os
import time
import threading
from typing import Any
import Pyro4

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PYRO_NS_HOST, PYRO_NS_PORT, PYRO_NAT_HOST

Pyro4.config.SERVERTYPE = "thread"
Pyro4.config.THREADPOOL_SIZE = 100  # type: ignore[assignment]
Pyro4.config.THREADPOOL_SIZE_MIN = 20  # type: ignore[assignment]


@Pyro4.expose
@Pyro4.behavior(instance_mode="single")
class TicketFrontend(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.worker_uris = []
        self.rr_index = 0
        self.last_refresh = 0
        self.refresh_interval = 2.0
        self._refresh_workers(force=True)

    def _refresh_workers(self, force=False):
        now = time.time()
        if not force and (now - self.last_refresh) < self.refresh_interval:
            return

        try:
            ns = Pyro4.locateNS(host=PYRO_NS_HOST, port=PYRO_NS_PORT)
            servicios = ns.list(prefix="tickets.worker.")
            nuevas_uris = list(servicios.values())
        except Exception:
            return

        with self.lock:
            self.worker_uris = nuevas_uris
            self.last_refresh = now
            if self.worker_uris:
                self.rr_index = self.rr_index % len(self.worker_uris)
            else:
                self.rr_index = 0

    def _get_next_worker_uri(self):
        self._refresh_workers()
        with self.lock:
            if not self.worker_uris:
                raise RuntimeError("No hay workers disponibles")
            uri = self.worker_uris[self.rr_index]
            self.rr_index = (self.rr_index + 1) % len(self.worker_uris)
            return uri

    def asignar_worker(self):
        return self._get_next_worker_uri()


def main():
    max_intentos = 10
    for intento in range(1, max_intentos + 1):
        try:
            daemon_kwargs: dict[str, Any] = {"host": "0.0.0.0"}
            if PYRO_NAT_HOST:
                daemon_kwargs["nathost"] = PYRO_NAT_HOST
            daemon = Pyro4.Daemon(**daemon_kwargs)

            ns = Pyro4.locateNS(host=PYRO_NS_HOST, port=PYRO_NS_PORT)

            frontend = TicketFrontend()
            uri = daemon.register(frontend)

            try:
                ns.remove("tickets.frontend")
            except Exception:
                pass

            ns.register("tickets.frontend", uri)

            print("Frontend Pyro listo: tickets.frontend")
            print(f"URI: {uri}")

            daemon.requestLoop()
            return

        except Exception as e:
            print(f"Intento {intento}/{max_intentos} - Error arrancando el frontend: {e}")
            time.sleep(2)

    print("No se pudo arrancar el frontend tras varios intentos. Saliendo.")
    sys.exit(1)


if __name__ == "__main__":
    main()