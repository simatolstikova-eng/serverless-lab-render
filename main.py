from flask import Flask, request, jsonify
import pg8000
import os

app = Flask(__name__)

# Подключение к БД
DATABASE_URL = os.environ.get('DATABASE_URL')
conn = None

if DATABASE_URL:
    try:
        # Парсим DATABASE_URL вручную
        # Формат: postgresql://user:pass@host:port/dbname
        db_url = DATABASE_URL.replace("postgresql://", "").replace("postgres://", "")
        auth, hostport_db = db_url.split("@")
        user, password = auth.split(":")
        hostport, database = hostport_db.split("/")
        
        if ":" in hostport:
            host, port = hostport.split(":")
            port = int(port)
        else:
            host = hostport
            port = 5432  # стандартный порт PostgreSQL
            
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
        print(f"DATABASE_URL: {DATABASE_URL}")
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
        # Проверяем, что это JSON запрос
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
        
        data = request.get_json()
        
        # Если JSON пустой или некорректный
        if data is None:
            return jsonify({"error": "Invalid JSON data"}), 400
            
        message = data.get('message', '')
        
        # Проверяем, что message есть
        if not message:
            return jsonify({"error": "Message field is required"}), 400
        
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
    app.run(host='0.0.0.0', port=5000, debug=False)