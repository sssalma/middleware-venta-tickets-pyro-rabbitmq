import Pyro4.naming

if __name__ == "__main__":
    Pyro4.naming.startNSloop(host="127.0.0.1", port=9090)