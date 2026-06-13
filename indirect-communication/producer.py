import sys
import os
import pika
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import RABBIT_HOST, RABBIT_USER, RABBIT_PASSWORD, QUEUE_NAME

def enviar_benchmark(nombre_fichero):
    """
    Lee el archivo de benchmark línea a línea y publica cada petición de compra 
    en la cola de RabbitMQ en mensajes JSON persistentes.
    """
    host_servidor = RABBIT_HOST
    credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASSWORD)

    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=host_servidor,
            credentials=credentials, 
            heartbeat=600, 
            blocked_connection_timeout=300))
        channel = connection.channel()
    except Exception as e:
        print(f"Error conectando a RabbitMQ: {e}")
        return
    #durable=True para que sobreviva a reinicios de RabbitMQ
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    try:
        with open(nombre_fichero, 'r') as f:
            for linea in f:
                if linea.startswith('#') or not linea.strip():
                    continue

                # Formato línea: BUY <client_id> <request_id> o BUY <client_id> <seat_id> <request_id>
                partes = linea.split()
                if not partes or partes[0] != "BUY":  #compruebo q sea una línea de compra
                    continue
                
                payload = {}
                if len(partes) == 3:  # No numerada
                    payload = {
                        "cliente_id": partes[1],
                        "request_id": partes[2]
                    }
                elif len(partes) == 4:  # Numerada
                    payload = {
                        "cliente_id": partes[1],
                        "seat_id": int(partes[2]),
                        "request_id": partes[3]
                    }

                # Publicar mensaje: enrutador por defecto (''), cola 'cola_tickets', mensaje en formato JSON, y marcarlo como persistente
                channel.basic_publish(
                    exchange='',
                    routing_key=QUEUE_NAME,
                    body=json.dumps(payload),
                    properties=pika.BasicProperties(
                        delivery_mode=2, 
                    )
                )
    except FileNotFoundError:
        print(f"Error: No se encuentra el archivo {nombre_fichero}")
    
    print(" [+] Todas las peticiones han sido enviadas a la cola.")
    connection.close()

if __name__ == "__main__":
   #llamamos con nombre del fichero por argumento: python producer.py benchmark_unnumbered_20000.txt o el 60k
    fichero = sys.argv[1] if len(sys.argv) > 1 else "benchmark_unnumbered_20000.txt"
    enviar_benchmark(fichero)