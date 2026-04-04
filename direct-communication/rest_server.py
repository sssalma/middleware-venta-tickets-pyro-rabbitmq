import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json

from base.redis_logica import RedisRepository
from base.tickets import tickets

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5000))

repo = RedisRepository()
service = tickets(repo)


class MyHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            datos = json.loads(body.decode("utf-8")) if body else {}

            if self.path == "/buy_numbered":
                cliente_id = datos.get("cliente_id")
                seat_id = datos.get("seat_id")
                request_id = datos.get("request_id")

                try:
                    seat_id = int(seat_id)
                except:
                    self._send_json(400, {
                        "ok": False,
                        "status": "FAIL",
                        "motivo": "seat_id_debe_ser_int"
                    })
                    return

                resultado = service.comprar_numerada(cliente_id, seat_id, request_id)
                self._send_json(200, resultado.to_dict())

            elif self.path == "/buy_unnumbered":
                cliente_id = datos.get("cliente_id")
                request_id = datos.get("request_id")

                resultado = service.comprar_no_numerada(cliente_id, request_id)
                self._send_json(200, resultado.to_dict())

            else:
                self._send_json(404, {
                    "ok": False,
                    "status": "FAIL",
                    "motivo": "ruta_no_encontrada"
                })

        except Exception as e:
            self._send_json(500, {
                "ok": False,
                "status": "FAIL",
                "motivo": f"error_interno: {str(e)}"
            })


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), MyHandler)
    print(f"Servidor corriendo en puerto {PORT}...")
    server.serve_forever()