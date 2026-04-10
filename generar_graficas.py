import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def generar_visualizaciones():
    try:
        # Cargar los datos (asegúrate de que el CSV esté actualizado con tus nuevos números)
        df = pd.read_csv("metricas_finales.csv")
        df = df[df['modelo'] == 'indirecto']
    except FileNotFoundError:
        print("Error: No se encuentra 'metricas_finales.csv'")
        return

    # Preparar datos por benchmark
    df_unnum = df[df['benchmark'].str.contains('unnumbered_20000')].sort_values('workers')
    df_hot = df[df['benchmark'] == 'bm_hotspot.txt'].sort_values('workers')
    df_uni = df[df['benchmark'] == 'bm_uniforme.txt'].sort_values('workers')

    # --- GRÁFICA 1: THROUGHPUT TOTAL (Capacidad de procesamiento) ---
    plt.figure(figsize=(10, 6))
    plt.plot(df_unnum['workers'], df_unnum['throughput'], 'o-', label='Sin Contención (20k)', color='#3498db')
    plt.plot(df_uni['workers'], df_uni['throughput'], 's-', label='Numerado Uniforme (60k)', color='#27ae60')
    plt.plot(df_hot['workers'], df_hot['throughput'], 'd--', label='Numerado Hotspot (60k)', color='#e74c3c')

    plt.title('Comparativa de Throughput: El impacto de la carga', fontsize=14)
    plt.xlabel('Número de Workers', fontsize=12)
    plt.ylabel('Operaciones por Segundo (ops/s)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig('grafica_1_throughput.png')

    # --- GRÁFICA 2: SPEEDUP (Escalabilidad Real) ---
    # Speedup = Tiempo(1 worker) / Tiempo(N workers). Ideal = N
    plt.figure(figsize=(10, 6))
    
    for label, data, color in [('Uniforme', df_uni, '#27ae60'), ('Hotspot', df_hot, '#e74c3c')]:
        t1 = data[data['workers'] == 1]['tiempo'].values[0]
        speedup = t1 / data['tiempo']
        plt.plot(data['workers'], speedup, 'o-', label=f'Speedup {label}', color=color)

    # Línea de escalabilidad ideal
    workers_range = df_uni['workers'].unique()
    plt.plot(workers_range, workers_range, 'k--', alpha=0.5, label='Escalabilidad Ideal')

    plt.title('Análisis de Speedup: ¿Realmente escalamos?', fontsize=14)
    plt.xlabel('Número de Workers', fontsize=12)
    plt.ylabel('Factor de Aceleración (X veces más rápido)', fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig('grafica_2_speedup.png')

    # --- GRÁFICA 3: GOODPUT (Ventas exitosas/seg) ---
    plt.figure(figsize=(10, 6))
    plt.bar(['Uniforme (15w)', 'Hotspot (15w)'], 
            [df_uni[df_uni['workers']==15]['success'].values[0] / df_uni[df_uni['workers']==15]['tiempo'].values[0],
             df_hot[df_hot['workers']==15]['success'].values[0] / df_hot[df_hot['workers']==15]['tiempo'].values[0]],
            color=['#2ecc71', '#e67e22'])
    plt.title('Goodput: Ventas reales confirmadas por segundo', fontsize=14)
    plt.ylabel('Éxitos / Segundo')
    plt.savefig('grafica_3_goodput.png')

    print("✓ Gráficas generadas: throughput, speedup y goodput.")

if __name__ == "__main__":
    generar_visualizaciones()