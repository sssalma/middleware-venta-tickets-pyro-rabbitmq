import pika
import json
import time
import sys
import os

# Esto añade la carpeta raíz del proyecto al camino de búsqueda de Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.redis_logica import RedisRepository
from base.tickets import tickets

# lógica de negocio
repo = RedisRepository()
service = tickets(repo)

def procesar_compra(ch, method, properties, body):
    # convierto el mensjase json a dict y miro si hay un argumento seatid (dif numerado o no)
    data = json.loads(body)
    if "seat_id" in data:
        resultado = service.comprar_numerada(
            data["cliente_id"], 
            data["seat_id"], 
            data["request_id"]
        )
    else:
        resultado = service.comprar_no_numerada(
            data["cliente_id"], 
            data["request_id"]
        )

    print(f"Request {data['request_id']}: {resultado.status} - {resultado.motivo}")
    # Confirmación manual a RabbitMQ para detectar si falla una venta y reintentarla
    #time.sleep(0.01)
    ch.basic_ack(delivery_tag=method.delivery_tag)

def iniciar_worker():
    try:
        #connection to rabbitmq
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()

        channel.queue_declare(queue='cola_tickets', durable=True) #durable= True para persistir si RabbitMQ se reinicia
        
        channel.basic_qos(prefetch_count=1)# Fair dispatch: espero a recibir el ack manual antes de enviar otro mensaje al mismo worker
        channel.basic_consume(queue='cola_tickets', on_message_callback=procesar_compra) #cuando llegue un mensaje llamar a procesar_compra

        print('Worker esperando mensajes.')
        channel.start_consuming()

    except Exception as e:
        print(f"Error en el Worker: {e}")

if __name__ == "__main__": #para mantener worker despierto
    iniciar_worker()
