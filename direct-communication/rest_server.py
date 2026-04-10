import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from datetime import datetime

from base.redis_logica import RedisRepository
from base.tickets import tickets

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5000))

repo = RedisRepository()
service = tickets(repo)


def log(msg):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] [WORKER {PORT}] {msg}", flush=True)


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

            log(f"PETICIÓN {self.path} | body={datos}")

            if self.path == "/buy_numbered":
                cliente_id = datos.get("cliente_id")
                seat_id = datos.get("seat_id")
                request_id = datos.get("request_id")

                try:
                    seat_id = int(seat_id)
                except Exception:
                    respuesta = {
                        "ok": False,
                        "status": "FAIL",
                        "motivo": "seat_id_debe_ser_int"
                    }
                    log(f"RESULTADO /buy_numbered | cliente={cliente_id} seat={seat_id} request={request_id} -> {respuesta}")
                    self._send_json(400, respuesta)
                    return

                resultado = service.comprar_numerada(cliente_id, seat_id, request_id)
                respuesta = resultado.to_dict()

                log(
                    f"RESULTADO /buy_numbered | cliente={cliente_id} seat={seat_id} "
                    f"request={request_id} -> status={respuesta['status']} motivo={respuesta['motivo']}"
                )

                self._send_json(200, respuesta)

            elif self.path == "/buy_unnumbered":
                cliente_id = datos.get("cliente_id")
                request_id = datos.get("request_id")

                resultado = service.comprar_no_numerada(cliente_id, request_id)
                respuesta = resultado.to_dict()

                log(
                    f"RESULTADO /buy_unnumbered | cliente={cliente_id} request={request_id} "
                    f"-> status={respuesta['status']} motivo={respuesta['motivo']}"
                )

                self._send_json(200, respuesta)

            else:
                respuesta = {
                    "ok": False,
                    "status": "FAIL",
                    "motivo": "ruta_no_encontrada"
                }
                log(f"RUTA DESCONOCIDA {self.path}")
                self._send_json(404, respuesta)

        except Exception as e:
            log(f"ERROR INTERNO en {self.path}: {str(e)}")
            self._send_json(500, {
                "ok": False,
                "status": "FAIL",
                "motivo": f"error_interno: {str(e)}"
            })

    def log_message(self, format, *args):
        # Esto evita los logs por defecto feos de BaseHTTPRequestHandler
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), MyHandler)
    log(f"Servidor corriendo en puerto {PORT}...")
    server.serve_forever()