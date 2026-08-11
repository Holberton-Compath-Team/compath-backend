from flask_swagger_ui import get_swaggerui_blueprint
from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
from flask_cors import CORS
# Yeni əlavə olunan kitabxanalar (JWT üçün)
import jwt
import datetime
from functools import wraps

# .env faylındakı məlumatları yükləyirik
load_dotenv()

app = Flask(__name__)
# --- SWAGGER UI KONFİQURASİYASI ---
SWAGGER_URL = '/api/docs'
API_URL = '/static/swagger.json'
CORS(app)

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "COMPATH API Docs"}
)

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
# ----------------------------------

# MySQL və JWT Konfiqurasiyası
app.config['MYSQL_HOST'] = os.getenv('DB_HOST')
app.config['MYSQL_USER'] = os.getenv('DB_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('DB_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('DB_NAME')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor' 
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY') # Token üçün gizli açarımız

mysql = MySQL(app)

# ==========================================
# JWT MÜHAFİZƏÇİSİ (DECORATOR)
# ==========================================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Token Authorization header-ində 'Bearer <token>' kimi göndərilməlidir
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        
        if not token:
            return jsonify({'error': 'İcazə rədd edildi! Token göndərilməyib.'}), 401
        
        try:
            # Token-i açırıq və içindən user_id-ni götürürük
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user_id = data['user_id']
        except:
            return jsonify({'error': 'Token etibarsızdır və ya vaxtı bitib!'}), 401
            
        return f(current_user_id, *args, **kwargs)
    return decorated

# ==========================================
# API ENDPOINT-LƏR
# ==========================================

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "COMPATH Backend API is running with MySQL!"}), 200

# SIGN UP API
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    fullname = data.get('fullname')
    email = data.get('email')
    password = data.get('password')

    if not fullname or not email or not password:
        return jsonify({"error": "Bütün sahələr doldurulmalıdır!"}), 400

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        cursor.close()
        return jsonify({"error": "Bu e-poçt artıq qeydiyyatdan keçib!"}), 409

    hashed_password = generate_password_hash(password)
    cursor.execute("INSERT INTO users (fullname, email, password) VALUES (%s, %s, %s)", (fullname, email, hashed_password))
    mysql.connection.commit()
    cursor.close()

    return jsonify({"status": "success", "message": "Uğurla qeydiyyatdan keçdiniz!"}), 201

# LOGIN API (Yeniləndi - Artıq Token qaytarır)
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "E-poçt və şifrə daxil edilməlidir!"}), 400

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()

    if user and check_password_hash(user['password'], password):
        # Şifrə düzgündürsə, 24 saatlıq Token yaradırıq:
        token = jwt.encode({
            'user_id': user['id'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
        }, app.config['SECRET_KEY'], algorithm="HS256")

        return jsonify({
            "status": "success", 
            "message": "Uğurla daxil oldunuz!",
            "token": token, # Frontend-ə tokeni göndəririk
            "user": {"id": user['id'], "fullname": user['fullname'], "email": user['email']}
        }), 200
    else:
        return jsonify({"error": "E-poçt və ya şifrə yanlışdır!"}), 401

# ==========================================
# SPRINT 2 - TƏLƏBƏ ŞİKAYƏTLƏRİ (TICKETS)
# ==========================================

# 1. Yeni şikayət yaratmaq (CREATE)
@app.route('/api/tickets', methods=['POST'])
@token_required
def create_ticket(current_user_id):
    data = request.get_json()
    
    title = data.get('title')
    description = data.get('description')
    department = data.get('department')
    
    if not all([title, description, department]):
        return jsonify({"error": "Bütün sahələr doldurulmalıdır!"}), 400
        
    cursor = mysql.connection.cursor()
    cursor.execute(
        "INSERT INTO tickets (user_id, title, description, department) VALUES (%s, %s, %s, %s)", 
        (current_user_id, title, description, department)
    )
    mysql.connection.commit()
    cursor.close()
    
    return jsonify({"message": "Şikayətiniz uğurla göndərildi!", "status": "Gözləmədə"}), 201

# 2. Şikayətlərin siyahısına baxmaq (READ)
@app.route('/api/tickets', methods=['GET'])
@token_required
def get_tickets(current_user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM tickets WHERE user_id = %s ORDER BY created_at DESC", (current_user_id,))
    tickets = cursor.fetchall()
    cursor.close()
    
    return jsonify(tickets), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)