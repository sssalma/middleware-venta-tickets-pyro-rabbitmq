"""
Test de integracion: verifica comunicacion directa (Pyro4) e indirecta (RabbitMQ).
"""
import sys
import os
import time
import threading
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PYRO_NS_HOST, PYRO_NS_PORT, REDIS_HOST, REDIS_PORT, RABBIT_HOST, RABBIT_USER, RABBIT_PASSWORD, QUEUE_NAME

import Pyro4.naming
import Pyro4.core

from base.tickets import tickets
from base.redis_logica import RedisRepository
from base.reset_redis import reset_redis

# 1. TEST BASE
print("=" * 60)
print("TEST 1: LOGICA BASE (atomicidad Redis)")
print("=" * 60)
reset_redis()
repo = RedisRepository()
svc = tickets(repo)

# Test: Compra numerada - mismo asiento dos veces
#   Verifica que SET NX impide la sobreventa: 1ra compra OK, 2da rechazada
r1 = svc.comprar_numerada("cliente1", 42, "req-001")
r2 = svc.comprar_numerada("cliente2", 42, "req-002")
assert r1.ok == True, f"Esperaba ok=True, got {r1}"
assert r2.ok == False, f"Esperaba ok=False (seat_already_sold), got {r2}"
assert r2.motivo == "seat_already_sold"
print("  [OK] Numerada: 1ra compra seat 42 = OK, 2da = seat_already_sold")

# Test: Idempotencia en numeradas - misma request_id repetida
#   Verifica que el cache de request_id devuelve el mismo resultado
r3 = svc.comprar_numerada("cliente3", 99, "req-003")
r4 = svc.comprar_numerada("cliente4", 99, "req-003")  # mismo request_id
assert r3.ok == True
assert r4.ok == True  # Devuelve el mismo resultado cacheado
assert r4.motivo == "seat_reserved"
print("  [OK] Idempotencia numerada: misma request_id devuelve mismo resultado")

# Test: Idempotencia en no numeradas - misma request_id repetida
#   Verifica que el cache de request_id evita compras duplicadas
r5 = svc.comprar_no_numerada("cliente5", "req-005")
r6 = svc.comprar_no_numerada("cliente6", "req-005")  # mismo request_id
assert r5.ok == True
assert r6.ok == True
assert r6.motivo == "ya_comprado_anteriormente"
print("  [OK] Idempotencia no numerada: misma request_id devuelve mismo resultado")

# Test: Asiento fuera de rango (límite inferior: 0)
#   Verifica que seat_id < 1 es rechazado
r7 = svc.comprar_numerada("cliente7", 0, "req-007")
assert r7.ok == False
assert r7.motivo == "invalid_seat_id"
print("  [OK] Asiento fuera de rango (0): invalid_seat_id")

# Test: Asiento fuera de rango (límite superior: 20001)
#   Verifica que seat_id > 20000 es rechazado
r8 = svc.comprar_numerada("cliente8", 20001, "req-008")
assert r8.ok == False
print("  [OK] Asiento fuera de rango (20001): invalid_seat_id")

# Test: Cliente_id vacio
#   Verifica que una peticion sin cliente_id es rechazada
r9 = svc.comprar_numerada("", 50, "req-009")
assert r9.ok == False
assert r9.motivo == "faltan_datos"
print("  [OK] Cliente_id vacio: faltan_datos")

# Test: Sold out en no numeradas
#   Verifica que al alcanzar el aforo de 20000, las siguientes compras son rechazadas
repo.redis.set("contador_tickets", 20000)
r10 = svc.comprar_no_numerada("cliente10", "req-010")
assert r10.ok == False
assert r10.motivo == "sold_out"
print("  [OK] No numerada sold_out: aforo completo, compra rechazada")

# Test: Concurrencia en asiento numerado
#   5 hilos compiten simultaneamente por el mismo asiento (seat 999)
#   Verifica que solo 1 gana (SET NX atomico) y los otros 4 pierden
resultados_concurrentes = []
lock_concurrente = threading.Lock()
def comprar_asiento(id_hilo):
    res = svc.comprar_numerada(f"thread{id_hilo}", 999, f"req-conc-{id_hilo}")
    with lock_concurrente:
        resultados_concurrentes.append(res.ok)

hilos = []
for i in range(5):
    t = threading.Thread(target=comprar_asiento, args=(i,))
    hilos.append(t)

for t in hilos:
    t.start()
for t in hilos:
    t.join()

exitos = sum(1 for ok in resultados_concurrentes if ok)
fallos = sum(1 for ok in resultados_concurrentes if not ok)
assert exitos == 1, f"Solo 1 deberia ganar, ganaron {exitos}"
assert fallos == 4, f"4 deberian perder, fallaron {fallos}"
print(f"  [OK] Concurrencia numerada: 5 hilos -> 1 ganador, 4 perdedores")

print("  [PASS] Test base: TODOS OK")
reset_redis()


# 2. TEST COMUNICACION DIRECTA (Pyro4)
print()
print("=" * 60)
print("TEST 2: COMUNICACION DIRECTA (Pyro4 RPC)")
print("=" * 60)

# Iniciar Name Server de Pyro4 en un hilo aparte
def run_ns():
    try:
        Pyro4.naming.startNSloop(host=PYRO_NS_HOST, port=PYRO_NS_PORT)
    except Exception:
        pass

ns_thread = threading.Thread(target=run_ns, daemon=True)
ns_thread.start()
time.sleep(1)

# Verificar que el NS esta vivo
try:
    ns = Pyro4.locateNS(host=PYRO_NS_HOST, port=PYRO_NS_PORT)
    print(f"  [OK] Name Server iniciado en {PYRO_NS_HOST}:{PYRO_NS_PORT}")
except Exception as e:
    print("  [FAIL] No se pudo iniciar NS:", e)
    sys.exit(1)

# Arrancar 2 workers Pyro4 que se registran en el Name Server
@Pyro4.expose
class TestWorker:
    def __init__(self, wid):
        self.wid = wid
        self.count = 0
        repo = RedisRepository()
        self.svc = tickets(repo)

    def comprar(self, client_id, request_id, seat_id=None):
        self.count += 1
        time.sleep(0.01)
        if seat_id is None:
            res = self.svc.comprar_no_numerada(client_id, request_id)
        else:
            res = self.svc.comprar_numerada(client_id, seat_id, request_id)
        return res.ok

workers_daemons = []

def start_worker(wid):
    daemon = Pyro4.Daemon(host=PYRO_NS_HOST)
    ns = Pyro4.locateNS(host=PYRO_NS_HOST, port=PYRO_NS_PORT)
    worker = TestWorker(wid)
    uri = daemon.register(worker)
    ns.register("tickets.worker." + str(wid), uri)
    workers_daemons.append(daemon)
    daemon.requestLoop()

for i in range(2):
    t = threading.Thread(target=start_worker, args=(i+1,), daemon=True)
    t.start()

time.sleep(1)

# Verificar workers registrados
ns = Pyro4.locateNS(host=PYRO_NS_HOST, port=PYRO_NS_PORT)
servicios = ns.list(prefix="tickets.worker.")
assert len(servicios) == 2, "Esperaba 2 workers, encontre " + str(len(servicios))
print("  [OK] 2 Workers Pyro4 registrados en NS")

# Cliente: probar unas cuantas requests
workers = [Pyro4.Proxy(uri) for uri in servicios.values()]

# Test: Compra numerada via RPC - verifica que el worker procesa correctamente
res = workers[0].comprar("c1", "r100", 100)
assert res == True, "Expected True, got " + str(res)
print("  [OK] Pyro4 numbered: compra exitosa")

res = workers[1].comprar("c2", "r101", 100)
assert res == False, "Expected False (seat_already_sold), got " + str(res)
print("  [OK] Pyro4 numbered: seat_already_sold funciona via RPC")

# Test: Compra no numerada via RPC
res = workers[0].comprar("c3", "r102")
assert res == True
print("  [OK] Pyro4 unnumbered: compra exitosa")

# Test: Round-robin - workers diferentes comparten el mismo Redis
#   Worker 0 vende seat 200, Worker 1 intenta vender el mismo y debe fallar
res1 = workers[0].comprar("c4", "r103", 200)
res2 = workers[1].comprar("c5", "r104", 200)  # ya vendido
assert res1 == True
assert res2 == False
print("  [OK] Pyro4 round-robin: workers comparten Redis correctamente")

print("  [PASS] Test comunicacion directa: TODOS OK")
reset_redis()


# 3. TEST COMUNICACION INDIRECTA (RabbitMQ)
print()
print("=" * 60)
print("TEST 3: COMUNICACION INDIRECTA (RabbitMQ)")
print("=" * 60)

import pika

# Test: Publicar mensajes en la cola de RabbitMQ
#   Verifica que el producer puede conectar y publicar mensajes persistentes
try:
    creds = pika.PlainCredentials(RABBIT_USER, RABBIT_PASSWORD)
    conn = pika.BlockingConnection(pika.ConnectionParameters(host=RABBIT_HOST, credentials=creds))
    chan = conn.channel()
    chan.queue_declare(queue=QUEUE_NAME, durable=True)

    # Probar envio y consumo de un mensaje
    payload_num = json.dumps({"cliente_id": "c1", "seat_id": 500, "request_id": "req500"})
    chan.basic_publish(exchange="", routing_key=QUEUE_NAME, body=payload_num,
                       properties=pika.BasicProperties(delivery_mode=2))

    payload_nnum = json.dumps({"cliente_id": "c2", "request_id": "req501"})
    chan.basic_publish(exchange="", routing_key=QUEUE_NAME, body=payload_nnum,
                       properties=pika.BasicProperties(delivery_mode=2))

    print(f"  [OK] Mensajes publicados en {QUEUE_NAME}")
    conn.close()
except Exception as e:
    print("  [FAIL] Error con RabbitMQ:", e)
    sys.exit(1)

# Consumidor: worker RabbitMQ que procesa los mensajes con ACK manual
repo2 = RedisRepository()
svc2 = tickets(repo2)

resultados_recibidos = []

def procesar_test(ch, method, properties, body):
    data = json.loads(body)
    if "seat_id" in data:
        res = svc2.comprar_numerada(data["cliente_id"], data["seat_id"], data["request_id"])
    else:
        res = svc2.comprar_no_numerada(data["cliente_id"], data["request_id"])
    resultados_recibidos.append((data["request_id"], res.ok, res.motivo))
    ch.basic_ack(delivery_tag=method.delivery_tag)

creds = pika.PlainCredentials(RABBIT_USER, RABBIT_PASSWORD)
conn2 = pika.BlockingConnection(pika.ConnectionParameters(host=RABBIT_HOST, credentials=creds))
chan2 = conn2.channel()
chan2.queue_declare(queue=QUEUE_NAME, durable=True)
chan2.basic_qos(prefetch_count=1)
chan2.basic_consume(queue=QUEUE_NAME, on_message_callback=procesar_test)

# Consumir los 2 mensajes con timeout
timeout = 5
start = time.time()
while len(resultados_recibidos) < 2 and (time.time() - start) < timeout:
    conn2.process_data_events(time_limit=1)

assert len(resultados_recibidos) == 2, "Esperaba 2 resultados, recibi " + str(len(resultados_recibidos))
req_ids = [r[0] for r in resultados_recibidos]
assert "req500" in req_ids
assert "req501" in req_ids

for req_id, ok, motivo in resultados_recibidos:
    if req_id == "req500":
        assert ok == True, "req500 deberia ser ok=True, got " + str(ok)
        print("  [OK] RabbitMQ numbered: " + str(req_id) + " -> " + str(motivo))
    elif req_id == "req501":
        assert ok == True, "req501 deberia ser ok=True, got " + str(ok)
        print("  [OK] RabbitMQ unnumbered: " + str(req_id) + " -> " + str(motivo))

conn2.close()

# Test: Idempotencia en RabbitMQ - reintento de mensaje
#   Simula un reintento de red: mismo mensaje publicado de nuevo
#   El worker debe devolver el mismo resultado (cacheado en Redis) sin duplicar la venta
creds3 = pika.PlainCredentials(RABBIT_USER, RABBIT_PASSWORD)
conn3 = pika.BlockingConnection(pika.ConnectionParameters(host=RABBIT_HOST, credentials=creds3))
chan3 = conn3.channel()
chan3.basic_publish(exchange="", routing_key=QUEUE_NAME, body=payload_num,
                   properties=pika.BasicProperties(delivery_mode=2))
chan3.close()

# Consumir el reintento
resultados_recibidos2 = []
def procesar_reintento(ch, method, properties, body):
    data = json.loads(body)
    if "seat_id" in data:
        res = svc2.comprar_numerada(data["cliente_id"], data["seat_id"], data["request_id"])
    else:
        res = svc2.comprar_no_numerada(data["cliente_id"], data["request_id"])
    resultados_recibidos2.append((data["request_id"], res.ok, res.motivo))
    ch.basic_ack(delivery_tag=method.delivery_tag)

conn4 = pika.BlockingConnection(pika.ConnectionParameters(host=RABBIT_HOST, credentials=creds))
chan4 = conn4.channel()
chan4.queue_declare(queue=QUEUE_NAME, durable=True)
chan4.basic_consume(queue=QUEUE_NAME, on_message_callback=procesar_reintento, auto_ack=False)
start = time.time()
while len(resultados_recibidos2) < 1 and (time.time() - start) < 5:
    conn4.process_data_events(time_limit=1)

assert len(resultados_recibidos2) == 1
req_id, ok, motivo = resultados_recibidos2[0]
assert ok == True, "Reintento deberia devolver True (idempotencia), got " + str(ok)
assert motivo == "seat_reserved", "Reintento deberia dar seat_reserved (cache), got " + str(motivo)
print("  [OK] RabbitMQ idempotencia: reintento devuelve mismo resultado (" + str(motivo) + ")")
conn4.close()

print("  [PASS] Test comunicacion indirecta: TODOS OK")

# Limpiar
reset_redis()

# Limpiar cola RabbitMQ
creds_clean = pika.PlainCredentials(RABBIT_USER, RABBIT_PASSWORD)
conn_clean = pika.BlockingConnection(pika.ConnectionParameters(host=RABBIT_HOST, credentials=creds_clean))
chan_clean = conn_clean.channel()
chan_clean.queue_delete(queue=QUEUE_NAME)
conn_clean.close()

print()
print("=" * 60)
print("RESUMEN FINAL: TODOS LOS TESTS PASARON")
print("=" * 60)
print("  [OK] Logica base (atomicidad, idempotencia, validaciones, sold_out, concurrencia)")
print("  [OK] Comunicacion directa (Pyro4 RPC, round-robin)")
print("  [OK] Comunicacion indirecta (RabbitMQ pub/sub, ACKs, idempotencia)")
