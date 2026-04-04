import redis

def reset_redis():
    r = redis.Redis(
        host="localhost",
        port=6379,
        db=0,
        decode_responses=True
    )

    print("Limpiando Redis...")

    # Borra toda la base de datos
    r.flushdb()

    print("Redis limpiado correctamente.")

if __name__ == "__main__":
    reset_redis()