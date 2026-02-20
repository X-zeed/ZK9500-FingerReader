# 🖐 Fingerprint Access Control System — PyQt5 + PostgreSQL

ระบบสแกนลายนิ้วมือแบบ GUI สำหรับ
**ลงทะเบียน → ตรวจสอบตัวตน → ดูข้อมูลในฐานข้อมูล**
ออกแบบ UI แบบ Clean Light พร้อม animation scanner ring

พัฒนาโดยใช้:

- Python
- PyQt5 GUI Framework
- PostgreSQL Database
- External Fingerprint SDK (.exe)

---

# 📦 Project Overview

แอปนี้เป็นโปรแกรม GUI เต็มรูปแบบ ไม่ใช่ script console

มี 3 หน้าในโปรแกรม:

| Page     | Function                |
| -------- | ----------------------- |
| REGISTER | สแกน + บันทึกลายนิ้วมือ |
| VERIFY   | ตรวจสอบตัวตน            |
| RECORDS  | ดูข้อมูลในฐานข้อมูล     |

---

# 📁 Project Structure

```
project/
│
├── Application/
│   ├── save.exe        # capture fingerprint
│   ├── verify.exe      # scan fingerprint
│   └── compare.exe     # compare template
│
├── fingerprint_app.py  # main GUI application
├── .env                # database config
└── README.md
```

---

# ⚙️ Installation

ติดตั้ง dependencies

```
pip install psycopg2-binary python-dotenv PyQt5
```

---

# 🔐 Environment Configuration

สร้างไฟล์ `.env`

```
DB_HOST=localhost
DB_NAME=fingerprint_db
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_PORT=5432
```

**ห้ามอัปโหลด `.env` ขึ้น Git**

เพิ่ม `.gitignore`

```
.env
```

---

# 🗄 Database Schema

```
CREATE TABLE fingerprints (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    template BYTEA,
    template_size INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

# ▶️ Run Program

```
python fingerprint_app.py
```

---

# 🧠 System Workflow

## Register Fingerprint

```
save.exe → Python → PostgreSQL
```

ขั้นตอน:

1. กด CAPTURE
2. เรียก save.exe
3. ดึง Base64 template
4. กรอกชื่อ / ID
5. บันทึกลง database

---

## Verify Fingerprint

```
verify.exe → Python → compare.exe → match DB
```

ขั้นตอน:

1. กด VERIFY
2. scan ลายนิ้วมือ
3. โหลด template จาก DB
4. compare ทีละ record
5. ถ้าคะแนน > 60 → ACCESS GRANTED

---

## Records Page

โหลดข้อมูลจาก database แล้วแสดงใน table

สามารถ:

- refresh
- search
- filter

---

# 🎨 UI Features

ระบบ UI ถูกออกแบบให้มี:

- animated scanner ring
- ripple animation
- status color system
- adaptive scaling layout
- modern panel cards
- live clock
- status badges
- access log panel

---

# 🧩 Architecture Design

โครงสร้างระบบแยกเป็น layer:

### Thread Workers

ทำงาน background เพื่อไม่ให้ GUI ค้าง

- `ScanWorker`
- `VerifyWorker`

---

### Core Logic

```
extract_template() → parse template จาก exe output
is_base64()        → validate template
get_connection()   → database connector
```

---

### UI Components

Reusable widgets:

- ScannerRing
- PanelCard
- NavButton
- StatusBar
- styled_input
- big_btn

---

# ⚡ Performance Notes

เวอร์ชันปัจจุบัน:

- compare ทีละ record
- โหลด DB ทุกครั้ง
- subprocess call exe ทุก scan

ถ้าจะ optimize เพิ่ม:

- RAM cache templates
- multiprocessing compare
- async subprocess
- connection pooling

---

# 🛠 Troubleshooting

## Scanner ไม่ทำงาน

ตรวจสอบ:

- driver fingerprint reader
- path Application/\*.exe
- permission run exe

---

## Database Error

ตรวจสอบ:

- PostgreSQL run อยู่
- ค่าใน `.env`
- port ถูกต้อง

---

## Verify แล้ว match ไม่เจอ

ตรวจสอบ:

- template ใน DB ถูกต้อง
- compare.exe return score จริง
- threshold score (ปัจจุบัน > 60)

---

# 🔒 Security Notes

ระบบนี้:

- เก็บ template เป็น BYTEA
- ไม่เก็บภาพลายนิ้วมือ
- ไม่เก็บ raw scan

---

# 🚀 Use Cases

ระบบนี้สามารถใช้ได้กับ:

- ระบบเข้าออกอาคาร
- ระบบลงเวลา
- biometric login
- access control
- security checkpoint

---

# 📜 License

Private / Internal System
Not for redistribution
