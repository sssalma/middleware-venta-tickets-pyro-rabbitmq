"""
Genera graficas a partir de metricas_finales.csv
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(ROOT_DIR, "metricas_finales.csv")
OUTPUT_DIR = os.path.join(ROOT_DIR, "graficas")

os.makedirs(OUTPUT_DIR, exist_ok=True)

df = pd.read_csv(CSV)
df["workers"] = df["workers"].astype(int)

benchmarks = df["benchmark"].unique()
modelos = df["modelo"].unique()
colores = {"directo": "#2196F3", "indirecto": "#FF5722"}
marcadores = {"directo": "o-", "indirecto": "s--"}

# 1. Throughput vs Workers (una grafica por benchmark)
for bm in benchmarks:
    plt.figure(figsize=(10, 6))
    subset = df[df["benchmark"] == bm]
    for mod in modelos:
        data = subset[subset["modelo"] == mod].sort_values("workers")
        if data.empty:
            continue
        plt.plot(data["workers"], data["throughput"], marcadores[mod],
                 color=colores[mod], linewidth=2, markersize=8,
                 label=mod.capitalize())

    nombre_corto = bm.replace(".txt", "").replace("benchmark_", "")
    plt.title(f"Throughput vs Workers - {nombre_corto}", fontsize=14, fontweight="bold")
    plt.xlabel("Numero de Workers", fontsize=12)
    plt.ylabel("Throughput (ops/seg)", fontsize=12)
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)
    plt.xticks(sorted(df[df["benchmark"] == bm]["workers"].unique()))
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f"throughput_{nombre_corto}.png"), dpi=150)
    plt.close()
    print(f"  Grafica: throughput_{nombre_corto}.png")

# 2. Grafica combinada: hotspot throughput para ambos modelos
plt.figure(figsize=(12, 8))
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
axes = axes.flatten()

for idx, bm in enumerate(benchmarks):
    ax = axes[idx]
    subset = df[df["benchmark"] == bm]
    for mod in modelos:
        data = subset[subset["modelo"] == mod].sort_values("workers")
        if data.empty:
            continue
        ax.plot(data["workers"], data["throughput"], marcadores[mod],
                color=colores[mod], linewidth=2, markersize=8,
                label=mod.capitalize())

    nombre_corto = bm.replace(".txt", "").replace("benchmark_", "")
    ax.set_title(nombre_corto, fontsize=12, fontweight="bold")
    ax.set_xlabel("Workers", fontsize=10)
    ax.set_ylabel("Throughput (ops/seg)", fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

plt.suptitle("Throughput vs Workers - Todos los benchmarks", fontsize=14, fontweight="bold")
plt.tight_layout(rect=[0, 0, 1, 0.97])
plt.savefig(os.path.join(OUTPUT_DIR, "combinado_throughput.png"), dpi=150)
plt.close()
print("  Grafica: combinado_throughput.png")

print(f"\nTodas las graficas guardadas en '{OUTPUT_DIR}/'")
print("Generadas:", os.listdir(OUTPUT_DIR))
