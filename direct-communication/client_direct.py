import csv
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib import request, error

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALLOWED_CONCURRENCY = {10, 20, 50}
CSV_HEADERS = [
    "benchmark",
    "workers",
    "limite",
    "concurrencia",
    "total",
    "success",
    "fail",
    "tiempo_total_seg",
    "throughput_ops_seg"
]


def enviar_post(url, datos):
    datos_json = json.dumps(datos).encode("utf-8")

    req = request.Request(
        url,
        data=datos_json,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with request.urlopen(req, timeout=10) as response:
            cuerpo = response.read().decode("utf-8")
            return json.loads(cuerpo)

    except error.HTTPError as e:
        cuerpo = e.read().decode("utf-8")
        try:
            return json.loads(cuerpo)
        except Exception:
            return {
                "ok": False,
                "status": "FAIL",
                "motivo": f"http_error_{e.code}"
            }

    except Exception as e:
        return {
            "ok": False,
            "status": "FAIL",
            "motivo": f"error_conexion: {str(e)}"
        }


def guardar_resultado_csv(nombre_fichero, fila, escribir_cabecera=False):
    with open(nombre_fichero, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if escribir_cabecera:
            writer.writerow(CSV_HEADERS)

        writer.writerow(fila)


def quiere_guardar_csv(respuesta):
    respuesta_normalizada = respuesta.strip().lower().replace("í", "i")
    return respuesta_normalizada in {"s", "si", "y", "yes"}


def leer_concurrencia():
    while True:
        concurrencia_input = input("Nivel de concurrencia (10, 20 o 50; Enter = 20): ").strip()

        if not concurrencia_input:
            return 20

        try:
            concurrencia = int(concurrencia_input)
        except ValueError:
            print("Valor no valido. Solo se permite 10, 20 o 50.")
            continue

        if concurrencia in ALLOWED_CONCURRENCY:
            return concurrencia

        print("Valor no valido. Solo se permite 10, 20 o 50.")


def cargar_peticiones_numerado(ruta_fichero, limite=None):
    peticiones = []

    with open(ruta_fichero, "r", encoding="utf-8") as f:
        for linea in f:
            if limite is not None and len(peticiones) >= limite:
                break

            linea = linea.strip()
            if not linea:
                continue

            partes = linea.split()

            # Formato: BUY cliente_id seat_id request_id
            if len(partes) != 4 or partes[0] != "BUY":
                continue

            _, cliente_id, seat_id, request_id = partes

            peticiones.append({
                "cliente_id": cliente_id,
                "seat_id": int(seat_id),
                "request_id": request_id
            })

    return peticiones


def cargar_peticiones_no_numerado(ruta_fichero, limite=None):
    peticiones = []

    with open(ruta_fichero, "r", encoding="utf-8") as f:
        for linea in f:
            if limite is not None and len(peticiones) >= limite:
                break

            linea = linea.strip()
            if not linea:
                continue

            partes = linea.split()

            # Formato: BUY cliente_id request_id
            if len(partes) != 3 or partes[0] != "BUY":
                continue

            _, cliente_id, request_id = partes

            peticiones.append({
                "cliente_id": cliente_id,
                "request_id": request_id
            })

    return peticiones


def ejecutar_benchmark_paralelo(url, peticiones, benchmark, concurrencia=20, progreso_cada=100):
    total = len(peticiones)
    success = 0
    fail = 0

    inicio = time.time()

    with ThreadPoolExecutor(max_workers=concurrencia) as executor:
        futuros = [executor.submit(enviar_post, url, datos) for datos in peticiones]

        for i, futuro in enumerate(as_completed(futuros), start=1):
            resultado = futuro.result()

            if resultado.get("status") in ["SUCCESS", "OK"]:
                success += 1
            else:
                fail += 1

            if progreso_cada and i % progreso_cada == 0:
                print(f"Completadas {i}/{total} peticiones...")

    fin = time.time()
    tiempo_total = fin - inicio
    throughput = total / tiempo_total if tiempo_total > 0 else 0

    print(f"\n=== RESULTADOS BENCHMARK {benchmark.upper()} ===")
    print(f"Total peticiones: {total}")
    print(f"SUCCESS: {success}")
    print(f"FAIL: {fail}")
    print(f"Tiempo total: {tiempo_total:.4f} segundos")
    print(f"Throughput: {throughput:.2f} peticiones/segundo")

    return {
        "benchmark": benchmark,
        "total": total,
        "success": success,
        "fail": fail,
        "tiempo_total": tiempo_total,
        "throughput": throughput
    }


if __name__ == "__main__":
    BASE_URL = "http://localhost:8080"

    RUTA_NUMERADO = PROJECT_ROOT / "benchmarks" / "benchmark_numbered_60000.txt"
    RUTA_NO_NUMERADO = PROJECT_ROOT / "benchmarks" / "benchmark_unnumbered_20000.txt"

    print("¿Qué benchmark quieres ejecutar?")
    print("1 - Numerado")
    print("2 - No numerado")
    opcion = input("Elige 1 o 2: ").strip()

    limite_input = input("Límite de peticiones (Enter para todas): ").strip()
    limite = int(limite_input) if limite_input else None

    workers_input = input("Número de workers activos: ").strip()
    workers = workers_input if workers_input else "desconocido"

    concurrencia = leer_concurrencia()

    guardar_csv = input("¿Guardar resultado en CSV? (s/n): ").strip().lower()

    if opcion == "1":
        url = f"{BASE_URL}/buy_numbered"
        peticiones = cargar_peticiones_numerado(RUTA_NUMERADO, limite=limite)
        resultado = ejecutar_benchmark_paralelo(
            url=url,
            peticiones=peticiones,
            benchmark="numerado",
            concurrencia=concurrencia
        )

    elif opcion == "2":
        url = f"{BASE_URL}/buy_unnumbered"
        peticiones = cargar_peticiones_no_numerado(RUTA_NO_NUMERADO, limite=limite)
        resultado = ejecutar_benchmark_paralelo(
            url=url,
            peticiones=peticiones,
            benchmark="no_numerado",
            concurrencia=concurrencia
        )

    else:
        print("Opción no válida.")
        raise SystemExit(1)

    if quiere_guardar_csv(guardar_csv):
        nombre_csv = PROJECT_ROOT / "resultados_directos.csv"

        fila = [
            resultado["benchmark"],
            workers,
            limite if limite is not None else "completo",
            concurrencia,
            resultado["total"],
            resultado["success"],
            resultado["fail"],
            f"{resultado['tiempo_total']:.4f}",
            f"{resultado['throughput']:.2f}"
        ]

        existe = nombre_csv.exists() and nombre_csv.stat().st_size > 0

        guardar_resultado_csv(
            nombre_csv,
            fila,
            escribir_cabecera=not existe
        )

        print(f"Resultado guardado en {nombre_csv}")
    else:
        print("Resultado no guardado en CSV.")
