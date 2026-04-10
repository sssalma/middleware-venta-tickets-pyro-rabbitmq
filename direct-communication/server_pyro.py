

import sys
import os
import Pyro4


# Añadir la ruta raíz al path para poder importar desde la carpeta 'base'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from base.tickets import tickets
from base.redis_logica import RedisRepository

@Pyro4.expose
class TicketWorker(object):
    def __init__(self):
        # Cada worker instancia la lógica, que a su vez conecta con el Redis central
        repo = RedisRepository()
        self.servicio = tickets(repo)
        print(f"Worker inicializado y conectado a Redis.")

    def comprar(self, client_id, request_id, seat_id=None):
        """
        Método expuesto remotamente. 
        Maneja tanto tickets numerados como no numerados.
        """
        if seat_id is None:
            return self.servicio.comprar_no_numerada(client_id, request_id)
        else:
            return self.servicio.comprar_numerada(client_id, seat_id, request_id)

    def ping(self):
        return "pong"

def main():
    if len(sys.argv) < 2:
        print("Uso: python server_pyro.py <ID_DEL_WORKER>")
        sys.exit(1)

    worker_id = sys.argv[1]
    
    # Configuramos el Daemon para que escuche en todas las interfaces (0.0.0.0)
    # Esto es clave para que máquinas externas puedan conectar
    daemon = Pyro4.Daemon()  
    
    try:
        # Localiza el Name Server (debe estar corriendo antes)
        ns = Pyro4.locateNS()
    except Exception as e:
        print(f"Error: No se encontró el Name Server. {e}")
        sys.exit(1)

    # Registramos el objeto en el Daemon y luego en el Name Server
    uri = daemon.register(TicketWorker)
    nombre_servidor = f"tickets.worker.{worker_id}"
    ns.register(nombre_servidor, uri)
    
    print(f"✅ Servidor Pyro listo: {nombre_servidor}")
    print(f"URI: {uri}")
    daemon.requestLoop()

if __name__ == "__main__":
    main()