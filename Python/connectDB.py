import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="fingerprint_db",
    user="postgres",
    password="Bill.53162",
    port=5432
)

print("Connected OK")
