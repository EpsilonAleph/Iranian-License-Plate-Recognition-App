import cv2
import time
from ultralytics import YOLO
from hezar.models import Model
import pyodbc
from datetime import datetime
import customtkinter as ctk
from tkinter import font, RIGHT, E


# ==== CONFIG & MODELS ====
MODEL_PATH = "LPR/lp_detector.pt"
lp_detector = YOLO(MODEL_PATH)
lp_ocr      = Model.load("hezarai/crnn-fa-64x256-license-plate-recognition")

# ==== DATABASE SETUP ====
conn = pyodbc.connect(
    # Change these to match your DB / if necessary
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=localhost;'
    'DATABASE=MechanicShopDB;'
    'Trusted_Connection=yes;'
)
cursor = conn.cursor()

# Create customers & services tables
cursor.execute("""
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='customers' AND xtype='U')
CREATE TABLE customers (
    id         INT IDENTITY(1,1) PRIMARY KEY,
    name       NVARCHAR(128),
    phone      NVARCHAR(32),
    plate      NVARCHAR(32),
    km         INT,
    created_at DATETIME
)
""")
cursor.execute("""
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='services' AND xtype='U')
CREATE TABLE services (
    id           INT IDENTITY(1,1) PRIMARY KEY,
    customer_id  INT,
    service_name NVARCHAR(64),
    km           INT,
    description  NVARCHAR(256),
    date         DATETIME
)
""")
conn.commit()


# GUI
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

class MechanicShopApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Main window
        self.title("سامانه مدیریت سرویس خودرو 🚗")
        self.geometry("1200x1200")    # window size
        self.configure(bg="#F0F5F9")  # background color

        # Service intervals
        self.service_intervals = {
            "روغن موتور": {"km": 5000, "days": 180},
            "روغن ترمز": {"km": 20000, "days": 365},
            "روغن گیربکس": {"km": 40000, "days": 730},
            "لنت ترمز": {"km": 30000, "days": 540},
            "فیلتر روغن": {"km": 5000, "days": 180},
            "فیلتر هوا": {"km": 10000, "days": 365},
            "فیلتر کابین": {"km": 15000, "days": 365},
            "فیلتر بنزین": {"km": 20000, "days": 365},
            "ضد یخ": {"km": 15000, "days": 365},
            "شمع موتور": {"km": 20000, "days": 365},
        }

        # Header
        header = ctk.CTkFrame(self, fg_color="#1A374D", height=90, corner_radius=0)
        header.pack(fill="x")
        header_label = ctk.CTkLabel(
            header,
            text="📋 سامانه مدیریت سرویس خودرو",
            font=("B Nazanin", 34, "bold"),
            text_color="white"
        )
        header_label.pack(pady=20)

        # Scrollable area
        sf = ctk.CTkScrollableFrame(
            self,
            corner_radius=20,
            fg_color="#FFFFFF",
            width=1100,
            height=1000,
            border_width=2,
            border_color="#E5E5E5"
        )
        sf.pack(padx=20, pady=20, fill="both", expand=True)

        # Customer Form
        customer_label = ctk.CTkLabel(
            sf,
            text="اطلاعات مشتری",
            font=("B Nazanin", 24, "bold"),
            text_color="#1A374D"
        )
        customer_label.pack(pady=20)

        info_frame = ctk.CTkFrame(
            sf,
            fg_color="#F8F9FA",
            corner_radius=15,
            border_width=1,
            border_color="#E5E5E5"
        )
        info_frame.pack(fill="x", padx=15, pady=10)

        # Form layout
        labels = ["نام مشتری", "شماره موبایل", "شماره پلاک", "کیلومتر فعلی"]
        self.entries = []
        for i, text in enumerate(labels):
            label = ctk.CTkLabel(
                info_frame,
                text=f"{text} :",
                font=("B Nazanin", 16),
                anchor="e"
            )
            label.grid(row=i, column=1, sticky="e", padx=15, pady=12)
            
            entry = ctk.CTkEntry(
                info_frame,
                width=300,
                height=35,
                font=("B Nazanin", 14),
                justify="right",
                border_width=1,
                corner_radius=8
            )
            entry.grid(row=i, column=0, padx=15, pady=12)
            self.entries.append(entry)

        # Scan Plate button
        self.scan_btn = ctk.CTkButton(
            sf,
            text="📸 اسکن پلاک (۶ ثانیه)",
            font=("B Nazanin", 16),
            fg_color="#FF6B6B",
            text_color="white",
            hover_color="#FF5252",
            height=40,
            width=200,
            corner_radius=10,
            command=self.scan_plate
        )
        self.scan_btn.pack(pady=15)

        # Info box
        self.info_box = ctk.CTkTextbox(
            sf,
            height=150,
            width=1000,
            font=("B Nazanin", 14),
            corner_radius=10,
            border_width=1,
            border_color="#E5E5E5"
        )
        self.info_box.pack(pady=15)
        self.info_box.insert("0.0", "هنوز اطلاعاتی وارد نشده است.\n")

        # Service checkboxes
        service_label = ctk.CTkLabel(
            sf,
            text="سرویس‌های مورد نظر:",
            font=("B Nazanin", 24, "bold"),
            text_color="#1A374D"
        )
        service_label.pack(pady=15)

        svc_frame = ctk.CTkFrame(
            sf,
            fg_color="#F8F9FA",
            corner_radius=15,
            border_width=1,
            border_color="#E5E5E5"
        )
        svc_frame.pack(pady=10)

        # Checkbox layout
        self.services = {}
        names = list(self.service_intervals.keys())
        for idx, name in enumerate(names):
            row = idx // 3
            col = idx % 3
            cb = ctk.CTkCheckBox(
                svc_frame,
                text=name,
                font=("B Nazanin", 14),
                checkbox_height=25,
                checkbox_width=25,
                corner_radius=5
            )
            cb.grid(row=row, column=col, padx=30, pady=15, sticky="w")
            self.services[name] = cb

        # Description section
        descf = ctk.CTkFrame(sf, fg_color="transparent")
        descf.pack(pady=15)
        
        desc_label = ctk.CTkLabel(
            descf,
            text="توضیحات:",
            font=("B Nazanin", 16)
        )
        desc_label.grid(row=0, column=0, padx=10, sticky="w")
        
        self.desc_entry = ctk.CTkEntry(
            descf,
            width=700,
            height=35,
            font=("B Nazanin", 14),
            justify="right",
            corner_radius=8
        )
        self.desc_entry.grid(row=0, column=1, padx=10)

        # Action buttons
        btnf = ctk.CTkFrame(sf, fg_color="transparent")
        btnf.pack(pady=25)

        button_params = [
            ("➕ ثبت مشتری", "#4CAF50", "#45A049", self.add_customer),
            ("✅ ثبت سرویس", "#2196F3", "#1976D2", self.register_service),
            ("📋 سوابق سرویس", "#9C27B0", "#7B1FA2", self.show_service_history)
        ]

        for i, (text, color, hover, command) in enumerate(button_params):
            ctk.CTkButton(
                btnf,
                text=text,
                font=("B Nazanin", 16, "bold"),
                fg_color=color,
                hover_color=hover,
                height=45,
                width=180,
                corner_radius=12,
                command=command
            ).grid(row=0, column=i, padx=20)

    def scan_plate(self):
        """Open camera for 6 seconds, detect plate + OCR, fill entry."""
        self.info_box.insert("0.0", "📸 شروع اسکن پلاک برای ۶ ثانیه...\n")
        cap = cv2.VideoCapture(0)
        start = time.time()
        plate_text = None

        while time.time() - start < 6:
            ret, frame = cap.read()
            if not ret:
                break
            cv2.imshow("Scan Plate", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            # Try detection in each frame
            res = lp_detector(frame, conf=0.4)[0]
            for box in res.boxes.data.tolist():
                x1,y1,x2,y2,_,_ = map(int, box[:6])
                crop = frame[y1:y2, x1:x2]
                txt = lp_ocr.predict(crop)[0]['text'].strip()
                if txt:
                    plate_text = txt
                    break
            if plate_text:
                break

        cap.release()
        cv2.destroyAllWindows()

        if not plate_text:
            self.info_box.insert("0.0", "❌ پلاکی یافت نشد.\n")
            return

        # Fill into Plate entry
        ent = self.entries[2]
        ent.delete(0, "end")
        ent.insert(0, plate_text)
        self.info_box.insert("0.0", f"✅ پلاک {plate_text} شناسایی شد.\n")

    def add_customer(self):
        name, phone, plate, km = [e.get().strip() for e in self.entries]
        if not all((name, phone, plate, km)):
            self.info_box.insert("0.0", "❌ لطفاً همه فیلدها را پر کنید.\n")
            return
        now = datetime.now()
        cursor.execute("""
            INSERT INTO customers (name, phone, plate, km, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, name, phone, plate, int(km), now)
        conn.commit()
        self.info_box.insert("0.0", f"✅ مشتری {name} ثبت شد.\n")

    def register_service(self):
        selected = [n for n,cb in self.services.items() if cb.get()==1]
        _, _, plate, km = [e.get().strip() for e in self.entries]
        if not selected:
            self.info_box.insert("0.0", "❌ حداقل یک سرویس را انتخاب کنید.\n")
            return

        # Find customer
        cursor.execute("SELECT id FROM customers WHERE plate=? ORDER BY id DESC", plate)
        row = cursor.fetchone()
        if not row:
            self.info_box.insert("0.0", "❌ مشتری یافت نشد! ابتدا ثبتش کنید.\n")
            return
        cid = row[0]
        now = datetime.now()
        desc = self.desc_entry.get().strip()
        for svc in selected:
            cursor.execute("""
                INSERT INTO services (customer_id, service_name, km, description, date)
                VALUES (?, ?, ?, ?, ?)
            """, cid, svc, int(km), desc, now)
        conn.commit()
        self.info_box.insert("0.0", f"✅ سرویس برای پلاک {plate} ثبت شد.\n")

    def show_service_history(self):
        plate = self.entries[2].get().strip()
        cursor.execute("SELECT id FROM customers WHERE plate=? ORDER BY id DESC", plate)
        row = cursor.fetchone()
        if not row:
            self.info_box.insert("0.0", "❌ سابقه‌ای برای این پلاک یافت نشد.\n")
            return
        cid = row[0]
        cursor.execute("""
            SELECT service_name, km, date, description
            FROM services WHERE customer_id=?
        """, cid)
        rows = cursor.fetchall()
        text = f"📋 سوابق سرویس برای {plate}:\n"
        for svc, km, dt, desc in rows:
            text += f"{dt:%Y-%m-%d} — {svc} — {km} km\nتوضیح: {desc}\n\n"
        self.info_box.insert("0.0", text)


if __name__ == "__main__":
    app = MechanicShopApp()
    app.mainloop()
