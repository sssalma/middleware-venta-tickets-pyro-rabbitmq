import random
import os

def generar_distribuido(filename="benchmarks/bm_uniforme.txt", total_req=60000):
    # Asegurar que existe la carpeta
    dirpath = os.path.dirname(filename)
    if dirpath and not os.path.exists(dirpath):
        os.makedirs(dirpath)
        
    total_seats = 20000
    
    with open(filename, "w") as f:
        for i in range(total_req):
            client_id = f"user{random.randint(1, 10000)}"
            request_id = f"{i}"
            
            # Distribución UNIFORME: todos los asientos tienen la misma probabilidad
            seat_id = random.randint(1, total_seats)
                
            f.write(f"BUY {client_id} {seat_id} {request_id}\n")
            
    print(f"Benchmark generado: {filename} con {total_req} peticiones (Distribución uniforme).")

if __name__ == "__main__":
    generar_distribuido()