import subprocess
import psycopg2
import re

# ---------- helper ----------
def is_base64(s):
    return re.fullmatch(r'[A-Za-z0-9+/=]+', s) is not None


def extract_template(output):
    lines = output.strip().splitlines()

    for line in reversed(lines):
        line = line.strip()
        if len(line) > 100 and is_base64(line):
            return line

    return None


# ---------- scan fingerprint ----------
result = subprocess.run(
    ["verify.exe"],
    capture_output=True,
    text=True
)

scan_template = extract_template(result.stdout)

if not scan_template:
    print("❌ Scan failed")
    print(result.stdout)
    exit()

print("✅ Scanned template OK")
print("Length =", len(scan_template))


# ---------- connect DB ----------
conn = psycopg2.connect(
    host="localhost",
    database="fingerprint_db",
    user="postgres",
    password="Bill.53162",
    port=5432
)
cur = conn.cursor()

cur.execute("SELECT user_id, template FROM fingerprints")
rows = cur.fetchall()

print("DB rows =", len(rows))


# ---------- compare ----------
matched = False

for user_id, db_template in rows:

    db_b64 = bytes(db_template).decode()

    compare = subprocess.run(
        ["compare.exe", scan_template, db_b64],
        capture_output=True,
        text=True
    )

    output = compare.stdout.strip()

    print("\n--- Comparing with", user_id, "---")
    print("stdout =", repr(output))
    print("stderr =", repr(compare.stderr))
    print("returncode =", compare.returncode)

    # parse score
    try:
        score = int(output)
    except:
        print("❌ invalid score output")
        continue

    print("SCORE =", score)

    if score > 60:
        print("\n✅ MATCH USER =", user_id)
        matched = True
        break

if not matched:
    print("\n❌ NO MATCH")


cur.close()
conn.close()
