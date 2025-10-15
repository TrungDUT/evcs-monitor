import requests
from bs4 import BeautifulSoup
import re
import json
import time
from datetime import datetime
import openpyxl
import os

# ==== Cấu hình ====
URL = "https://evcs.vn/tram-sac-vinfast-cong-ty-tnhh-ha-tang-tram-sac-xanh-45-doan-khue-p-hoa-cuong-da-nang-c.dna0204.html"
FOLDER = "./logs"  # Lưu cùng thư mục trên cloud
DATA_FILE = os.path.join(FOLDER, "prev_data.json")
LOG_XLSX = os.path.join(FOLDER, "evcs_log.xlsx")
LOG_TXT = os.path.join(FOLDER, "evcs_log.txt")

# ==== Hàm tạo thư mục ====
os.makedirs(FOLDER, exist_ok=True)

def parse_data(html):
    """Trích xuất dữ liệu trạm sạc từ HTML"""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    def find(pattern):
        m = re.search(pattern, text)
        return {"free": int(m.group(1)), "total": int(m.group(2))} if m else None

    data = {
        "150kW": find(r"✧\s*150kW\s*trống\s*(\d+)\s*/\s*(\d+)\s*cổng"),
        "120kW": find(r"✧\s*120kW\s*trống\s*(\d+)\s*/\s*(\d+)\s*cổng"),
        "60kW": find(r"✧\s*60kW\s*trống\s*(\d+)\s*/\s*(\d+)\s*cổng"),
        "3.5kW": find(r"✧\s*3\.5kW\s*trống\s*(\d+)\s*/\s*(\d+)\s*cổng"),
    }

    for key, val in data.items():
        if val:
            val["charging"] = val["total"] - val["free"]
    return data


def load_prev():
    if not os.path.exists(DATA_FILE):
        return None
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_current(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def init_excel():
    if not os.path.exists(LOG_XLSX):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Logs"
        ws.append(["Thời gian", "Loại sạc", "Cổng trống", "Tổng cổng", "Xe đang sạc"])
        wb.save(LOG_XLSX)


def log_change(timestamp, key, cur):
    """Ghi thay đổi vào Excel + TXT"""
    init_excel()

    wb = openpyxl.load_workbook(LOG_XLSX)
    ws = wb.active
    ws.append([timestamp, key, cur["free"], cur["total"], cur["charging"]])
    wb.save(LOG_XLSX)

    with open(LOG_TXT, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {key}: Trống {cur['free']}/{cur['total']} | Đang sạc {cur['charging']} xe\n")


def check_changes():
    """Kiểm tra web và ghi log nếu có thay đổi"""
    resp = requests.get(URL, timeout=15)
    data = parse_data(resp.text)
    prev = load_prev()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n[{timestamp}] Dữ liệu hiện tại: {data}")

    if not prev:
        print("🔰 Lần đầu chạy, lưu dữ liệu gốc.")
        for key, val in data.items():
            if val:
                log_change(timestamp, key, val)
        save_current(data)
        return

    changed = False
    for key, cur in data.items():
        if not cur:
            continue
        old = prev.get(key)
        if not old or cur != old:
            changed = True
            print(f"⚡ Thay đổi phát hiện tại {key}: {old} ➜ {cur}")
            log_change(timestamp, key, cur)

    if changed:
        save_current(data)
        print("✅ Đã lưu thay đổi.")
    else:
        print("⏸ Không có thay đổi, không lưu log.")


if __name__ == "__main__":
    print(f"🚀 Bắt đầu theo dõi trạm sạc tại: {URL}")
    print(f"📂 Log lưu ở: {FOLDER}")

    while True:
        try:
            check_changes()
        except Exception as e:
            print("❌ Lỗi:", e)
        time.sleep(60)
