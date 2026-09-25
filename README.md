# Venta de tickets distribuida: comunicación directa vs. indirecta

Sistema de venta de entradas implementado **dos veces sobre el mismo núcleo de negocio**,
una con comunicación **directa** (RPC con Pyro4) y otra con comunicación **indirecta**
(cola de mensajes con RabbitMQ), para comparar ambos modelos de middleware bajo carga.

> Task 1 de *Sistemes Distribuïts* — Grau en Enginyeria Informàtica, URV.
> Trabajo en pareja. Desplegado y medido también sobre AWS.

## La idea

La lógica de venta vive en `base/` y es agnóstica al transporte. Encima se montan dos
middlewares distintos, de modo que la comparativa mide el modelo de comunicación y no
diferencias de implementación:

```text
                    ┌─ direct-communication/    cliente ──RPC──► frontend ──► servidor Pyro
base/ (lógica)  ────┤
                    └─ indirect-communication/  producer ──► cola RabbitMQ ──► N workers
                                    │
                                    └──────────► Redis (estado de asientos)
```

- **Directa** — Pyro4 con *name server*: el cliente invoca métodos remotos y espera la
  respuesta. Latencia baja, pero el cliente queda acoplado y bloqueado.
- **Indirecta** — RabbitMQ: el productor encola la compra y varios workers concurrentes
  la consumen. Desacopla productor y consumidor y permite escalar horizontalmente
  añadiendo workers, a cambio de perder la respuesta inmediata.

## Dos modalidades de venta

- **Numerada** — el cliente pide un asiento concreto (1–20000). Solo uno puede
  conseguirlo.
- **No numerada** — el cliente pide "una entrada cualquiera" del aforo disponible.

## Concurrencia e idempotencia

Ambos caminos comparten `base/redis_logica.py`, que resuelve los dos problemas duros:

- **Exclusión mutua sobre el asiento**: la reserva se hace con una operación atómica de
  Redis, de forma que dos clientes que piden el mismo asiento a la vez no pueden
  obtenerlo los dos.
- **Idempotencia**: cada compra lleva un `request_id`. Antes de procesar, el repositorio
  comprueba si esa petición ya se resolvió y, si es así, devuelve **el resultado
  original** en lugar de volver a ejecutarla. Esto es lo que hace seguro el reintento en
  el modelo indirecto, donde un mensaje puede reentregarse.

El resultado de toda compra se normaliza en `modelo_compra` (`ok`, `status`, `motivo`,
`cliente_id`, `request_id`, `seat_id`), igual en los dos modelos.

## Contenido

| Ruta | Descripción |
|---|---|
| `base/` | Lógica de negocio (`tickets.py`), repositorio Redis y modelo de respuesta |
| `direct-communication/` | Servidor, frontend, cliente y name server de Pyro4 |
| `indirect-communication/` | Productor y worker de RabbitMQ, más el reset de la cola |
| `scripts/` | Generadores de carga (uniforme y hotspot) y cálculo de métricas |
| `benchmarks/` | Trazas de las ejecuciones (hasta 60.000 peticiones) |
| `tests/` | Tests unitarios y de integración |
| `config.py` | Configuración por variables de entorno |
| `Documentacion.pdf` | Memoria con el análisis comparativo |

## Puesta en marcha

```bash
pip install -r requirements.txt   # Pyro4, pika, redis
```

Hacen falta un **Redis** y, para el modo indirecto, un **RabbitMQ** en marcha.

**Comunicación directa:**

```bash
python direct-communication/run_nameserver.py
python direct-communication/server_pyro.py
python direct-communication/frontend_pyro.py
python direct-communication/client_pyro.py
```

**Comunicación indirecta:**

```bash
python indirect-communication/worker.py    # lanzar varios, uno por terminal
python indirect-communication/producer.py
```

## Benchmarks

Dos patrones de carga, elegidos para estresar cosas distintas:

- **Uniforme** (`bm_numbered_uniforme.py`) — asientos repartidos al azar; mide el
  rendimiento en el caso favorable.
- **Hotspot** (`hotspot_numbered.py`) — muchos clientes peleando por los mismos
  asientos; mide el coste real de la contención.

```bash
bash scripts/run_all_benchmarks.sh
python scripts/metricas.py          # → throughput y latencias
```

Los resultados agregados están en `metricas_finaless.csv` y las trazas en `benchmarks/`.

## Configuración

Todo se ajusta por variables de entorno (ver `config.py`): `REDIS_HOST`, `REDIS_PORT`,
`RABBIT_HOST`, `RABBIT_USER`, `RABBIT_PASSWORD`, `QUEUE_NAME`, `PYRO_NS_HOST`,
`PYRO_NS_PORT`, `PYRO_NAT_HOST` (necesaria al desplegar en AWS, donde la IP pública no
coincide con la de la interfaz) y `CLIENT_NUM_HILOS`.

## Stack

Python · Pyro4 · RabbitMQ (pika) · Redis · AWS EC2
