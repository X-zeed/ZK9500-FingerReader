# 🖐 Fingerprint Scanner System (Python + PostgreSQL)

ระบบสแกนลายนิ้วมือ → บันทึก → ตรวจสอบตัวตน
พัฒนาด้วย Python + PostgreSQL + External Fingerprint SDK (.exe)

---

## 📁 Project Structure

```
project/
│
├── Application/
│   ├── compare.exe
│   ├── save.exe
│   └── verify.exe
│
├── ConnectDB.py
├── save_fingerprint.py
├── verify_fingerprint.py
└── .env
```

---

## ⚙️ Installation

ติดตั้ง dependencies

```bash
pip install psycopg2-binary python-dotenv
```

---

## 🔐 Environment Config

สร้างไฟล์ `.env`

```
DB_HOST=localhost
DB_NAME=fingerprint_db
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_PORT=5432
```

> ⚠️ ห้าม upload `.env` ขึ้น Git

เพิ่ม `.gitignore`

```
.env
```

---

## 🧠 System Workflow

### ➤ Save Fingerprint

```
save.exe → Python → PostgreSQL
```

ขั้นตอน:

1. เรียก `Application/save.exe`
2. ดึง Base64 template
3. ตรวจสอบ format
4. บันทึกลง database

Run:

```bash
python save_fingerprint.py
```

---

### ➤ Verify Fingerprint

```
verify.exe → Python → compare.exe → DB match
```

ขั้นตอน:

1. รอ scan ลายนิ้วมือ
2. ดึง template
3. โหลด template จาก DB
4. compare ทีละ user
5. แสดง user ที่ match

Run:

```bash
python verify_fingerprint.py
```

หยุดโปรแกรม:

```
Ctrl + C
```

---

## 🗄 Database Schema

```sql
CREATE TABLE fingerprints (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    template BYTEA,
    template_size INT
);
```

---

## 🧩 ConnectDB.py

ไฟล์นี้ใช้รวม logic การเชื่อมต่อ database
ข้อดี:

- แก้ config จุดเดียว
- ปลอดภัยกว่า
- reuse ได้ทั้งโปรเจกต์

---

## 🚀 Features

- Real-time fingerprint scan loop
- Duplicate scan protection
- DB connection isolation
- Error-safe compare
- Modular architecture

---

## ⚡ Performance Notes

เวอร์ชันปัจจุบัน:

- compare ทีละ record
- โหลด DB ทุกครั้ง

ถ้าจะใช้ production แนะนำเพิ่ม:

- RAM cache template
- multiprocessing compare
- connection pool
- async subprocess

---

## 🛠 Troubleshooting

### Scan ไม่ติด

ตรวจสอบ

- driver scanner
- path exe
- permission

### DB connect error

ตรวจสอบ

- PostgreSQL run อยู่
- ค่าใน `.env`
- port

### compare.exe error

ดู debug output console

---

## 🧑‍💻 Use Cases

ระบบนี้สามารถนำไปใช้ต่อยอดเป็น

- ระบบเข้าออกอาคาร
- ระบบลงเวลา
- biometric authentication
- security gate
- attendance system

---

## 📜 License

Private / Internal Use
