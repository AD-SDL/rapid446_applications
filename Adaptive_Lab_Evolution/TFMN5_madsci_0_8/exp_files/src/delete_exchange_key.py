import os
from dotenv import load_dotenv
from redis import Redis


load_dotenv()

redis = Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    password=os.getenv("REDIS_PASSWORD") or None,
)

redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")

redis = Redis(
    host=redis_host,
    port=redis_port,
    password=os.getenv("REDIS_PASSWORD") or None,
)

redis.delete("redlock:exchange_nest")
print("Deleted the exchange key!")