from pyrogram import Client, filters
import requests
import json
import mysql.connector
from mysql.connector import Error

# إعدادات Pyrogram
API_ID = "20944746"  # استبدل بـ API ID الخاص بك
API_HASH = "d169162c1bcf092a6773e685c62c3894"  # استبدل بـ API Hash الخاص بك
BOT_TOKEN = "7343612422:AAEZ8mcBf3ek2gylGQ4h9HJ_-bymskAzKvE"  # استبدل بـ توكن البوت الخاص بك

# إعدادات قاعدة البيانات
DB_CONFIG = {
    "user": "db_94aznkc4cigy",
    "password": "5C82pUP0hiskqEQjXosYrjxA",
    "host": "up-de-fra1-mysql-1.db.run-on-seenode.com",
    "port": 11550,
    "database": "db_94aznkc4cigy"  # اسم قاعدة البيانات
}

# إعدادات API الخارجية
API_URL = "http://pass-gpt.nowtechai.com/api/v1/pass"
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# إنشاء جلسة البوت
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# دالة الاتصال بقاعدة البيانات
def connect_db():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as err:
        print(f"خطأ في الاتصال بقاعدة البيانات: {err}")
        return None

# دالة لحفظ المحادثات في قاعدة البيانات
def save_conversation_to_db(user_id, conversation):
    connection = connect_db()
    if connection:
        cursor = connection.cursor()
        try:
            query = "INSERT INTO conversations (user_id, conversation) VALUES (%s, %s)"
            cursor.execute(query, (user_id, json.dumps(conversation)))
            connection.commit()
            print(f"تم حفظ المحادثة للمستخدم {user_id}.")
        except Error as err:
            print(f"خطأ أثناء حفظ المحادثة: {err}")
        finally:
            cursor.close()
            connection.close()

# دالة لاسترجاع المحادثات من قاعدة البيانات
def get_conversation_from_db(user_id):
    connection = connect_db()
    if connection:
        cursor = connection.cursor()
        try:
            query = "SELECT conversation FROM conversations WHERE user_id = %s ORDER BY created_at DESC LIMIT 1"
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
            return []
        except Error as err:
            print(f"خطأ أثناء استرجاع المحادثة: {err}")
            return []
        finally:
            cursor.close()
            connection.close()

# دالة للتعامل مع API الخارجي
def send_message_to_api(conversation):
    data = {"contents": conversation}
    try:
        response = requests.post(API_URL, headers=HEADERS, data=json.dumps(data), stream=True)
        response.raise_for_status()
        reply = ""
        for line in response.iter_lines(decode_unicode=True):
            if line and line.startswith("data:"):
                content = line[5:].strip()
                try:
                    json_content = json.loads(content)
                    reply += json_content.get('content', '')
                except json.JSONDecodeError:
                    reply += content
        return reply if reply else "لم يتم الحصول على رد."
    except requests.exceptions.RequestException as e:
        return f"حدث خطأ أثناء التواصل مع API: {e}"

# وظيفة بدء البوت
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("مرحبًا! أرسل لي رسالة وسأرد عليك، وسأحتفظ بسياق المحادثة.")

# وظيفة التعامل مع الرسائل
@app.on_message(filters.text & ~filters.command("start"))
async def handle_message(client, message):
    user_id = message.from_user.id
    user_message = message.text

    # استرجاع المحادثة السابقة أو البدء بمحادثة جديدة
    user_conversation = get_conversation_from_db(user_id) or [
        {"role": "system", "content": "You are a helpful assistant."}
    ]

    # إضافة رسالة المستخدم
    user_conversation.append({"role": "user", "content": user_message})

    # إرسال الرسالة إلى API
    reply = send_message_to_api(user_conversation)

    # إضافة رد البوت إلى المحادثة
    user_conversation.append({"role": "assistant", "content": reply})

    # حفظ المحادثة في قاعدة البيانات
    save_conversation_to_db(user_id, user_conversation)

    # إرسال الرد للمستخدم
    await message.reply_text(reply)

# تشغيل البوت
if __name__ == "__main__":
    print("Bot is running...")
    app.run()
