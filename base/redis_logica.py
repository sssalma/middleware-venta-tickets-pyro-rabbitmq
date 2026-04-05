import redis
import json
from base.modelo_compra import modelo_compra


class RedisRepository:
    def __init__(self):
        self.redis = redis.Redis(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=True
        )

    def comprar_numerada(self, cliente_id, seat_id, request_id):
        clave_request = f"request:{request_id}"

        # 1. Si ya se procesó esta request, devolver lo mismo
        if self.redis.exists(clave_request):
            datos = json.loads(self.redis.get(clave_request))       # type: ignore
            return modelo_compra(
                ok=datos["ok"],
                status=datos["status"],
                motivo=datos["motivo"],
                cliente_id=datos["cliente_id"],
                request_id=datos["request_id"],
                seat_id=datos["seat_id"]
            )

        # 2. Validar asiento
        if seat_id < 1 or seat_id > 20000:
            resultado = modelo_compra(
                ok=False,
                status="FAIL",
                motivo="invalid_seat_id",
                cliente_id=cliente_id,
                request_id=request_id,
                seat_id=seat_id
            )
            self.redis.set(clave_request, json.dumps(resultado.to_dict()))
            return resultado

        # 3. Intentar reservar el asiento
        clave_asiento = f"seat:{seat_id}"
        reservado = self.redis.set(clave_asiento, cliente_id, nx=True)

        if reservado:
            resultado = modelo_compra(
                ok=True,
                status="SUCCESS",
                motivo="seat_reserved",
                cliente_id=cliente_id,
                request_id=request_id,
                seat_id=seat_id
            )
        else:
            resultado = modelo_compra(
                ok=False,
                status="FAIL",
                motivo="seat_already_sold",
                cliente_id=cliente_id,
                request_id=request_id,
                seat_id=seat_id
            )

        # 4. Guardar resultado para idempotencia
        self.redis.set(clave_request, json.dumps(resultado.to_dict()))
        return resultado
    
    def comprar_no_numerada(self, cliente_id: str, request_id: str) -> modelo_compra:
        # Idempotencia para no revender en reintentos
        if self.redis.sismember("procesadas", request_id):
            return modelo_compra(True, "OK", "ya_comprado_anteriormente", cliente_id, request_id)

        # Lógica de reserva atómica con contador de 0 a 20k
        tickets_vendidos = self.redis.incr("contador_tickets")
        if tickets_vendidos <= 20000: # type: ignore
            self.redis.sadd("procesadas", request_id)
            return modelo_compra(True, "OK", "compra_exitosa", cliente_id, request_id)
        else:
            return modelo_compra(False, "FAIL", "sold_out", cliente_id, request_id)