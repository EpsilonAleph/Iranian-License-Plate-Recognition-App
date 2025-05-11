import cv2
import time
from ultralytics import YOLO
from hezar.models import Model
import pyodbc
import customtkinter as ctk
import jdatetime
import arabic_reshaper
from bidi.algorithm import get_display
from tkinter import simpledialog

tarikhRAW = jdatetime.datetime.now()
tarikh = str(tarikhRAW.strftime("%Y-%m-%d %H:%M:%S"))

def to_rtl(text: str) -> str:
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

# ==== CONFIG & MODELS ====
MODEL_PATH = "D:/Projects/Python/License_detection_mechanicshop/persian-ALPR-main/lp_detector.pt"
lp_detector = YOLO(MODEL_PATH)
lp_ocr      = Model.load("hezarai/crnn-fa-64x256-license-plate-recognition")

# ==== DATABASE SETUP ====
conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=localhost;'
    'DATABASE=MechanicShopDB;'
    'Trusted_Connection=yes;'
)
cursor = conn.cursor()

cursor.execute("""
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='customers' AND xtype='U')
CREATE TABLE customers (
    id         INT IDENTITY(1,1) PRIMARY KEY,
    name       NVARCHAR(128),
    phone      NVARCHAR(32),
    plate      NVARCHAR(32),
    car_model  NVARCHAR(32),
    km         INT,
    created_at VARCHAR(50)
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
    date         VARCHAR(50)
)
""")
conn.commit()

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

class MechanicShopApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("سامانه مدیریت سرویس خودرو 🚗")
        self.geometry("1100x1000")
        self.configure(bg="#F0F5F9")

        # Service intervals (km only now)
        self.service_intervals = {
            "روغن موتور": {"km": 5000},
            "روغن ترمز": {"km": 20000},
            "روغن گیربکس": {"km": 40000},
            "لنت ترمز": {"km": 30000},
            "فیلتر روغن": {"km": 5000},
            "فیلتر هوا": {"km": 10000},
            "فیلتر کابین": {"km": 15000},
            "فیلتر بنزین": {"km": 20000},
            "ضد یخ": {"km": 15000},
            "شمع موتور": {"km": 20000},
        }

        header = ctk.CTkFrame(self, fg_color="#0000CD", height=90, corner_radius=0)
        header.pack(fill="x")
        header_label = ctk.CTkLabel(
            header,
            text="📋 سامانه مدیریت سرویس خودرو",
            font=("B Nazanin", 34, "bold"),
            text_color="white"
        )
        header_label.pack(pady=20)

        sf = ctk.CTkScrollableFrame(
            self,
            corner_radius=25,
            fg_color="#808080",
            width=1100,
            height=1000,
            border_width=2,
            border_color="#0000CD"
        )
        sf.pack(padx=20, pady=20, fill="both", expand=False)

        main_container = ctk.CTkFrame(
            sf,
            fg_color="transparent"
        )
        main_container.pack(fill="both", expand=False, padx=10)

        right_frame = ctk.CTkFrame(
            main_container,
            fg_color="#F8F9FA",
            corner_radius=15,
            border_width=1,
            border_color="#E5E5E5"
        )
        right_frame.pack(side="right", padx=(0, 20), fill="both", expand=False)

        service_label = ctk.CTkLabel(
            right_frame,
            text="سرویس‌های مورد نظر:",
            font=("B Nazanin", 20, "bold"),
            text_color="#1A374D"
        )
        service_label.pack(pady=15)

        self.services = {}
        names = list(self.service_intervals.keys())
        svc_grid = ctk.CTkFrame(right_frame, fg_color="transparent")
        svc_grid.pack(pady=10)
        
        for idx, name in enumerate(names):
            row = idx // 2
            col = idx % 2
            cb = ctk.CTkCheckBox(
                svc_grid,
                text=name,
                font=("B Nazanin", 14),
                checkbox_height=20,
                checkbox_width=20,
                corner_radius=4
            )
            cb.grid(row=row, column=col, padx=20, pady=10)
            self.services[name] = cb

        left_frame = ctk.CTkFrame(
            main_container,
            fg_color="#F8F9FA",
            corner_radius=15,
            border_width=1,
            border_color="#E5E5E5"
        )
        left_frame.pack(side="left", fill="both", expand=False)

        customer_label = ctk.CTkLabel(
            left_frame,
            text="اطلاعات مشتری",
            font=("B Nazanin", 24, "bold"),
            text_color="#1A374D"
        )
        customer_label.pack(pady=15)

        info_frame = ctk.CTkFrame(
            left_frame,
            fg_color="transparent",
        )
        info_frame.pack(fill="x", padx=15, pady=10)

        labels = ["نام مشتری", "شماره موبایل", "شماره پلاک", "کیلومتر فعلی", "مدل ماشین"]
        self.entries = []
        for i, text in enumerate(labels):
            entry = ctk.CTkEntry(
                info_frame,
                width=200,
                height=35,
                font=("B Nazanin", 14),
                justify="right",
                border_width=1,
                corner_radius=8
            )
            entry.grid(row=i, column=1, padx=15, pady=12)
            self.entries.append(entry)
            
            label = ctk.CTkLabel(
                info_frame,
                text=f"{text} :",
                font=("B Nazanin", 16),
                anchor="e"
            )
            label.grid(row=i, column=0, sticky="e", padx=15, pady=12)

        self.scan_btn = ctk.CTkButton(
            left_frame,
            text="📸 اسکن پلاک (۶ ثانیه)",
            font=("B Nazanin", 16),
            fg_color="#4682B4",
            text_color="white",
            hover_color="#FF5252",
            height=40,
            width=200,
            corner_radius=10,
            command=self.scan_plate
        )
        self.scan_btn.pack(pady=15)

        center_frame = ctk.CTkFrame(
            main_container,
            fg_color="#F8F9FA",
            corner_radius=15,
            border_width=1,
            border_color="#E5E5E5"
        )
        center_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)

        self.info_box = ctk.CTkTextbox(
            center_frame,
            height=200,
            width=100,
            font=("B Nazanin", 14),
            corner_radius=10,
            border_width=2,
            border_color="#E5E5E5"
        )
        self.info_box.pack(padx=10, pady=10, fill="both", expand=True)
        self.info_box.insert("0.0", "هنوز اطلاعاتی وارد نشده است.\n")

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

        btnf = ctk.CTkFrame(sf, fg_color="transparent")
        btnf.pack(pady=15, padx=10)

        button_params = [
            ("➕ ثبت مشتری", "#4CAF50", "#45A049", self.add_customer),
            ("✅ ثبت سرویس", "#2F4F4F", "#1976D2", self.register_service),
            ("📋 سوابق سرویس", "#B22222", "#7B1FA2", self.show_service_history_with_due)
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
        self.info_box.insert("0.0", "📸 شروع اسکن پلاک برای ثانیه...\n")
        cap = cv2.VideoCapture(0)
        start = time.time()
        plate_text = None

        while time.time() - start < 5:
            ret, frame = cap.read()
            if not ret:
                break
            res = lp_detector(frame, conf=0.4)[0]
            for box in res.boxes.data.tolist():
                x1, y1, x2, y2, _, _ = map(int, box[:6])
                crop = frame[y1:y2, x1:x2]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                txt = lp_ocr.predict(crop)[0]['text'].strip()
                if txt:
                    plate_text = txt
                    print(plate_text)

            cv2.imshow("Scan Plate", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

        if not plate_text:
            self.info_box.insert("0.0", "❌ پلاکی یافت نشد.\n")
            return

        # Query database for the detected plate
        cursor.execute("SELECT name, phone, km, car_model FROM customers WHERE plate=?", plate_text)
        customer = cursor.fetchone()

        if customer:
            name, phone, km, car_model = customer
            self.info_box.insert("0.0", f"✅ پلاک {to_rtl(plate_text)} پیدا شد! اطلاعات مشتری بارگذاری شد.\n")
        
            # Populate the fields
            self.entries[0].delete(0, "end")  # Name field
            self.entries[0].insert(0, name)

            self.entries[1].delete(0, "end")  # Phone field
            self.entries[1].insert(0, phone)

            self.entries[3].delete(0, "end")  # KM field
            self.entries[3].insert(0, str(km))

            self.entries[4].delete(0, "end")  # Car model field
            self.entries[4].insert(0, car_model)

        else:
            # If not found, just insert the plate number into the plate field
            ent = self.entries[2]
            ent.delete(0, "end")
            ent.insert(0, to_rtl(plate_text))
            self.info_box.insert("0.0", f"✅ پلاک {to_rtl(plate_text)} شناسایی شد.\n")


    def add_customer(self):
        name, phone, plate, km, car_model = [e.get().strip() for e in self.entries]
        if not all((name, phone, plate, km, car_model)):
            self.info_box.insert("0.0", "❌ لطفاً همه فیلدها را پر کنید.\n")
            return
        now = tarikh
        cursor.execute("""
            INSERT INTO customers (name, phone, plate, km, car_model, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, name, phone, plate, int(km), now)
        conn.commit()
        self.info_box.insert("0.0", f"✅ مشتری {name} ثبت شد.\n")

    def register_service(self):
        selected = [n for n, cb in self.services.items() if cb.get()==1]
        _, _, plate, km, _ = [e.get().strip() for e in self.entries]
        if not selected:
            self.info_box.insert("0.0", "❌ حداقل یک سرویس را انتخاب کنید.\n")
            return

        cursor.execute("SELECT id FROM customers WHERE plate=? ORDER BY id DESC", plate)
        row = cursor.fetchone()
        if not row:
            self.info_box.insert("0.0", "❌ مشتری یافت نشد! ابتدا ثبتش کنید.\n")
            return
        cid = row[0]
        now = tarikh
        desc = self.desc_entry.get().strip()
        for svc in selected:
            cursor.execute("""
                INSERT INTO services (customer_id, service_name, km, description, date)
                VALUES (?, ?, ?, ?, ?)
            """, cid, svc, int(km), desc, now)
        conn.commit()
        self.info_box.insert("0.0", f"✅ سرویس برای پلاک {plate} ثبت شد.\n")

    def show_service_history_with_due(self):
        # Step 1: Get plate
        plate = self.entries[2].get().strip()
        if not plate:
            self.info_box.insert("0.0", "❌ لطفاً شماره پلاک را وارد کنید.\n")
            return

        # Step 2: Find customer
        cursor.execute("SELECT id FROM customers WHERE plate=? ORDER BY id DESC", plate)
        row = cursor.fetchone()
        if not row:
            self.info_box.insert("0.0", "❌ سابقه‌ای برای این پلاک یافت نشد.\n")
            return
        cid = row[0]

        # Step 3: Ask for new odometer
        new_km_str = simpledialog.askstring("کیلومتر فعلی", "عدد کیلومتر فعلی را وارد کنید:")
        if new_km_str is None:
            self.info_box.insert("0.0", "❌ کیلومتر فعلی وارد نشد.\n")
            return
        try:
            new_km = int(new_km_str)
        except:
            self.info_box.insert("0.0", "❌ لطفاً کیلومتر را به عدد صحیح وارد کنید.\n")
            return

        # Step 4: Fetch service history
        cursor.execute("""
            SELECT service_name, km, date, description
            FROM services WHERE customer_id=?
            ORDER BY date DESC
        """, cid)
        rows = cursor.fetchall()
        if not rows:
            self.info_box.insert("0.0", "❌ هیچ سرویسی برای این خودرو ثبت نشده است.\n")
            return

        # Step 5: Find last odometer and show history
        history_lines = []
        last_service_km = {}
        last_service_date = {}
        for svc, km, dt, desc in rows:
            history_lines.append(f"{dt} — {svc} — {km} کیلومتر\nتوضیح: {desc}\n")
            # we want the service with the largest (latest) km for each service_name
            if svc not in last_service_km or km > last_service_km[svc]:
                last_service_km[svc] = km
                last_service_date[svc] = dt

        # Step 6: Calculate due services
        due_lines = []
        for svc, interval in self.service_intervals.items():
            last_km = last_service_km.get(svc, None)
            if last_km is None:
                due_lines.append(f"🔴 {svc}: هرگز انجام نشده (اولین سرویس)")
            else:
                passed_km = new_km - last_km
                if passed_km >= interval["km"]:
                    due_lines.append(f"🔴 {svc}: موعد تعویض! از آخرین سرویس {passed_km} کیلومتر گذشته است.")
                else:
                    due_lines.append(f"🟢 {svc}: {interval['km'] - passed_km} کیلومتر تا موعد بعدی باقی مانده است.")

        # Step 7: Show
        text = f"📋 سوابق سرویس برای {plate}:\n" + "".join(history_lines) + "\n"
        text += "🛠️ سرویس‌هایی که موعدشان رسیده یا نزدیک است:\n" + "\n".join(due_lines)
        self.info_box.insert("0.0", text + "\n\n")

if __name__ == "__main__":
    app = MechanicShopApp()
    app.mainloop()