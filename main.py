from flask import Flask, request, jsonify
import pg8000
import os
from urllib.parse import urlparse

app = Flask(__name__)

# Подключение к БД
DATABASE_URL = os.environ.get('DATABASE_URL')
conn = None

if DATABASE_URL:
    try:
        url = urlparse(DATABASE_URL)
        conn = pg8000.connect(
            database=url.path[1:],  # убираем первый символ '/'
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
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
    if not conn:
        return jsonify({"error": "DB not connected"}), 500

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        message = data.get('message', '')
        
        with conn.cursor() as cur:
            cur.execute("INSERT INTO messages (content) VALUES (%s)", (message,))
            conn.commit()

        return jsonify({"status": "saved", "message": message})
    
    except Exception as e:
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
    app.run(debug=True)