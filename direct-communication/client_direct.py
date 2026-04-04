import json
import time
import csv
from urllib import request, error


def enviar_post(url, datos):
    datos_json = json.dumps(datos).encode("utf-8")

    req = request.Request(
        url,
        data=datos_json,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with request.urlopen(req) as response:
            cuerpo = response.read().decode("utf-8")
            return json.loads(cuerpo)

    except error.HTTPError as e:
        cuerpo = e.read().decode("utf-8")
        try:
            return json.loads(cuerpo)
        except:
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
            writer.writerow([
                "benchmark",
                "workers",
                "limite",
                "total",
                "success",
                "fail",
                "tiempo_total_seg",
                "throughput_ops_seg"
            ])

        writer.writerow(fila)


def ejecutar_benchmark_numerado(ruta_fichero, base_url, limite=None, progreso_cada=100):
    url = f"{base_url}/buy_numbered"

    total = 0
    success = 0
    fail = 0

    inicio = time.time()

    with open(ruta_fichero, "r", encoding="utf-8") as f:
        for linea in f:
            if limite is not None and total >= limite:
                break

            linea = linea.strip()
            if not linea:
                continue

            partes = linea.split()

            # Formato: BUY cliente_id seat_id request_id
            if len(partes) != 4 or partes[0] != "BUY":
                continue

            _, cliente_id, seat_id, request_id = partes

            datos = {
                "cliente_id": cliente_id,
                "seat_id": int(seat_id),
                "request_id": request_id
            }

            resultado = enviar_post(url, datos)

            total += 1
            if resultado.get("status") in ["SUCCESS", "OK"]:
                success += 1
            else:
                fail += 1

            if progreso_cada and total % progreso_cada == 0:
                print(f"Procesadas {total} peticiones...")

    fin = time.time()
    tiempo_total = fin - inicio
    throughput = total / tiempo_total if tiempo_total > 0 else 0

    print("\n=== RESULTADOS BENCHMARK NUMERADO ===")
    print(f"Total peticiones: {total}")
    print(f"SUCCESS: {success}")
    print(f"FAIL: {fail}")
    print(f"Tiempo total: {tiempo_total:.4f} segundos")
    print(f"Throughput: {throughput:.2f} peticiones/segundo")

    return {
        "benchmark": "numerado",
        "total": total,
        "success": success,
        "fail": fail,
        "tiempo_total": tiempo_total,
        "throughput": throughput
    }


def ejecutar_benchmark_no_numerado(ruta_fichero, base_url, limite=None, progreso_cada=100):
    url = f"{base_url}/buy_unnumbered"

    total = 0
    success = 0
    fail = 0

    inicio = time.time()

    with open(ruta_fichero, "r", encoding="utf-8") as f:
        for linea in f:
            if limite is not None and total >= limite:
                break

            linea = linea.strip()
            if not linea:
                continue

            partes = linea.split()

            # Formato: BUY cliente_id request_id
            if len(partes) != 3 or partes[0] != "BUY":
                continue

            _, cliente_id, request_id = partes

            datos = {
                "cliente_id": cliente_id,
                "request_id": request_id
            }

            resultado = enviar_post(url, datos)

            total += 1
            if resultado.get("status") in ["SUCCESS", "OK"]:
                success += 1
            else:
                fail += 1

            if progreso_cada and total % progreso_cada == 0:
                print(f"Procesadas {total} peticiones...")

    fin = time.time()
    tiempo_total = fin - inicio
    throughput = total / tiempo_total if tiempo_total > 0 else 0

    print("\n=== RESULTADOS BENCHMARK NO NUMERADO ===")
    print(f"Total peticiones: {total}")
    print(f"SUCCESS: {success}")
    print(f"FAIL: {fail}")
    print(f"Tiempo total: {tiempo_total:.4f} segundos")
    print(f"Throughput: {throughput:.2f} peticiones/segundo")

    return {
        "benchmark": "no_numerado",
        "total": total,
        "success": success,
        "fail": fail,
        "tiempo_total": tiempo_total,
        "throughput": throughput
    }


if __name__ == "__main__":
    BASE_URL = "http://localhost:8080"

    RUTA_NUMERADO = "benchmarks/benchmark_numbered_60000.txt"
    RUTA_NO_NUMERADO = "benchmarks/benchmark_unnumbered_20000.txt"

    print("¿Qué benchmark quieres ejecutar?")
    print("1 - Numerado")
    print("2 - No numerado")
    opcion = input("Elige 1 o 2: ").strip()

    limite_input = input("Límite de peticiones (Enter para todas): ").strip()
    limite = int(limite_input) if limite_input else None

    workers_input = input("Número de workers activos: ").strip()
    workers = workers_input if workers_input else "desconocido"

    guardar_csv = input("¿Guardar resultado en CSV? (s/n): ").strip().lower()

    if opcion == "1":
        resultado = ejecutar_benchmark_numerado(RUTA_NUMERADO, BASE_URL, limite=limite)

    elif opcion == "2":
        resultado = ejecutar_benchmark_no_numerado(RUTA_NO_NUMERADO, BASE_URL, limite=limite)

    else:
        print("Opción no válida.")
        exit()

    if guardar_csv == "s":
        nombre_csv = "resultados_directos.csv"

        fila = [
            resultado["benchmark"],
            workers,
            limite if limite is not None else "completo",
            resultado["total"],
            resultado["success"],
            resultado["fail"],
            f"{resultado['tiempo_total']:.4f}",
            f"{resultado['throughput']:.2f}"
        ]

        try:
            with open(nombre_csv, "r", encoding="utf-8"):
                existe = True
        except FileNotFoundError:
            existe = False

        guardar_resultado_csv(
            nombre_csv,
            fila,
            escribir_cabecera=not existe
        )

        print(f"Resultado guardado en {nombre_csv}")