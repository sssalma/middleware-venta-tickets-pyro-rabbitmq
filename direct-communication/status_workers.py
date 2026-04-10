from scaling_utils import get_workers


def main():
    workers = get_workers()

    print("=== ESTADO DE WORKERS ===")

    if not workers:
        print("No hay workers activos.")
        return

    print(f"Total activos: {len(workers)}")
    print("Lista de workers:")
    for worker in workers:
        print(f"  - Puerto {worker['port']} | PID {worker['pid']}")


if __name__ == "__main__":
    main()