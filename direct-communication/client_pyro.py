import sys
import os
import time
import csv
import Pyro4
from concurrent.futures import ThreadPoolExecutor

SERVER_IP = "192.168.1.131"
SERVER_PORT = 9090
NUM_HILOS = 20

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def procesar_linea(args):
    line, frontend_uri = args
    parts = line.strip().split()

    if not parts:
        return False

    try:
        # Cada tarea crea su proxy al FRONTEND, no al worker
        with Pyro4.Proxy(frontend_uri) as frontend:
            if len(parts) == 3:  # Unnumbered: BUY client_id request_id
                res = frontend.comprar(parts[1], parts[2])

            elif len(parts) == 4:  # Numbered: BUY client_id seat_id request_id
                seat_id = int(parts[2])
                res = frontend.comprar(parts[1], parts[3], int(seat_id))

            else:
                return False

        return True if res else False

    except Exception as e:
        print("ERROR:", e)
        return False


def guardar_metricas_csv(
    benchmark_path,
    num_workers,
    duracion,
    throughput,
    exitos,
    fallos,
    csv_file=os.path.join(os.path.dirname(__file__), "..", "metricas_finales.csv")
):
    file_exists = os.path.isfile(csv_file)

    with open(csv_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "modelo",
                "benchmark",
                "workers",
                "tiempo",
                "throughput",
                "success",
                "fail"
            ])

        writer.writerow([
            "directo",
            os.path.basename(benchmark_path),
            num_workers,
            f"{duracion:.2f}",
            f"{throughput:.2f}",
            exitos,
            fallos
        ])


def run_benchmark_paralelo(file_path):
    if not os.path.exists(file_path):
        print(f"Error: El archivo {file_path} no existe.")
        return

    try:
        ns = Pyro4.locateNS(host=SERVER_IP, port=SERVER_PORT)

        # SINGLE ENTRY POINT: el cliente solo obtiene el frontend
        frontend_uri = ns.lookup("tickets.frontend")

        # Solo para métricas, no para llamar directamente
        servicios = ns.list(prefix="tickets.worker.")
        num_workers = len(servicios)

        if num_workers == 0:
            print("No se encontraron workers registrados.")
            return

        print("Conectado al frontend único: tickets.frontend")
        print(f"Workers detectados por Name Server: {num_workers}")

    except Exception as e:
        print(f"Error Pyro: {e}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        lines = [l for l in f.readlines() if l.startswith("BUY")]

    print(f"Iniciando benchmark DIRECTO con {len(lines)} operaciones y {NUM_HILOS} hilos...")

    start_time = time.time()

    tareas = [(line, frontend_uri) for line in lines]

    with ThreadPoolExecutor(max_workers=NUM_HILOS) as executor:
        resultados = list(executor.map(procesar_linea, tareas))

    end_time = time.time()
    duracion = end_time - start_time

    exitos = sum(1 for r in resultados if r)
    fallos = len(lines) - exitos
    throughput = len(lines) / duracion if duracion > 0 else 0.0

    print("\n" + "=" * 40)
    print("RESULTADOS DIRECTA (PYRO - SINGLE ENTRY POINT)")
    print("=" * 40)
    print(f"Workers activos: {num_workers}")
    print(f"Tiempo total:    {duracion:.2f} seg")
    print(f"Throughput:      {throughput:.2f} op/seg")
    print(f"Éxitos:          {exitos}")
    print(f"Fallos:          {fallos}")
    print("=" * 40)

    guardar_metricas_csv(
        benchmark_path=file_path,
        num_workers=num_workers,
        duracion=duracion,
        throughput=throughput,
        exitos=exitos,
        fallos=fallos
    )

    print("Métricas guardadas en metricas_finales.csv")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python client_pyro.py <ruta_benchmark>")
    else:
        run_benchmark_paralelo(sys.argv[1])