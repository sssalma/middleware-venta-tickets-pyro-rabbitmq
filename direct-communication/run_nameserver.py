import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import Pyro4.naming
from config import PYRO_NS_HOST, PYRO_NS_PORT

if __name__ == "__main__":
    Pyro4.naming.startNSloop(host=PYRO_NS_HOST, port=PYRO_NS_PORT)