import time, random, logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

while True:
    event = random.choice(["ok", "db_timeout", "oom_warning"])
    if event == "ok":
        logging.info("GET /api/checkout 200 OK - 42ms")
    elif event == "db_timeout":
        logging.error("psycopg2.OperationalError: connection to server at 'db-prod' (10.0.1.5), port 5432 failed: timeout expired")
    elif event == "oom_warning":
        logging.critical("MemoryError: Worker process exceeded 512MB container limit during payload serialization")
    time.sleep(2)
