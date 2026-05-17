import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.redis_logica import RedisRepository
from base.tickets import tickets

repo = RedisRepository()
service = tickets(repo)

print(service.comprar_numerada("c1", 10, "r1").to_dict())
print(service.comprar_numerada("c2", 10, "r2").to_dict())
print(service.comprar_no_numerada("c3", "r3").to_dict())

repo.redis.flushdb()