import json
from urllib import request

url = "http://localhost:8080/buy_unnumbered"

datos = {
    "cliente_id": "c3",
    "request_id": "r500"
}

datos_json = json.dumps(datos).encode("utf-8")

req = request.Request(
    url,
    data=datos_json,
    headers={"Content-Type": "application/json"},
    method="POST"
)

with request.urlopen(req) as response:
    cuerpo = response.read().decode("utf-8")
    print(cuerpo)