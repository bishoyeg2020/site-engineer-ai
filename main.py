import os
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import google.generativeai as genai
import PIL.Image
import io
import sqlite3
from datetime import datetime

# 1. إعداد Gemini
# استدعاء المفتاح بشكل آمن من إعدادات السيرفر
api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

app = FastAPI(title="مساعد المهندس الموقع API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. إنشاء وتجهيز قاعدة البيانات (SQLite)
def init_db():
    conn = sqlite3.connect("faults_history.db")
    cursor = conn.cursor()
    # إنشاء جدول لحفظ الأعطال لو مش موجود
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faults (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_time TEXT,
            report TEXT
        )
    ''')
    conn.commit()
    conn.close()

# تشغيل دالة إنشاء قاعدة البيانات أول ما السيرفر يشتغل
init_db()

@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")

# 3. مسار تحليل العطل وحفظه في قاعدة البيانات
@app.post("/analyze-error/")
async def analyze_error(file: UploadFile = File(...)):
    try:
        image_data = await file.read()
        img = PIL.Image.open(io.BytesIO(image_data))

        prompt = """
        أنت مهندس صيانة تكييف مركزي وأنظمة تبريد خبير.
        قم بتحليل هذه الصورة المأخوذة من الموقع واستخرج كود العطل أو بيانات اللوحة.
        بناءً على خبرتك وأكواد ASHRAE، اكتب:
        1. المشكلة المحتملة باختصار.
        2. 3 خطوات سريعة للفحص يمكن للمهندس تنفيذها فوراً.
        3. متى يجب الرجوع لمقاول الصيانة.
        الرد يكون باللغة العربية وموجه لمهندس موقع.
        """
        response = model.generate_content([prompt, img])
        report_text = response.text

        # حفظ التقرير في قاعدة البيانات مع تاريخ ووقت اليوم
        conn = sqlite3.connect("faults_history.db")
        cursor = conn.cursor()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO faults (date_time, report) VALUES (?, ?)", (current_time, report_text))
        conn.commit()
        conn.close()

        return {"status": "success", "report": report_text}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 4. مسار جديد لاستدعاء سجل الأعطال السابقة
@app.get("/history/")
async def get_history():
    try:
        conn = sqlite3.connect("faults_history.db")
        cursor = conn.cursor()
        # هنجيب الأعطال مترتبة من الأحدث للأقدم
        cursor.execute("SELECT date_time, report FROM faults ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()
        
        # تحويل البيانات لشكل يقدر الموبايل يفهمه
        history_list = [{"date": row[0], "report": row[1]} for row in rows]
        return {"status": "success", "history": history_list}
    except Exception as e:
        return {"status": "error", "message": str(e)}
