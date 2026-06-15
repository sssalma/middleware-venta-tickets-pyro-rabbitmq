import sys
import os
import pika
import json
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import RABBIT_HOST, RABBIT_USER, RABBIT_PASSWORD, QUEUE_NAME

NUM_HILOS = 10

def parsear_linea(linea):
    partes = linea.split()
    if not partes or partes[0] != "BUY":
        return None
    if len(partes) == 3:
        return {
            "cliente_id": partes[1],
            "request_id": partes[2]
        }
    elif len(partes) == 4:
        return {
            "cliente_id": partes[1],
            "seat_id": int(partes[2]),
            "request_id": partes[3]
        }
    return None

def enviar_bloque(lineas):
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=RABBIT_HOST,
        credentials=pika.PlainCredentials(RABBIT_USER, RABBIT_PASSWORD),
        heartbeat=600,
        blocked_connection_timeout=300))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    for linea in lineas:
        payload = parsear_linea(linea)
        if payload is None:
            continue
        channel.basic_publish(
            exchange='',
            routing_key=QUEUE_NAME,
            body=json.dumps(payload),
            properties=pika.BasicProperties(delivery_mode=2)
        )
    connection.close()

def enviar_benchmark(nombre_fichero):
    try:
        with open(nombre_fichero, 'r') as f:
            lineas = [linea.strip() for linea in f if not linea.startswith('#') and linea.strip()]
    except FileNotFoundError:
        print(f"Error: No se encuentra el archivo {nombre_fichero}")
        return

    bloques = [lineas[i::NUM_HILOS] for i in range(NUM_HILOS)]
    with ThreadPoolExecutor(max_workers=NUM_HILOS) as executor:
        executor.map(enviar_bloque, bloques)

    print(" [+] Todas las peticiones han sido enviadas a la cola.")

if __name__ == "__main__":
   #llamamos con nombre del fichero por argumento: python producer.py benchmark_unnumbered_20000.txt o el 60k
    fichero = sys.argv[1] if len(sys.argv) > 1 else "benchmark_unnumbered_20000.txt"
    enviar_benchmark(fichero)