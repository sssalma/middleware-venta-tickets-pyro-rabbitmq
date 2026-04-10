import time
import json
import requests
import sys
import os
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://localhost:8080"
CSV_FILE = "metricas_finales.csv"

def enviar_peticion(linea):
    partes = linea.strip().split()
    if not partes: return None
    
    # Formato: BUY <client_id> <seat_id> <request_id>
    # O para no numerados (aunque el benchmark suele tener seat_id 0)
    if "unnumbered" in benchmark_global:
        url = f"{BASE_URL}/buy_unnumbered"
        payload = {"cliente_id": partes[1], "request_id": partes[3]}
    else:
        url = f"{BASE_URL}/buy_numbered"
        payload = {"cliente_id": partes[1], "seat_id": int(partes[2]), "request_id": partes[3]}
    
    try:
        r = requests.post(url, json=payload, timeout=5)
        return r.json()
    except:
        return {"status": "ERROR"}

def run_direct_benchmark(benchmark_path, num_workers):
    global benchmark_global
    benchmark_global = benchmark_path
    
    with open(benchmark_path, 'r') as f:
        lineas = [l for l in f.readlines() if l.startswith("BUY")]

    print(f"Iniciando Directo: {benchmark_path} con {num_workers} servidores...")
    
    # Usamos una concurrencia alta para saturar los servidores (ej: 100 hilos)
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=50) as executor:
        resultados = list(executor.map(enviar_peticion, lineas))
    end_time = time.time()
    
    total_time = end_time - start_time
    success = sum(1 for r in resultados if r and r.get("status") in ["SUCCESS", "OK"])
    fail = len(lineas) - success
    throughput = len(lineas) / total_time
    
    # Escribir en el CSV
    with open(CSV_FILE, "a") as f:
        f.write(f"directo,{os.path.basename(benchmark_path)},{num_workers},{total_time:.2f},{throughput:.2f},{success},{fail}\n")
    
    print(f"Finalizado. Tiempo: {total_time:.2f}s | Throughput: {throughput:.2f}")

if __name__ == "__main__":
    # Uso: python metricas_directas.py benchmarks/bm_hotspot.txt 4
    run_direct_benchmark(sys.argv[1], int(sys.argv[2]))