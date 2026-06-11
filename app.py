from flask import Flask, render_template, request, redirect, flash
from datetime import datetime
import os
import requests
import gspread
import json  # เพิ่มระบบอ่านข้อความกุญแจดิจิทัล
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)
app.secret_key = "super_secret_key_for_flash_messages"

# 🔑 ใส่รหัสจาก Telegram ของคุณตรงนี้ (กรุณาใส่รหัสเดิมของคุณลงไปแทนที่ข้อความนี้นะครับ)
TELEGRAM_TOKEN = '8948799554:AAHEaRX6UN0Mibc34Hn9PDhZ9A_s4zupvjI'
TELEGRAM_CHAT_ID = '8638315134'
GOOGLE_JSON_KEY = 'google_key.json' 
SPREADSHEET_NAME = 'ระบบลงเวลาพนักงาน'

# 🗂️ รายชื่อพนักงานในระบบของคุณ
EMPLOYEE_DATA = {
    "000001": {"name": "อั้ม", "branch": "สำนักงานใหญ่"},
    "000002": {"name": "บี", "branch": "สำนักงานใหญ่"},
    "000003": {"name": "ซี", "branch": "สำนักงานใหญ่"},
    "000004": {"name": "แม่บ้าน", "branch": "สำนักงานใหญ่"}
}

def append_to_google_sheet(row_data):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # 🛡️ ส่วนที่แก้ไข: เช็คว่าถ้าอยู่บน Render ให้ดึงกุญแจจาก Environment ถ้าอยู่ในคอมให้ดึงจากไฟล์
        google_key_env = os.environ.get('GOOGLE_JSON_KEY')
        
        if google_key_env:
            # ใช้กุญแจจากหน้าเว็บ Render
            key_data = json.loads(google_key_env)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(key_data, scope)
        else:
            # ใช้กุญแจจากไฟล์ในคอมพิวเตอร์ของคุณ (ตามที่คุณกดรันแล้วผ่านปกติ)
            creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON_KEY, scope)
            
        client = gspread.authorize(creds)
        sheet = client.open(SPREADSHEET_NAME).sheet1
        sheet.append_row(row_data)
    except Exception as e:
        print("บันทึกลง Google Sheets ไม่สำเร็จ:", e)

def send_telegram_notify(message, image_path=None):
    try:
        if image_path and os.path.exists(image_path):
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            files = {'photo': open(image_path, 'rb')}
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': message}
            requests.post(url, files=files, data=data)
        else:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
            requests.post(url, data=data)
    except Exception as e:
        print("ส่ง Telegram ไม่สำเร็จ:", e)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/clock', methods=['POST'])
def clock():
    emp_id = request.form.get('emp_id')
    action = request.form.get('action')
    current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    display_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    photo = request.files.get('photo')
    
    if emp_id and photo:
        if emp_id not in EMPLOYEE_DATA:
            flash(f"❌ รหัสพนักงาน [{emp_id}] ไม่ถูกต้อง! กรุณาตรวจสอบและลองใหม่อีกครั้ง", "danger")
            return redirect('/')
            
        emp_name = EMPLOYEE_DATA[emp_id]["name"]
        emp_branch = EMPLOYEE_DATA[emp_id]["branch"]
            
        UPLOAD_FOLDER = 'static/uploads'
        if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
        
        file_extension = os.path.splitext(photo.filename)[1]
        filename = f"{emp_id}_{action}_{current_time}{file_extension}"
        image_path = os.path.join(UPLOAD_FOLDER, filename)
        photo.save(image_path)
        
        row_data = [emp_id, emp_name, emp_branch, action, display_time, filename]
        append_to_google_sheet(row_data)
        
        telegram_message = f"⏱️ มีพนักงานลงเวลา\n📌 รหัสพนักงาน: {emp_id}\n👤 ชื่อ: {emp_name}\n🏢 สาขา: {emp_branch}\n🔄 ทำการ: {action}\n⏰ เวลา: {display_time}"
        send_telegram_notify(telegram_message, image_path)
        
        flash(f"🎉 บันทึก [{action}] สำเร็จ!\n👤 คุณ: {emp_name}\n⏰ เวลา: {display_time}", "success")
            
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
