from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import google.generativeai as genai
import PIL.Image
import io
import sqlite3
from datetime import datetime
import os

# استدعاء المفتاح بشكل آمن
api_key = os.environ.get("GOOGLE_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

app = FastAPI(title="مساعد المهندس الذكي API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_db():
    conn = sqlite3.connect("faults_history.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faults (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_time TEXT,
            report TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- مكتبة الكتالوجات (تقدر تعدل اللينكات دي براحتك بعدين) ---
CATALOGS_LINKS = {
    "daikin": "https://drive.google.com/file/d/daikin_example_link/view",
    "دايكن": "https://drive.google.com/file/d/daikin_example_link/view",
    "carrier": "https://drive.google.com/file/d/carrier_example_link/view",
    "كارير": "https://drive.google.com/file/d/carrier_example_link/view",
    "york": "https://drive.google.com/file/d/york_example_link/view",
    "يورك": "https://drive.google.com/file/d/york_example_link/view",
}

@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")

@app.post("/analyze-error/")
async def analyze_error(file: UploadFile = File(...)):
    try:
        image_data = await file.read()
        img = PIL.Image.open(io.BytesIO(image_data))

        # هندسة الأوامر (Prompt Engineering) مخصصة لمجالك
        prompt = """
        أنت مهندس صيانة تكييف مركزي وأنظمة تبريد (Chillers & Cooling Towers) خبير.
        قم بتحليل هذه الصورة واستخرج كود العطل أو بيانات اللوحة.
        1. اذكر اسم الماركة (مثل Daikin, Carrier إلخ) بوضوح في بداية الرد.
        2. اشرح المشكلة المحتملة باختصار شديد.
        3. اكتب 3 خطوات فحص فنية من كتالوج الصيانة الرسمي (Troubleshooting).
        الرد يكون باللغة العربية وموجه لمهندس موقع محترف.
        """
        response = model.generate_content([prompt, img])
        report_text = response.text

        # البحث عن الماركة لإرفاق الكتالوج
        matched_catalog = ""
        for brand, link in CATALOGS_LINKS.items():
            if brand in report_text.lower():
                matched_catalog = link
                break

        # حفظ في السجل
        conn = sqlite3.connect("faults_history.db")
        cursor = conn.cursor()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO faults (date_time, report) VALUES (?, ?)", (current_time, report_text))
        conn.commit()
        conn.close()

        # إرسال التقرير + رابط الكتالوج (لو موجود) للواجهة
        return {"status": "success", "report": report_text, "catalog_url": matched_catalog}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/history/")
async def get_history():
    try:
        conn = sqlite3.connect("faults_history.db")
        cursor = conn.cursor()
        cursor.execute("SELECT date_time, report FROM faults ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()
        
        history_list = [{"date": row[0], "report": row[1]} for row in rows]
        return {"status": "success", "history": history_list}
    except Exception as e:
        return {"status": "error", "message": str(e)}
