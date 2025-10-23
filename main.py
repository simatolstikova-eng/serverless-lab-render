from flask import Flask, request, jsonify
import pg8000
import os
import json

app = Flask(__name__)

# Подключение к БД
DATABASE_URL = os.environ.get('DATABASE_URL')
conn = None

if DATABASE_URL:
    try:
        # Парсим DATABASE_URL вручную
        db_url = DATABASE_URL.replace("postgresql://", "").replace("postgres://", "")
        auth, hostport_db = db_url.split("@")
        user, password = auth.split(":")
        hostport, database = hostport_db.split("/")
        
        if ":" in hostport:
            host, port = hostport.split(":")
            port = int(port)
        else:
            host = hostport
            port = 5432
            
        conn = pg8000.connect(
            database=database,
            user=user,
            password=password,
            host=host,
            port=port
        )
        print("✅ Database connected successfully")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
else:
    print("❌ DATABASE_URL not found")

# Создание таблицы при старте
if conn:
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            conn.commit()
        print("✅ Table created successfully")
    except Exception as e:
        print(f"❌ Table creation failed: {e}")

@app.route('/')
def home():
    return jsonify({
        "status": "Server is running", 
        "db_connected": conn is not None
    })

@app.route('/save', methods=['POST'])
def save_message():
    print("📨 Received POST request to /save")
    
    if not conn:
        return jsonify({"error": "DB not connected"}), 500

    try:
        # Логируем заголовки
        print(f"📋 Headers: {dict(request.headers)}")
        print(f"📦 Content-Type: {request.content_type}")
        print(f"📦 Content-Length: {request.content_length}")
        
        # Проверяем Content-Type
        if not request.is_json:
            print("❌ Not JSON content type")
            return jsonify({
                "error": "Content-Type must be application/json",
                "received_content_type": request.content_type
            }), 400
        
        # Пробуем получить JSON
        data = request.get_json(force=True, silent=True)
        print(f"📝 Raw data: {data}")
        
        if data is None:
            # Пробуем прочитать сырые данные
            raw_data = request.get_data(as_text=True)
            print(f"📝 Raw request data: '{raw_data}'")
            return jsonify({
                "error": "Invalid JSON data",
                "raw_data_received": raw_data
            }), 400
            
        message = data.get('message', '')
        print(f"💾 Message to save: '{message}'")
        
        if not message:
            return jsonify({"error": "Message field is required"}), 400
        
        with conn.cursor() as cur:
            cur.execute("INSERT INTO messages (content) VALUES (%s)", (message,))
            conn.commit()

        print("✅ Message saved successfully")
        return jsonify({"status": "saved", "message": message})
    
    except Exception as e:
        print(f"❌ Error in save_message: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/messages')
def get_messages():
    if not conn:
        return jsonify({"error": "DB not connected"}), 500

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, content, created_at FROM messages ORDER BY id DESC LIMIT 10")
            rows = cur.fetchall()

        messages = [{"id": r[0], "text": r[1], "time": r[2].isoformat()} for r in rows]
        return jsonify(messages)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)