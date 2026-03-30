import redis
import json
from base.modelo_compra import ModeloCompra


class RedisRepository:

    def comprar_numerada(self, ):
        #1. Si esta request ya se procesó, devolvemos el resultado guardado
        #2. Validar asiento
        # 3. Intentar reservar el asiento
        # 4. Guardar el resultado de la request para idempotencia
        return 0
    
    def comprar_no_numerada(self, cliente_id: str, request_id: str) -> ModeloCompra:
        # Idempotencia para no revender en reintentos
        if self.redis.sismember("procesadas", request_id):
            return ModeloCompra(True, "OK", "ya_comprado_anteriormente", cliente_id, request_id)

        # Lógica de reserva atómica con contador de 0 a 20k
        tickets_vendidos = self.redis.incr("contador_tickets")
        if tickets_vendidos <= 20000:
            self.redis.sadd("procesadas", request_id)
            return ModeloCompra(True, "OK", "compra_exitosa", cliente_id, request_id)
        else:
            return ModeloCompra(False, "FAIL", "sold_out", cliente_id, request_id)