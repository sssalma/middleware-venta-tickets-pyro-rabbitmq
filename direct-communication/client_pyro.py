
import sys
import os
import Pyro4
import time


def run_benchmark(file_path):
    if not os.path.exists(file_path):
        print(f"Error: El archivo {file_path} no existe.")
        return

    try:
        ns = Pyro4.locateNS()
        # Buscamos todos los servicios que empiecen por "tickets.worker."
        servicios = ns.list(prefix="tickets.worker.")
        
        if not servicios:
            print("No se encontraron Workers registrados en el Name Server.")
            return

        print(f"Detectados {len(servicios)} workers: {list(servicios.keys())}")
        
        # Creamos una lista de proxies (uno por cada worker detectado)
        workers = [Pyro4.Proxy(uri) for uri in servicios.values()]
        
    except Exception as e:
        print(f"Error conectando con Pyro: {e}")
        return

    with open(file_path, 'r') as f:
        lines = f.readlines()

    print(f"Iniciando benchmark con {len(lines)} operaciones...")
    start_time = time.time()
    
    exitos = 0
    fallos = 0
    num_workers = len(workers)

    for i, line in enumerate(lines):
        parts = line.strip().split()
        if not parts: continue
        
        # Balanceo Round Robin (reparto equitativo entre workers)
        worker = workers[i % num_workers]
        
        try:
            # Formato esperado: BUY <client_id> <request_id> [seat_id]
            # Unnumbered: BUY C1 R1 -> len=3
            # Numbered: BUY C1 S1 R1 -> len=4
            if len(parts) == 3:
                res = worker.comprar(parts[1], parts[2])
            elif len(parts) == 4:
                res = worker.comprar(parts[1], parts[3], parts[2]) # (client, request, seat)
            
                if res: exitos += 1
                else: fallos += 1
        except Exception as e:
            print(f"Error en worker {i % num_workers}: {e}")
            fallos += 1

    end_time = time.time()
    duracion = end_time - start_time

    print(f"\n" + "="*30)
    print(f"RESULTADOS ARQUITECTURA DIRECTA (PYRO)")
    print(f"="*30)
    print(f"Tiempo total: {duracion:.2f} segundos")
    print(f"Throughput:   {len(lines)/duracion:.2f} op/seg")
    print(f"Éxitos:       {exitos}")
    print(f"Fallos:       {fallos}")
    print(f"="*30)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python client_pyro.py <ruta_al_benchmark>")
    else:
        run_benchmark(sys.argv[1])