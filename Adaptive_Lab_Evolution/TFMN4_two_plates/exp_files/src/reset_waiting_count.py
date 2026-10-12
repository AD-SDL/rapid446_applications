
import os
import sys

from dotenv import load_dotenv
from redis import Redis

# Add the root project folder (TFMN4 directory) to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


# loads .env into environment
load_dotenv()

redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")
redis_password = os.getenv("REDIS_PASSWORD")
exchange_auto_unlock_seconds = 86400 # 86400 seconds = 24 hours
exchange_lock_timeout = 7200 # 7200 seconds = 2 hours
exchange_waiters_key = "exchange_waiters"

redis = Redis(
    host=redis_host,
    port=redis_port,
    password=redis_password,
)

# At the very beginning of your experiment, before starting loops or acquiring any locks:
redis.set(exchange_waiters_key, 0)

# Optional: verify
waiters = int(redis.get(exchange_waiters_key) or 0)
print(f"Processes waiting for exchange lock (reset) = {waiters}", flush=True)
