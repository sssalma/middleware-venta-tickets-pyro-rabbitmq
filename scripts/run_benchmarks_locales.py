"""
Ejecuta los benchmarks de hotspot y uniforme localmente (localhost).
Parchea las IPs hardcodeadas a localhost.
Modelos: directo (Pyro4) e indirecto (RabbitMQ)
Workers: 2, 4, 8, 16
"""
import sys
import os
import time
import threading
import json
import csv
import subprocess
from concurrent.futures import ThreadPoolExecutor

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

# Parche: redirigir Pyro4 a localhost
import Pyro4.naming
original_locateNS = Pyro4.locateNS
def patched_locateNS(host=None, **kwargs):
    if host and "192.168.1.131" in host:
        host = "localhost"
    return original_locateNS(host=host, **kwargs)
Pyro4.locateNS = patched_locateNS

from base.tickets import tickets
from base.redis_logica import RedisRepository
from base.reset_redis import reset_redis

# Configuracion
BENCHMARKS = [
    ("bm_hotspot.txt", os.path.join(ROOT_DIR, "benchmarks", "bm_hotspot.txt")),
    ("bm_uniforme.txt", os.path.join(ROOT_DIR, "benchmarks", "bm_uniforme.txt")),
]
WORKER_COUNTS = [1, 2, 3, 4]
CSV_FILE = os.path.join(ROOT_DIR, "metricas_finales.csv")

def reset_all():
    reset_redis()
    # Limpiar cola RabbitMQ
    try:
        import pika
        creds = pika.PlainCredentials("admin", "admin")
        conn = pika.BlockingConnection(pika.ConnectionParameters(host="localhost", credentials=creds))
        ch = conn.channel()
        ch.queue_delete(queue="cola_tickets")
        conn.close()
    except:
        pass

# ============================================================
# COMUNICACION DIRECTA (Pyro4)
# ============================================================
@Pyro4.expose
class BenchmarkWorker:
    def __init__(self, wid):
        self.wid = wid
        self.count = 0
        repo = RedisRepository()
        self.svc = tickets(repo)

    def comprar(self, client_id, request_id, seat_id=None):
        self.count += 1
        if seat_id is None:
            res = self.svc.comprar_no_numerada(client_id, request_id)
        else:
            res = self.svc.comprar_numerada(client_id, int(seat_id), request_id)
        return res.ok

def run_direct_benchmark(benchmark_name, benchmark_path, num_workers):
    print(f"\n--- DIRECTO: {benchmark_name}, workers={num_workers} ---")
    reset_all()

    # 1. Iniciar/reusar NS
    try:
        ns = Pyro4.locateNS(host="localhost")
        # Limpiar registros viejos
        for name in list(ns.list(prefix="tickets.worker.").keys()):
            try:
                ns.remove(name)
            except:
                pass
    except Exception:
        def start_ns():
            try:
                Pyro4.naming.startNSloop(host="localhost", port=9090)
            except:
                pass
        t = threading.Thread(target=start_ns, daemon=True)
        t.start()
        time.sleep(1)
        ns = Pyro4.locateNS(host="localhost")

    # 2. Iniciar workers
    worker_daemons = []
    def start_worker(wid):
        daemon = Pyro4.Daemon(host="localhost")
        ns_local = Pyro4.locateNS(host="localhost")
        worker = BenchmarkWorker(wid)
        uri = daemon.register(worker)
        ns_local.register(f"tickets.worker.{wid}", uri)
        worker_daemons.append(daemon)
        daemon.requestLoop()

    worker_threads = []
    for i in range(num_workers):
        t = threading.Thread(target=start_worker, args=(i+1,), daemon=True)
        t.start()
        worker_threads.append(t)

    time.sleep(1)

    # Verificar workers
    ns = Pyro4.locateNS(host="localhost")
    servicios = ns.list(prefix="tickets.worker.")
    if len(servicios) != num_workers:
        print(f"  Error: se registraron {len(servicios)} workers, esperaba {num_workers}")
        return

    # 3. Ejecutar benchmark (copiado de client_pyro.py)
    workers = [Pyro4.Proxy(uri) for uri in servicios.values()]

    with open(benchmark_path, "r", encoding="utf-8") as f:
        lines = [l for l in f.readlines() if l.startswith("BUY")]

    print(f"  {len(lines)} operaciones, {num_workers} workers...")

    def procesar_linea(args):
        i, line, workers = args
        num_w = len(workers)
        parts = line.strip().split()
        if not parts:
            return False
        worker = workers[i % num_w]
        try:
            if len(parts) == 3:
                res = worker.comprar(parts[1], parts[2])
            elif len(parts) == 4:
                res = worker.comprar(parts[1], parts[3], parts[2])
            else:
                return False
            return True if res else False
        except Exception:
            return False

    start_time = time.time()
    tareas = [(i, line, workers) for i, line in enumerate(lines)]
    with ThreadPoolExecutor(max_workers=50) as executor:
        resultados = list(executor.map(procesar_linea, tareas))
    duracion = time.time() - start_time

    exitos = sum(1 for r in resultados if r)
    fallos = len(lines) - exitos
    throughput = len(lines) / duracion if duracion > 0 else 0.0

    print(f"  Tiempo: {duracion:.2f}s, Throughput: {throughput:.2f} ops/s, OK: {exitos}, FAIL: {fallos}")

    # Guardar en CSV (formato 9 columnas)
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["modelo","benchmark","workers","tiempo_envio","tiempo_total","throughput_envio","throughput_total","success","fail"])
        writer.writerow(["directo", benchmark_name, num_workers,
                         "", f"{duracion:.2f}",
                         "", f"{throughput:.2f}",
                         exitos, fallos])

    reset_all()

# ============================================================
# COMUNICACION INDIRECTA (RabbitMQ)
# ============================================================
def run_indirect_benchmark(benchmark_name, benchmark_path, num_workers):
    print(f"\n--- INDIRECTO: {benchmark_name}, workers={num_workers} ---")
    reset_all()

    import pika
    from base.redis_logica import RedisRepository
    from base.tickets import tickets

    # 1. Iniciar workers RabbitMQ (en este test, los workers son hilos)
    #    pero en el sistema real se lanzan como procesos separados.
    #    Para medicion usamos el mismo enfoque que metricas.py
    #    pero con los workers reales.

    creds = pika.PlainCredentials("admin", "admin")
    conn_params = pika.ConnectionParameters(host="localhost", credentials=creds,
                                             heartbeat=600, blocked_connection_timeout=7200)

    # Lanzar workers como hilos
    results_queue = []

    def rabbit_worker(wid):
        repo = RedisRepository()
        svc = tickets(repo)
        conn = pika.BlockingConnection(conn_params)
        ch = conn.channel()
        ch.queue_declare(queue="cola_tickets", durable=True)
        ch.basic_qos(prefetch_count=1)

        def callback(ch, method, properties, body):
            data = json.loads(body)
            if "seat_id" in data:
                res = svc.comprar_numerada(data["cliente_id"], data["seat_id"], data["request_id"])
            else:
                res = svc.comprar_no_numerada(data["cliente_id"], data["request_id"])
            results_queue.append(res.ok)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        ch.basic_consume(queue="cola_tickets", on_message_callback=callback)
        ch.start_consuming()

    threads = []
    for i in range(num_workers):
        t = threading.Thread(target=rabbit_worker, args=(i+1,), daemon=True)
        t.start()
        threads.append(t)

    time.sleep(0.5)

    # 2. Producer: enviar mensajes
    conn = pika.BlockingConnection(conn_params)
    chan = conn.channel()
    chan.queue_declare(queue="cola_tickets", durable=True)

    with open(benchmark_path, "r", encoding="utf-8") as f:
        lines = [l for l in f.readlines() if l.startswith("BUY")]

    print(f"  {len(lines)} operaciones, {num_workers} workers...")

    start_time = time.time()

    for linea in lines:
        partes = linea.strip().split()
        if len(partes) == 3:
            payload = {"cliente_id": partes[1], "request_id": partes[2]}
        elif len(partes) == 4:
            payload = {"cliente_id": partes[1], "seat_id": int(partes[2]), "request_id": partes[3]}
        else:
            continue
        chan.basic_publish(exchange="", routing_key="cola_tickets",
                          body=json.dumps(payload),
                          properties=pika.BasicProperties(delivery_mode=2))

    conn.close()

    # 3. Esperar a que se procesen todos los mensajes
    total = len(lines)
    last_count = 0
    stall_count = 0
    while len(results_queue) < total:
        time.sleep(0.5)
        if len(results_queue) == last_count:
            stall_count += 1
        else:
            stall_count = 0
        last_count = len(results_queue)
        if stall_count > 20:  # 10s sin progreso
            print(f"  Timeout: {len(results_queue)}/{total} procesados")
            break

    duracion = time.time() - start_time
    exitos = sum(1 for r in results_queue if r)
    fallos = len(results_queue) - exitos
    throughput = total / duracion if duracion > 0 else 0.0

    print(f"  Tiempo: {duracion:.2f}s, Throughput: {throughput:.2f} ops/s, OK: {exitos}, FAIL: {fallos}")

    # Guardar en CSV (formato 9 columnas)
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["modelo","benchmark","workers","tiempo_envio","tiempo_total","throughput_envio","throughput_total","success","fail"])
        writer.writerow(["indirecto", benchmark_name, num_workers,
                         f"{duracion:.2f}", f"{duracion:.2f}",
                         f"{throughput:.2f}", f"{throughput:.2f}",
                         exitos, fallos])

    reset_all()

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("RUNNER DE BENCHMARKS LOCALES")
    print("=" * 60)
    print(f"Benchmarks: {[b[0] for b in BENCHMARKS]}")
    print(f"Workers: {WORKER_COUNTS}")

    for bname, bpath in BENCHMARKS:
        for nw in WORKER_COUNTS:
            run_direct_benchmark(bname, bpath, nw)
    for bname, bpath in BENCHMARKS:
        for nw in WORKER_COUNTS:
            run_indirect_benchmark(bname, bpath, nw)

    print("\n" + "=" * 60)
    print("COMPLETADO - Resultados en metricas_finales.csv")
    print("=" * 60)
