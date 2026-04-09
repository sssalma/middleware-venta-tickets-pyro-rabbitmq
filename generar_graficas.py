import pandas as pd
import matplotlib.pyplot as plt

def generar_visualizaciones():
    # 1. Cargar los datos del CSV
    try:
        df = pd.read_csv("metricas_finales.csv")
        # Aseguramos que solo usamos el modelo indirecto para estas gráficas
        df = df[df['modelo'] == 'indirecto']
    except FileNotFoundError:
        print("No se encuentra el archivo 'metricas_finales.csv'")
        return

    # --- GRÁFICA A: ESCALABILIDAD (Throughput vs Workers) ---
    df_esc = df[df['benchmark'].str.contains('unnumbered_20000')].sort_values('workers')
    
    if not df_esc.empty:
        plt.figure(figsize=(10, 6))
        plt.plot(df_esc['workers'], df_esc['throughput'], marker='o', linewidth=2, color='#3498db', label='Sin Contención (20k)')
        plt.title('Análisis de Escalabilidad: Throughput vs Workers', fontsize=14)
        plt.xlabel('Número de Workers Activos', fontsize=12)
        plt.ylabel('Operaciones por Segundo (ops/seg)', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        plt.savefig('grafica_escalabilidad.png')
        print("✓ Generada: grafica_escalabilidad.png")

    # --- GRÁFICA B: ÉXITOS VS FALLOS (Benchmark Hotspot 60k) ---
    # Usamos tu último test de bm_hotspot con 4 workers para mostrar el impacto
    df_hot_pie = df[(df['benchmark'].str.contains('bm_hotspot')) & (df['workers'] == 4)].iloc[-1:]
    
    if not df_hot_pie.empty:
        plt.figure(figsize=(8, 8))
        labels = ['Ventas Exitosas', 'Fallos (Contención/Sold Out)']
        sizes = [df_hot_pie['success'].values[0], df_hot_pie['fail'].values[0]]
        colors = ['#2ecc71', '#e74c3c']
        
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors, explode=(0.05, 0))
        plt.title('Distribución de Resultados bajo Alta Contención (Hotspot)', fontsize=14)
        plt.savefig('grafica_hotspot_pie.png')
        print("✓ Generada: grafica_hotspot_pie.png")

    # --- GRÁFICA C: COMPARATIVA DE ESCALABILIDAD (Ideal vs Hotspot) ---
    # Esta es la que pedías para ver el "Throughput Collapse"
    df_ideal = df[df['benchmark'].str.contains('unnumbered_20000')].sort_values('workers')
    df_contencion = df[df['benchmark'].str.contains('bm_hotspot')].sort_values('workers')

    if not df_ideal.empty and not df_contencion.empty:
        plt.figure(figsize=(10, 6))
        
        # Línea Ideal (Verde)
        plt.plot(df_ideal['workers'], df_ideal['throughput'], 
                 marker='o', linewidth=2, color='#27ae60', label='Escalabilidad Ideal (Sin Contención)')
        
        # Línea Hotspot (Roja)
        plt.plot(df_contencion['workers'], df_contencion['throughput'], 
                 marker='s', linewidth=2, color='#e74c3c', linestyle='--', label='Escalabilidad con Hotspot (80/5)')

        plt.title('Comparativa: Impacto de la Contención en la Escalabilidad', fontsize=14)
        plt.xlabel('Número de Workers Activos', fontsize=12)
        plt.ylabel('Throughput Total (ops/seg)', fontsize=12)
        plt.xticks([1, 2, 4])
        plt.grid(True, linestyle=':', alpha=0.6)
        plt.legend()
        
        # Añadimos una anotación para resaltar la brecha
        plt.annotate('Pérdida de eficiencia', 
                     xy=(4, df_contencion[df_contencion['workers']==4]['throughput'].values[0]), 
                     xytext=(2, 600),
                     arrowprops=dict(facecolor='black', shrink=0.05, width=1))

        plt.savefig('grafica_comparativa_hotspot.png')
        print("✓ Generada: grafica_comparativa_hotspot.png")

if __name__ == "__main__":
    generar_visualizaciones()