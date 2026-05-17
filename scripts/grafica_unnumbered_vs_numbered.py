"""Graph: Unnumbered vs Numbered - faceted by architecture (2 subplots)."""
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('metricas_finales.csv')
df['workers'] = df['workers'].astype(int)

bm_unnumbered = 'benchmark_unnumbered_20000.txt'
bm_numbered = 'benchmark_numbered_60000.txt'

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

ticket_types = [
    ('unnumbered', bm_unnumbered, '#1565C0', 'o-', 'No numeradas'),
    ('numbered',   bm_numbered,   '#E65100', 's--', 'Numeradas (hotspot)'),
]

for ax_idx, (title, modelo) in enumerate([
    ('Arquitectura Directa (Pyro4)', 'directo'),
    ('Arquitectura Indirecta (RabbitMQ)', 'indirecto'),
]):
    ax = axes[ax_idx]
    for _, bm_file, color, marker, label in ticket_types:
        data = df[(df['modelo'] == modelo) & (df['benchmark'] == bm_file)].sort_values('workers')
        if data.empty:
            continue
        ax.plot(data['workers'], data['throughput'], marker,
                color=color, linewidth=2.5, markersize=9, label=label)

    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.set_xlabel('Número de Workers', fontsize=11)
    ax.set_ylabel('Throughput (ops/seg)', fontsize=11)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(sorted(df['workers'].unique()))

plt.suptitle('Comparativa: Entradas No Numeradas vs Numeradas', fontsize=14, fontweight='bold')
plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig('graficas/comparativa_unnumbered_vs_numbered.png', dpi=150)
print("Saved: graficas/comparativa_unnumbered_vs_numbered.png")
