# PythonAnywhere Setup Instructions

## خطوات رفع البوت على PythonAnywhere:

### 1. إنشاء حساب
- روح https://www.pythonanywhere.com
- اضغط "Start running Python online for free!"
- سجل حساب مجاني (3 شهور)

### 2. رفع الملفات
- اضغط "Files" في لوحة التحكم
- ارفع هذي الملفات:
  - telegram_sniper.py
  - flask_app.py
  - requirements.txt
  - templates/auth.html

### 3. تثبيت المكتبات
- اضغط "Consoles" → "Bash"
- اكتب: `pip3.10 install --user -r requirements.txt`

### 4. إعداد Web App
- اضغط "Web" في لوحة التحكم  
- "Add a new web app"
- اختر "Flask"
- Source code: `/home/yourusername/mysite/flask_app.py`
- Python version: 3.10

### 5. Environment Variables
- في Web tab
- اضغط "Environment variables"
- أضف:
  - `BOT_TOKEN`: (token البوت من BotFather)
  - `ADMIN_ID`: 8018256893
  - `PYTHONANYWHERE_DOMAIN`: yourusername.pythonanywhere.com

### 6. تشغيل البوت
- Consoles → Python3.10
- `exec(open('telegram_sniper.py').read())`

## النتيجة:
- Web App: https://yourusername.pythonanywhere.com
- أي شخص في العالم يقدر يوصل له
- البوت يشتغل 24/7

## ملاحظات:
- Free account: 100 seconds/day CPU time
- استخدم Always-On Tasks للبوت ($5/month)
- أو restart البوت كل يوم يدوياً
