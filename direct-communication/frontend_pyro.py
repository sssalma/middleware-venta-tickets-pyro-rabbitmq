import time
import threading
import Pyro4

Pyro4.config.SERVERTYPE = "thread"
Pyro4.config.THREADPOOL_SIZE = 100
Pyro4.config.THREADPOOL_SIZE_MIN = 20


@Pyro4.expose
@Pyro4.behavior(instance_mode="single")
class TicketFrontend(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.worker_uris = []

        # guardamos proxies para no abrir una conexion nueva en cada peticion
        self.worker_proxies = {}

        # indice usado para repartir entre workers
        self.rr_index = 0

        # se refresca cada cierto tiempo para permitir escalado dinamico
        self.last_refresh = 0
        self.refresh_interval = 2.0

        # primer refresco obligado al arrancar
        self._refresh_workers(force=True)

    def _refresh_workers(self, force=False):
        # actualiza los workers registrados en el Name Server
        now = time.time()

        if not force and (now - self.last_refresh) < self.refresh_interval:
            return

        try:
            ns = Pyro4.locateNS(host="192.168.1.131", port=9090)
            servicios = ns.list(prefix="tickets.worker.")
            nuevas_uris = list(servicios.values())
        except Exception:
            # si falla el name server, mantenemos la lista anterior
            return

        with self.lock:
            antiguas = set(self.worker_uris)
            nuevas = set(nuevas_uris)

            # quitamos proxies de workers que ya no estan registrados
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

            # ajustamos el indice para que no se salga de rango
            if self.worker_uris:
                self.rr_index = self.rr_index % len(self.worker_uris)
            else:
                self.rr_index = 0

    def _get_next_worker_uri(self):
        # selecciona el siguiente worker, repartiendo las peticiones
        self._refresh_workers()

        with self.lock:
            if not self.worker_uris:
                raise RuntimeError("No hay workers disponibles")

            uri = self.worker_uris[self.rr_index]
            self.rr_index = (self.rr_index + 1) % len(self.worker_uris)

            return uri

    def _get_worker_proxy(self, uri):
        # reutilizamos proxies para evitar crear demasiadas conexiones
        with self.lock:
            proxy = self.worker_proxies.get(uri)

            if proxy is None:
                proxy = Pyro4.Proxy(uri)
                self.worker_proxies[uri] = proxy

            return proxy

    def _remove_worker_proxy(self, uri):
        # si un worker falla, quitamos su proxy para no seguir usandolo
        with self.lock:
            proxy = self.worker_proxies.pop(uri, None)

            if proxy is not None:
                try:
                    proxy._pyroRelease()
                except Exception:
                    pass

    def comprar(self, client_id, request_id, seat_id=None):
        # este metodo es el punto de entrada unico para el cliente
        self._refresh_workers()

        with self.lock:
            num_workers = len(self.worker_uris)

        if num_workers == 0:
            raise RuntimeError("No hay workers disponibles para procesar la compra")

        ultimo_error = None

        # probamos como maximo tantos workers como haya registrados
        for _ in range(num_workers):
            uri = None

            try:
                uri = self._get_next_worker_uri()
                worker_proxy = self._get_worker_proxy(uri)

                # si no hay seat_id es una compra no numerada
                if seat_id is None:
                    return worker_proxy.comprar(client_id, request_id)

                # si hay seat_id, se trata de una compra numerada
                else:
                    seat_id = int(seat_id)
                    return worker_proxy.comprar(client_id, request_id, seat_id)

            except Exception as e:
                # si un worker cae, se elimina y se intenta con otro
                ultimo_error = e

                if uri is not None:
                    self._remove_worker_proxy(uri)

                self._refresh_workers(force=True)

        raise RuntimeError(f"No se pudo procesar la compra. Último error: {ultimo_error}")


def main():
    # arranca el frontend y lo registra como tickets.frontend
    try:
        daemon = Pyro4.Daemon(
            host="0.0.0.0",
            nathost="192.168.1.131"
        )

        ns = Pyro4.locateNS(host="192.168.1.131", port=9090)

        frontend = TicketFrontend()
        uri = daemon.register(frontend)

        # borramos registro anterior si existia
        try:
            ns.remove("tickets.frontend")
        except Exception:
            pass

        ns.register("tickets.frontend", uri)

        print("Frontend Pyro listo: tickets.frontend")
        print(f"URI: {uri}")

        # aqui se queda esperando llamadas rpc
        daemon.requestLoop()

    except Exception as e:
        print(f"Error arrancando el frontend: {e}")


if __name__ == "__main__":
    main()