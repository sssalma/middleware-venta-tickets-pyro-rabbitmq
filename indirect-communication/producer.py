import pika
import json
import sys

def enviar_benchmark(nombre_fichero):
    # Conexión a RabbitMQ
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()
    except Exception as e:
        print(f"Error conectando a RabbitMQ: {e}")
        return

    channel.queue_declare(queue='cola_tickets', durable=True)
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
                    routing_key='cola_tickets',
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