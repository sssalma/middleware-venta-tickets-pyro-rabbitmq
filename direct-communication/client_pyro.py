import sys
import os
import time
import csv
import Pyro4
from concurrent.futures import ThreadPoolExecutor

# Añadir la ruta raíz para importar desde 'base' si es necesario
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def procesar_linea(args):
    """Función que será ejecutada por cada hilo."""
    i, line, workers = args
    num_workers = len(workers)
    parts = line.strip().split()

    if not parts:
        return False

    # Round Robin entre workers
    worker = workers[i % num_workers]

    try:
        if len(parts) == 3:  # Unnumbered
            res = worker.comprar(parts[1], parts[2])
        elif len(parts) == 4:  # Numbered
            res = worker.comprar(parts[1], parts[3], parts[2])
        else:
            return False

        return True if res else False

    except Exception:
        return False


def guardar_metricas_csv(
    benchmark_path,
    num_workers,
    duracion,
    throughput,
    exitos,
    fallos,
    csv_file = os.path.join(os.path.dirname(__file__), "..", "metricas_finales.csv")
):
    """
    Guarda los resultados en metricas_finales.csv.
    Si el archivo no existe, escribe la cabecera.
    """
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


def run_benchmark_paralelo(file_path, max_hilos=50):
    if not os.path.exists(file_path):
        print(f"Error: El archivo {file_path} no existe.")
        return

    try:
        ns = Pyro4.locateNS(host="127.0.0.1")
        servicios = ns.list(prefix="tickets.worker.")
        if not servicios:
            print("No se encontraron Workers.")
            return

        print(f"Detectados {len(servicios)} workers.")

        # Creamos los proxies una sola vez
        workers = [Pyro4.Proxy(uri) for uri in servicios.values()]

    except Exception as e:
        print(f"Error Pyro: {e}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        lines = [l for l in f.readlines() if l.startswith("BUY")]

    print(f"Iniciando benchmark PARALELO con {len(lines)} operaciones y {max_hilos} hilos...")

    start_time = time.time()

    # Preparamos los argumentos para cada tarea
    tareas = [(i, line, workers) for i, line in enumerate(lines)]

    # Ejecución concurrente
    with ThreadPoolExecutor(max_workers=max_hilos) as executor:
        resultados = list(executor.map(procesar_linea, tareas))

    end_time = time.time()
    duracion = end_time - start_time

    exitos = sum(1 for r in resultados if r)
    fallos = len(lines) - exitos
    throughput = len(lines) / duracion if duracion > 0 else 0.0

    print("\n" + "=" * 30)
    print("RESULTADOS DIRECTA (PYRO PARALELO)")
    print("=" * 30)
    print(f"Workers activos: {len(workers)}")
    print(f"Tiempo total:    {duracion:.2f} seg")
    print(f"Throughput:      {throughput:.2f} op/seg")
    print(f"Éxitos:          {exitos}")
    print(f"Fallos:          {fallos}")
    print("=" * 30)

    guardar_metricas_csv(
        benchmark_path=file_path,
        num_workers=len(workers),
        duracion=duracion,
        throughput=throughput,
        exitos=exitos,
        fallos=fallos
    )

    print("Métricas guardadas en metricas_finales.csv")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python client_pyro.py <ruta_benchmark> [num_hilos]")
    else:
        hilos = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        run_benchmark_paralelo(sys.argv[1], hilos)