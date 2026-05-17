import random
import os

def generar_hotspot(filename="benchmarks/bm_hotspot.txt", total_req=60000):
    dirpath = os.path.dirname(filename)
    if dirpath and not os.path.exists(dirpath):
        os.makedirs(dirpath)
    total_seats = 20000
    # 5% de los asientos = 1,000 asientos
    hot_seats_range = int(total_seats * 0.05) 
    
    with open(filename, "w") as f:
        for i in range(total_req):
            client_id = f"user{random.randint(1, 10000)}"
            request_id = f"{i}"
            
            # 80% de probabilidad de elegir uno de los 1,000 asientos "hot" y 20% de elegir uno de los 19,000 restantes
            if random.random() < 0.80:
                seat_id = random.randint(1, hot_seats_range)
            else:
                seat_id = random.randint(hot_seats_range + 1, total_seats)
                
            f.write(f"BUY {client_id} {seat_id} {request_id}\n")
    print(f"Benchmark generado: {filename} con {total_req} peticiones.")

if __name__ == "__main__":
    generar_hotspot()