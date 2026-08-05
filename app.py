from flask_swagger_ui import get_swaggerui_blueprint
from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os

# .env faylındakı məlumatları yükləyirik
load_dotenv()

app = Flask(__name__)
# --- SWAGGER UI KONFİQURASİYASI ---
SWAGGER_URL = '/api/docs'
API_URL = '/static/swagger.json'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "COMPATH API Docs"}
)

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
# ----------------------------------
# MySQL Konfiqurasiyası
app.config['MYSQL_HOST'] = os.getenv('DB_HOST')
app.config['MYSQL_USER'] = os.getenv('DB_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('DB_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('DB_NAME')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor' 

mysql = MySQL(app)

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

# LOGIN API
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
        return jsonify({
            "status": "success", 
            "message": "Uğurla daxil oldunuz!",
            "user": {"id": user['id'], "fullname": user['fullname'], "email": user['email']}
        }), 200
    else:
        return jsonify({"error": "E-poçt və ya şifrə yanlışdır!"}), 401

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)