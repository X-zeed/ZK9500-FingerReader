import subprocess
import re
import time
from ConnectDB import get_connection


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


print("🔁 Waiting for fingerprint... (Ctrl+C to stop)\n")

last_template = None

try:
    while True:

        # ---------- scan ----------
        result = subprocess.run(
            ["Application/verify.exe"],
            capture_output=True,
            text=True
        )

        scan_template = extract_template(result.stdout)

        if not scan_template:
            time.sleep(0.5)
            continue

        # กันสแกนซ้ำ
        if scan_template == last_template:
            time.sleep(0.5)
            continue

        last_template = scan_template

        print("\n📥 Finger detected")
        print("Length =", len(scan_template))

        # ---------- connect DB ----------
        try:
            conn = get_connection()
            cur = conn.cursor()

            cur.execute("SELECT user_id, template FROM fingerprints")
            rows = cur.fetchall()

        except Exception as db_error:
            print("❌ DB Error:", db_error)
            time.sleep(1)
            continue

        print("DB rows =", len(rows))

        # ---------- compare ----------
        matched = False

        for user_id, db_template in rows:

            db_b64 = bytes(db_template).decode()

            compare = subprocess.run(
                ["Application/compare.exe", scan_template, db_b64],
                capture_output=True,
                text=True
            )

            output = compare.stdout.strip()

            try:
                score = int(output)
            except:
                print("❌ compare.exe output error:", repr(output))
                continue

            print(f"Compare {user_id} → {score}")

            if score > 60:
                print(f"\n✅ MATCH USER = {user_id}\n")
                matched = True
                break

        if not matched:
            print("\n❌ NO MATCH\n")

        time.sleep(1)

except KeyboardInterrupt:
    print("\n🛑 Stopped by user")