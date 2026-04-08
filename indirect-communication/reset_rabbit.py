import pika

def reset_rabbit():
    try:
        # Conecto a rabbitmq y borro la cola de tickets para eliminar los mensajes acumulados y hacer pruebas limpias.
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()

        channel.queue_delete(queue='cola_tickets')
        
        print(" Cola 'cola_tickets' eliminada correctamente.")
        connection.close()
    except Exception as e:
        print(f"Error limpiando RabbitMQ: {e}")

if __name__ == "__main__":
    reset_rabbit()