import time
import threading
import Pyro4


@Pyro4.expose
@Pyro4.behavior(instance_mode="single")
class TicketFrontend(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.worker_uris = []
        self.worker_proxies = {}   # uri -> proxy persistente
        self.rr_index = 0
        self.last_refresh = 0
        self.refresh_interval = 2.0
        self._refresh_workers(force=True)

    def _refresh_workers(self, force=False):
        now = time.time()

        if not force and (now - self.last_refresh) < self.refresh_interval:
            return

        try:
            ns = Pyro4.locateNS(host="127.0.0.1")
            servicios = ns.list(prefix="tickets.worker.")
            nuevas_uris = list(servicios.values())
        except Exception:
            # Si el nameserver falla temporalmente, mantenemos la lista anterior
            return

        with self.lock:
            antiguas = set(self.worker_uris)
            nuevas = set(nuevas_uris)

            # Cerrar proxies de workers que ya no están
            eliminadas = antiguas - nuevas
            for uri in eliminadas:
                proxy = self.worker_proxies.pop(uri, None)
                if proxy is not None:
                    try:
                        proxy._pyroRelease()
                    except Exception:
                        pass

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

    def _get_worker_proxy(self, uri):
        with self.lock:
            proxy = self.worker_proxies.get(uri)
            if proxy is None:
                proxy = Pyro4.Proxy(uri)
                self.worker_proxies[uri] = proxy
            return proxy

    def _remove_worker_proxy(self, uri):
        with self.lock:
            proxy = self.worker_proxies.pop(uri, None)
            if proxy is not None:
                try:
                    proxy._pyroRelease()
                except Exception:
                    pass

    def comprar(self, client_id, request_id, seat_id=None):
        self._refresh_workers()

        with self.lock:
            num_workers = len(self.worker_uris)

        if num_workers == 0:
            raise RuntimeError("No hay workers disponibles para procesar la compra")

        ultimo_error = None

        for _ in range(num_workers):
            uri = None
            try:
                uri = self._get_next_worker_uri()
                worker_proxy = self._get_worker_proxy(uri)

                if seat_id is None:
                    return worker_proxy.comprar(client_id, request_id)
                else:
                    return worker_proxy.comprar(client_id, request_id, seat_id)

            except Exception as e:
                ultimo_error = e
                if uri is not None:
                    self._remove_worker_proxy(uri)
                self._refresh_workers(force=True)

        raise RuntimeError(f"No se pudo procesar la compra. Último error: {ultimo_error}")

    def ping(self):
        return "frontend pong"


def main():
    try:
        daemon = Pyro4.Daemon(host="0.0.0.0", nathost="127.0.0.1")
        ns = Pyro4.locateNS(host="127.0.0.1")

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

    except Exception as e:
        print(f"Error arrancando el frontend: {e}")


if __name__ == "__main__":
    main()