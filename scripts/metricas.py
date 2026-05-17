import time
import subprocess
import redis
import pika
import sys
import json
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Configuración
RABBIT_HOST = '192.168.1.131'
QUEUE_NAME = 'cola_tickets'
REDIS_HOST = '192.168.1.131'
REDIS_PORT = 6379

def get_rabbit_message_count():
    try:
        # Usa las credenciales que creaste (admin/admin) si es necesario
        credentials = pika.PlainCredentials('admin', 'admin')
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=RABBIT_HOST, 
            credentials=credentials
        ))
        channel = connection.channel()
        queue = channel.queue_declare(queue=QUEUE_NAME, durable=True, passive=True)
        count = queue.method.message_count
        connection.close()
        return count
    except Exception as e:
        # Esto te dirá por qué el cronómetro se para antes de tiempo
        print(f"Error consultando RabbitMQ: {e}")
        return -1 # Devolvemos -1 para que el bucle no crea que es 0

def run_experiment_indirect(benchmark_path, num_workers):
    print(f"\n{'='*50}")
    print(f"EXPERIMENTO INDIRECTO (RabbitMQ) - Workers: {num_workers}")
    print(f"Benchmark: {benchmark_path}")
    print(f"{'='*50}")
    
    # 1. Conexión a Redis
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    
    # 2. Inicio del cronómetro y ejecución del Producer
    print("[1/3] Lanzando Producer y enviando peticiones...")
    start_time = time.time()
    
    # Configuramos el entorno para asegurar que el productor encuentre los módulos
    env_vars = os.environ.copy()
    env_vars["PYTHONPATH"] = ROOT_DIR
    
    # Ejecutamos el script producer.py pasándole el benchmark
    subprocess.run(["python", os.path.join(ROOT_DIR, "indirect-communication", "producer.py"), benchmark_path], env=env_vars)
    
    # ... dentro de run_experiment_indirect ...
    print("[2/3] Procesando... (Esperando a que la cola se vacíe)")
    while True:
        count = get_rabbit_message_count()
        
        if count > 0:
            print(f"    > Mensajes pendientes: {count}    ", end="\r")
        elif count == 0:
            print("    > Cola vacía. Esperando margen de seguridad...")
            time.sleep(2.0)
            if get_rabbit_message_count() == 0: 
                break
        else:
            print("    > Esperando reconexión con RabbitMQ...          ", end="\r")
        
        time.sleep(1.0) # Aumenta un poco el tiempo entre consultas
    
    end_time = time.time()
    total_time = end_time - start_time

    # 4. Cálculo de métricas consultando directamente a Redis
    print("\n[3/3] Recopilando métricas de Redis...")
    
    all_requests_keys = r.keys("request:*")
    success = 0
    fail = 0
    
    for key in all_requests_keys:  
        val = r.get(key)
        if val:
            datos = json.loads(val)
            if datos.get("status") in ["SUCCESS", "OK"]:
                success += 1
            else:
                fail += 1

    # Caso especial: tickets no numerados
    no_num_success = r.scard("procesadas")
    if no_num_success > 0:
        success = no_num_success
        intentos = int(r.get("contador_tickets") or 0)
        fail = max(0, intentos - success)

    total_ops = success + fail
    throughput = total_ops / total_time if total_time > 0 else 0

    # Imprimir resultados por pantalla
    print("\n" + "*"*30)
    print(f"TIEMPO TOTAL:  {total_time:.2f} seg")
    print(f"THROUGHPUT:    {throughput:.2f} ops/seg")
    print(f"SUCCESS:       {success}")
    print(f"FAIL:          {fail}")
    print(f"TOTAL:         {total_ops}")
    print("*"*30)

    # Guardar en un CSV para gráficas
    csv_file = os.path.join(ROOT_DIR, "metricas_finales.csv")
    file_exists = os.path.isfile(csv_file)
    with open(csv_file, "a") as f:
        if not file_exists:
            f.write("modelo,benchmark,workers,tiempo,throughput,success,fail\n")
        f.write(f"indirecto,{os.path.basename(benchmark_path)},{num_workers},{total_time:.2f},{throughput:.2f},{success},{fail}\n")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python metricas.py <ruta_benchmark> <num_workers_activos>")
    else:
        run_experiment_indirect(sys.argv[1], sys.argv[2])