import os

PYRO_NS_HOST = os.environ.get("PYRO_NS_HOST", "localhost")
PYRO_NS_PORT = int(os.environ.get("PYRO_NS_PORT", "9090"))
PYRO_NAT_HOST = os.environ.get("PYRO_NAT_HOST", "")

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))

RABBIT_HOST = os.environ.get("RABBIT_HOST", "localhost")
RABBIT_USER = os.environ.get("RABBIT_USER", "admin")
RABBIT_PASSWORD = os.environ.get("RABBIT_PASSWORD", "admin")

QUEUE_NAME = os.environ.get("QUEUE_NAME", "cola_tickets")

CLIENT_NUM_HILOS = int(os.environ.get("CLIENT_NUM_HILOS", "10"))
