import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import subprocess
import redis
import pika
import json

from config import RABBIT_HOST, RABBIT_USER, RABBIT_PASSWORD, QUEUE_NAME, REDIS_HOST, REDIS_PORT


def get_rabbit_message_count():
    try:
        credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASSWORD)
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBIT_HOST,
                credentials=credentials
            )
        )
        channel = connection.channel()
        queue = channel.queue_declare(
            queue=QUEUE_NAME,
            durable=True,
            passive=True
        )
        count = queue.method.message_count
        connection.close()
        return count

    except Exception as e:
        print(f"Error consultando RabbitMQ: {e}")
        return -1


def contar_lineas_benchmark(benchmark_path):
    with open(benchmark_path, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.startswith("BUY"))


def run_experiment_indirect(benchmark_path, num_workers):
    print(f"\n{'=' * 50}")
    print(f"EXPERIMENTO INDIRECTO (RabbitMQ) - Workers: {num_workers}")
    print(f"Benchmark: {benchmark_path}")
    print(f"{'=' * 50}")

    total_benchmark_ops = contar_lineas_benchmark(benchmark_path)

    r = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=0,
        decode_responses=True
    )

    print("[1/3] Lanzando Producer y enviando peticiones...")

    start_time = time.time()

    env_vars = os.environ.copy()
    env_vars["PYTHONPATH"] = os.getcwd()

    subprocess.run(
        ["python3", "indirect-communication/producer.py", benchmark_path],
        env=env_vars
    )

    send_end_time = time.time()
    tiempo_envio = send_end_time - start_time

    print(f"[Producer] Tiempo Fire-and-Forget: {tiempo_envio:.2f} seg")

    print("[2/3] Procesando... (Esperando a que la cola se vacíe)")

    while True:
        count = get_rabbit_message_count()

        if count > 0:
            print(f"    > Mensajes pendientes: {count}    ", end="\r")

        elif count == 0:
            print("    > Cola vacía. Esperando margen de seguridad...")
            time.sleep(2.0)

            if get_rabbit_message_count() == 0:
                break

        else:
            print("    > Esperando reconexión con RabbitMQ...          ", end="\r")

        time.sleep(0.2)

    # Leer tiempos registrados por el worker (server-side)
    processing_started = r.get("worker:processing_started_at")
    processing_finished = r.get("worker:processing_finished_at")

    if isinstance(processing_started, str) and isinstance(processing_finished, str):
        tiempo_procesamiento_server = float(processing_finished) - float(processing_started)
        tiempo_total = tiempo_envio + tiempo_procesamiento_server
        tiempo_procesamiento = tiempo_procesamiento_server
    else:
        # Fallback a cálculo local si no hay datos del worker
        tiempo_total = time.time() - start_time
        tiempo_procesamiento = time.time() - send_end_time

    print("\n[3/3] Recopilando métricas de Redis...")

    all_requests_keys_raw = r.keys("request:*")
    all_requests_keys = all_requests_keys_raw if isinstance(all_requests_keys_raw, list) else []
    success = 0
    fail = 0

    for key in all_requests_keys:
        val = r.get(key)
        if isinstance(val, str):
            datos = json.loads(val)
            if datos.get("status") in ["SUCCESS", "OK"]:
                success += 1
            else:
                fail += 1

    benchmark_name = os.path.basename(benchmark_path)

    # SOLO para benchmark unnumbered
    if "unnumbered" in benchmark_name:
        no_num_success_raw = r.scard("procesadas")
        no_num_success = no_num_success_raw if isinstance(no_num_success_raw, int) else 0

        if no_num_success > 0:
            success = no_num_success
            intentos_raw = r.get("contador_tickets")
            intentos = int(intentos_raw) if isinstance(intentos_raw, str) else 0
            fail = max(0, intentos - success)

    total_ops = success + fail

    throughput_total = total_ops / tiempo_total if tiempo_total > 0 else 0
    throughput_envio = total_benchmark_ops / tiempo_envio if tiempo_envio > 0 else 0

    print("\n" + "*" * 40)
    print(f"TIEMPO ENVÍO FIRE-AND-FORGET:   {tiempo_envio:.2f} seg (cliente)")
    print(f"TIEMPO PROCESAMIENTO (server):  {tiempo_procesamiento:.2f} seg")
    print(f"TIEMPO TOTAL (server-side):     {tiempo_total:.2f} seg")
    print(f"THROUGHPUT ENVÍO:               {throughput_envio:.2f} ops/seg")
    print(f"THROUGHPUT TOTAL:               {throughput_total:.2f} ops/seg")
    print(f"SUCCESS:                      {success}")
    print(f"FAIL:                         {fail}")
    print(f"TOTAL PROCESADAS:             {total_ops}")
    print("*" * 40)

    # Guardar CSV siempre en la raíz del proyecto
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    csv_file = os.path.join(base_dir, "metricas_finales.csv")
    file_exists = os.path.isfile(csv_file)

    with open(csv_file, "a", encoding="utf-8") as f:
        if not file_exists:
            f.write(
                "modelo,benchmark,workers,tiempo_envio,tiempo_total,"
                "throughput_envio,throughput_total,success,fail\n"
            )

        f.write(
            f"indirecto,"
            f"{os.path.basename(benchmark_path)},"
            f"{num_workers},"
            f"{tiempo_envio:.2f},"
            f"{tiempo_total:.2f},"
            f"{throughput_envio:.2f},"
            f"{throughput_total:.2f},"
            f"{success},"
            f"{fail}\n"
        )

    print(f"Métricas guardadas en {csv_file}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python metricas.py <ruta_benchmark> <num_workers_activos>")
    else:
        run_experiment_indirect(sys.argv[1], sys.argv[2])