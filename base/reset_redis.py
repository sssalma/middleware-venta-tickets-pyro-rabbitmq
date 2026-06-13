import sys
import os
import redis

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import REDIS_HOST, REDIS_PORT

def reset_redis():
    r = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=0,
        decode_responses=True
    )

    print("Limpiando Redis...")

    # Borra toda la base de datos
    r.flushdb()

    print("Redis limpiado correctamente.")

if __name__ == "__main__":
    reset_redis()