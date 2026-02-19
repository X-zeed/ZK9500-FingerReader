import subprocess
import psycopg2
import re

def is_base64(s):
    return re.fullmatch(r'[A-Za-z0-9+/=]+', s) is not None


# run exe
result = subprocess.run(
    ["fingerprint_wrapper.exe"],
    capture_output=True,
    text=True
)

lines = result.stdout.strip().splitlines()

template_base64 = None

# หา line ที่เป็น base64 จริง
for line in reversed(lines):
    line = line.strip()
    if len(line) > 100 and is_base64(line):
        template_base64 = line
        break

if not template_base64:
    print("❌ No valid fingerprint template found")
    exit()

print("Template =", template_base64[:60], "...")

# connect DB
conn = psycopg2.connect(
    host="localhost",
    database="fingerprint_db",
    user="postgres",
    password="Bill.53162",
    port=5432
)

cur = conn.cursor()

cur.execute("""
INSERT INTO fingerprints (user_id, template, template_size)
VALUES (%s, %s, %s)
""", (
    "Bill",
    template_base64.encode(),
    len(template_base64)
))

conn.commit()
cur.close()
conn.close()

print("Saved to DB ✔")
