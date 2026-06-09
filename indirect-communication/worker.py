import pika
import json
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base.redis_logica import RedisRepository
from base.tickets import tickets

# lógica de negocio
repo = RedisRepository()
service = tickets(repo)

def procesar_compra(ch, method, properties, body):
    data = json.loads(body)
    request_id = data["request_id"]
    now = time.time()

    repo.redis.setnx("worker:processing_started_at", now)

    repo.redis.set(f"worker:start:{request_id}", now)

    if "seat_id" in data:
        resultado = service.comprar_numerada(
            data["cliente_id"],
            data["seat_id"],
            request_id
        )
    else:
        resultado = service.comprar_no_numerada(
            data["cliente_id"],
            request_id
        )

    now_end = time.time()
    repo.redis.set(f"worker:end:{request_id}", now_end)
    repo.redis.set("worker:processing_finished_at", now_end)

    print(f"Request {request_id}: {resultado.status} - {resultado.motivo}")
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
