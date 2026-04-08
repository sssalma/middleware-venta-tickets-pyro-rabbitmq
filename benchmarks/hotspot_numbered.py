import os
import random

def generar_benchmark_numerados():

    total_lineas = 10000
    total_asientos = 20000

    # 5% de asientos (hotspot)
    num_hot = int(total_asientos * 0.05)  # 1000 asientos
    hot_seats = list(range(1, num_hot + 1))
    cold_seats = list(range(num_hot + 1, total_asientos + 1))

    with open('benchmarks/bm_hotspot_numerados.txt', 'w') as f:
        f.write("# Concert Ticket Benchmark  Numbered Seats\n")
        f.write("# Seats: 1..20000\n")
        f.write("# 80% of requests target 5% of seats\n")
        f.write("# Format: BUY <client_id> <seat_id> <request_id>\n\n")

        for i in range(1, total_lineas + 1):
            # 80% hotspot
            if random.random() < 0.8:
                seat_id = random.choice(hot_seats)
            else:
                seat_id = random.choice(cold_seats)

            f.write(f"BUY user{i:05d} {seat_id} {i:05d}\n")

    print("bm_hotspot_numerados.txt generado.")

if __name__ == "__main__":
    generar_benchmark_numerados()