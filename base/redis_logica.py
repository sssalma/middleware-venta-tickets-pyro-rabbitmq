import redis
import json
from base.modelo_compra import ModeloCompra


class RedisRepository:

    def comprar_numerada(self, ):
        #1. Si esta request ya se procesó, devolvemos el resultado guardado
        #2. Validar asiento
        # 3. Intentar reservar el asiento
        # 4. Guardar el resultado de la request para idempotencia
        