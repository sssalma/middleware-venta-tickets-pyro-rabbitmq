import sys
import os
import time
import csv
import Pyro4
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import PYRO_NS_HOST, PYRO_NS_PORT, CLIENT_NUM_HILOS


def procesar_bloque(args):
    bloque_lineas, frontend_uri = args
    exitos = 0
    fallos = 0

    frontend = Pyro4.Proxy(frontend_uri)

    try:
        for line in bloque_lineas:
            parts = line.strip().split()
            if len(parts) not in (3, 4):
                fallos += 1
                continue

            try:
                worker_uri = frontend.asignar_worker()
                worker = Pyro4.Proxy(worker_uri)

                if len(parts) == 3:
                    res = worker.comprar(parts[1], parts[2])
                else:
                    res = worker.comprar(parts[1], parts[3], int(parts[2]))

                worker._pyroRelease()

                if res:
                    exitos += 1
                else:
                    fallos += 1

            except Exception as e:
                print("ERROR:", e)
                fallos += 1

    finally:
        frontend._pyroRelease()

    return exitos, fallos


def dividir_en_bloques(lines, num_bloques):
    # reparte las lineas entre los hilos de forma equilibrada
    bloques = [[] for _ in range(num_bloques)]

    for i, line in enumerate(lines):
        bloques[i % num_bloques].append(line)

    return bloques


def guardar_metricas_csv(
    benchmark_path,
    num_workers,
    duracion,
    throughput,
    exitos,
    fallos
):
    # guardamos las metricas en la raiz del proyecto
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    csv_file = os.path.join(base_dir, "metricas_finales.csv")

    file_exists = os.path.isfile(csv_file)

    with open(csv_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "modelo",
                "benchmark",
                "workers",
                "tiempo_envio",
                "tiempo_total",
                "throughput_envio",
                "throughput_total",
                "success",
                "fail"
            ])

        writer.writerow([
            "directo",
            os.path.basename(benchmark_path),
            num_workers,
            "",
            f"{duracion:.2f}",
            "",
            f"{throughput:.2f}",
            exitos,
            fallos
        ])


def run_benchmark(file_path):
    if not os.path.exists(file_path):
        print(f"Error: El archivo {file_path} no existe.")
        return

    try:
        # localizamos el name server de pyro
        ns = Pyro4.locateNS(host=PYRO_NS_HOST, port=PYRO_NS_PORT)

        # single entry point: el cliente solo busca el frontend
        frontend_uri = ns.lookup("tickets.frontend")

        # esto solo se usa para saber cuantos workers habia activos
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

    # cargamos solo las operaciones BUY del benchmark
    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line for line in f.readlines() if line.startswith("BUY")]

    hilos_efectivos = min(CLIENT_NUM_HILOS, len(lines))

    print(
        f"Iniciando benchmark DIRECTO con {len(lines)} operaciones "
        f"y {hilos_efectivos} hilos..."
    )

    # dividimos el benchmark entre los hilos
    bloques = dividir_en_bloques(lines, hilos_efectivos)
    tareas = [(bloque, frontend_uri) for bloque in bloques]

    start_time = time.time()

    exitos = 0
    fallos = 0

    # ejecutamos las peticiones de forma concurrente
    with ThreadPoolExecutor(max_workers=hilos_efectivos) as executor:
        resultados = list(executor.map(procesar_bloque, tareas))

    # juntamos los resultados de todos los hilos
    for ex, fa in resultados:
        exitos += ex
        fallos += fa

    end_time = time.time()

    duracion = end_time - start_time
    throughput = len(lines) / duracion if duracion > 0 else 0.0

    print("\n" + "=" * 40)
    print("RESULTADOS DIRECTA (PYRO - SINGLE ENTRY POINT)")
    print("=" * 40)
    print(f"Workers activos: {num_workers}")
    print(f"Hilos cliente:   {hilos_efectivos}")
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
        run_benchmark(sys.argv[1])