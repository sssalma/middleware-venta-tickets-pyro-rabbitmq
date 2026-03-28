from base.modelo_compra import modelo_compra


class tickets:
    def __init__(self, repository):
        self.repository = repository

    def comprar_numerada(self, cliente_id: str, seat_id: int, request_id: str) -> modelo_compra:
        # si no hay cliente_id o request_id es una peticion a la que le falta info
        if not cliente_id or not request_id:
            return modelo_compra(
                ok=False,
                status="FAIL",
                motivo="faltan_datos",
                cliente_id=cliente_id,
                request_id=request_id,
                seat_id=seat_id
            )

        # si no es un entero el asiento da error
        if not isinstance(seat_id, int):
            return modelo_compra(
                ok=False,
                status="FAIL",
                motivo="seat_id_debe_ser_int",
                cliente_id=cliente_id,
                request_id=request_id,
                seat_id=seat_id
            )

        return self.repository.comprar_numerada(cliente_id, seat_id, request_id)
    

    # AQUI PONER COMPRA NO NUMERADA
