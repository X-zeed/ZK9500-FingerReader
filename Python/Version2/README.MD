# 🖐 Fingerprint Access Control System

ระบบควบคุมการเข้าออกด้วยลายนิ้วมือ สร้างด้วย **PyQt5 + PostgreSQL**

พร้อม UI แบบ Clean Light, Animation Scanner Ring, และ Custom Dialog System

---

## 🛠 Tech Stack

| Layer    | Technology                      |
| -------- | ------------------------------- |
| GUI      | PyQt5                           |
| Database | PostgreSQL + psycopg2           |
| Scanner  | External Fingerprint SDK (.exe) |
| Config   | python-dotenv                   |

---

## 📁 Project Structure

```
project/
├── Application/
│   ├── save.exe        # จับ fingerprint
│   ├── verify.exe      # scan fingerprint
│   └── compare.exe     # เปรียบเทียบ template
│
├── fingerprint_app.py  # main GUI
├── custom_dialog.py    # custom popup dialogs
├── .env                # database config
└── README.md
```

---

## ⚙️ Installation

```bash
python -m pip install psycopg2-binary python-dotenv PyQt5
```

---

## 🔐 Environment Config

สร้างไฟล์ `.env` ที่ root ของ project:

```env
DB_HOST=localhost
DB_NAME=fingerprint_db
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_PORT=5432
```

> ⚠️ อย่า commit ไฟล์ `.env` ขึ้น Git

เพิ่ม `.gitignore`:

```
.env
```

---

## 🗄 Database Schema

```sql
CREATE TABLE fingerprints (
    id            SERIAL PRIMARY KEY,
    user_id       TEXT,
    template      BYTEA,
    template_size INT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## ▶️ Run

```bash
python fingerprint_app.py
```

---

## 📋 Pages

| Page         | หน้าที่                     |
| ------------ | --------------------------- |
| **REGISTER** | สแกนและบันทึกลายนิ้วมือใหม่ |
| **VERIFY**   | ตรวจสอบตัวตนจากลายนิ้วมือ   |
| **RECORDS**  | ดู / ค้นหาข้อมูลในฐานข้อมูล |

---

## 🔄 Workflow

### Register

```
save.exe  →  extract Base64 template  →  บันทึกลง PostgreSQL
```

1. กด **CAPTURE**
2. วางนิ้วบน scanner
3. กรอกชื่อหรือรหัสพนักงาน
4. กด **SAVE TO DATABASE**

---

### Verify

```
verify.exe  →  scan  →  compare.exe (ทีละ record)  →  score > 60 → GRANTED
```

1. กด **VERIFY**
2. วางนิ้วบน scanner
3. ระบบโหลด template จาก DB แล้วเปรียบเทียบ
4. แสดงผล **ACCESS GRANTED** หรือ **ACCESS DENIED**

---

### Records

- โหลดข้อมูลจาก DB อัตโนมัติ
- ค้นหาด้วย user ID หรือชื่อ
- Refresh ด้วยปุ่ม ↺

---

## 🎨 UI Features

- Animated Scanner Ring พร้อม ripple effect
- Custom Dialog System (แทน QMessageBox)
- Status color system (Blue / Green / Red / Orange)
- Adaptive scaling layout
- Live clock และ DB status indicator
- Access log panel แบบ real-time

---

## 🧩 Architecture

### Background Workers (QThread)

| Worker         | หน้าที่                           |
| -------------- | --------------------------------- |
| `ScanWorker`   | เรียก save.exe และ parse template |
| `VerifyWorker` | เรียก verify.exe และ compare DB   |

### Core Functions

```python
get_connection()     # เชื่อมต่อ PostgreSQL
extract_template()   # parse Base64 template จาก stdout
is_base64()          # validate template string
```

### Reusable Widgets

```
ScannerRing   PanelCard   NavButton
StatusBar     IconWidget  CustomDialog
```

---

## ⚡ Performance Notes

เวอร์ชันปัจจุบัน compare แบบ sequential (ทีละ record)
หากต้องการ optimize:

- Cache templates ใน RAM
- ใช้ `multiprocessing` สำหรับ compare
- ใช้ async subprocess
- Connection pooling

---

## 🛠 Troubleshooting

### Scanner ไม่ทำงาน

- ตรวจสอบ driver ของ fingerprint reader
- ตรวจสอบ path `Application/*.exe`
- ตรวจสอบสิทธิ์การรัน `.exe`

### Database Error

- ตรวจสอบว่า PostgreSQL กำลัง run อยู่
- ตรวจสอบค่าใน `.env`
- ตรวจสอบ port และ firewall

### Verify แล้วไม่ match

- ตรวจสอบ template ใน DB ว่าถูก format
- ตรวจสอบว่า `compare.exe` คืน score ถูกต้อง
- ลอง ปรับ threshold (ปัจจุบัน `> 60`)

---

## 🔒 Security Notes

- เก็บ fingerprint template เป็น `BYTEA` ไม่ใช่ภาพ
- ไม่เก็บ raw scan ลง disk
- Credential อยู่ใน `.env` ไม่ได้ hardcode

---

## 📜 License

Private / Internal Use Only — Not for redistribution

