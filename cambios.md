# Cambios realizados

## Objetivo
Mover el cálculo de tiempos totales del modelo indirecto al lado del servidor (workers), registrando timestamps en Redis.

## Archivos modificados

### `indirect-communication/worker.py`
Se agregó instrumentación de tiempos en `procesar_compra()`:
- `worker:processing_started_at` — timestamp del primer mensaje procesado (solo se crea una vez con `setnx`)
- `worker:start:<request_id>` — timestamp por cada mensaje al comenzar a procesarlo
- `worker:end:<request_id>` — timestamp por cada mensaje al terminar de procesarlo
- `worker:processing_finished_at` — se actualiza con cada mensaje, quedando el del último procesado

### `scripts/metricas.py`
Se reemplazó el cálculo local de `tiempo_total` por la lectura de los timestamps que el worker guardó en Redis:
- Lee `worker:processing_started_at` y `worker:processing_finished_at`
- Calcula `tiempo_total` y `tiempo_procesamiento` desde esos valores del servidor
- Mantiene `tiempo_envio` calculado localmente (lado del orquestador)
- Incluye fallback a cálculo local si no hay datos del worker

## Comportamiento
- Las métricas ahora reflejan el tiempo real de procesamiento en los workers
- Los tiempos se registran del lado del servidor (server-side) como indicó el profesor
- El CSV exporta los mismos campos pero con valores calculados desde Redis
