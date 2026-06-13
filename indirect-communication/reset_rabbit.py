import sys
import os
import pika

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import RABBIT_HOST, RABBIT_USER, RABBIT_PASSWORD, QUEUE_NAME

def reset_rabbit():
    try:
        credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASSWORD)
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBIT_HOST, credentials=credentials))
        channel = connection.channel()

        channel.queue_delete(queue=QUEUE_NAME)
        
        print(" Cola 'cola_tickets' eliminada correctamente.")
        connection.close()
    except Exception as e:
        print(f"Error limpiando RabbitMQ: {e}")

if __name__ == "__main__":
    reset_rabbit()