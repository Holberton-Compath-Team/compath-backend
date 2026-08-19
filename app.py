import os
import datetime
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_mysqldb import MySQL
import MySQLdb.cursors
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from dotenv import load_dotenv

# Mühit dəyişənlərini (.env) yükləyirik
load_dotenv()

app = Flask(__name__)
CORS(app)

# Təhlükəsizlik açarı
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'CompathKey2026')

# Verilənlər Bazası Konfiqurasiyası
app.config['MYSQL_HOST'] = os.getenv('DB_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('DB_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('DB_PASSWORD', '')
app.config['MYSQL_DB'] = os.getenv('DB_NAME', 'compath_db')

mysql = MySQL(app)

# ==========================================
# 🛡️ QORUYUCU FUNKSİYALAR (DECORATORS)
# ==========================================

# 1. Ümumi Token Yoxlaması (Həm tələbə, həm admin üçündür)
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        
        if not token:
            return jsonify({'error': 'Token tapılmadı!'}), 401
            
        try:
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            current_user = data
        except Exception as e:
            return jsonify({'error': 'Etibarsız və ya vaxtı bitmiş token!'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

# Admin rolunu yoxlayan köməkçi funksiya
def is_admin(current_user):
    return current_user.get('role') == 'admin'

# 2. Yalnız Admin Yoxlaması
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        
        if not token:
            return jsonify({'error': 'Token tapılmadı!'}), 401
            
        try:
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            if data.get('role') != 'admin':
                return jsonify({'error': 'İcazə rədd edildi! Bu əməliyyat yalnız Adminlər üçündür.'}), 403
            current_user = data
        except Exception as e:
            return jsonify({'error': 'Etibarsız token!'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

# ==========================================
# 🔑 AUTENTİFİKASİYA API-ləri
# ==========================================

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    fullname = data.get('fullname')
    email = data.get('email')
    password = data.get('password')

    if not fullname or not email or not password:
        return jsonify({'error': 'Məlumatlar əskikdir'}), 400

    hashed_password = generate_password_hash(password)

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    if cursor.fetchone():
        return jsonify({'error': 'Bu email artıq mövcuddur'}), 409

    cursor.execute(
        "INSERT INTO users (fullname, email, password, role) VALUES (%s, %s, %s, 'student')",
        (fullname, email, hashed_password)
    )
    mysql.connection.commit()
    cursor.close()

    return jsonify({'message': 'Qeydiyyat uğurla tamamlandı'}), 201


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email və şifrə daxil edilməlidir'}), 400

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, fullname, email, password, role FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()

    if not user or not check_password_hash(user['password'], password):
        return jsonify({'error': 'Email və ya şifrə yanlışdır'}), 401

    token = jwt.encode({
        'user_id': user['id'],
        'role': user['role'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['JWT_SECRET_KEY'], algorithm="HS256")

    # Frontend-in istədiyi formatda cavab qaytarırıq (id sahəsi əlavə edilib)
    return jsonify({
        'token': token,
        'user': {
            'id': user['id'],
            'fullname': user['fullname'],
            'email': user['email'],
            'role': user['role']
        }
    }), 200

# ==========================================
# 📋 ŞİKAYƏTLƏR (TICKETS) API-ləri
# ==========================================

# 1. Yeni şikayət yaratmaq (Tələbələr üçün)
@app.route('/api/tickets', methods=['POST'])
@token_required
def create_ticket(current_user):
    data = request.get_json()
    title = data.get('title')
    description = data.get('description')
    department = data.get('department')

    if not title or not description or not department:
        return jsonify({'error': 'Məlumatlar əskikdir'}), 400

    cursor = mysql.connection.cursor()
    cursor.execute(
        "INSERT INTO tickets (user_id, title, description, department, status) VALUES (%s, %s, %s, %s, 'Gözləmədə')",
        (current_user['user_id'], title, description, department)
    )
    mysql.connection.commit()
    cursor.close()

    return jsonify({'message': 'Müraciət uğurla yaradıldı'}), 201

# 2. Tələbənin ÖZ şikayətlərinə baxması
@app.route('/api/tickets', methods=['GET'])
@token_required
def get_my_tickets(current_user):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM tickets WHERE user_id = %s", (current_user['user_id'],))
    tickets = cursor.fetchall()
    cursor.close()
    
    return jsonify(tickets), 200

# 3. BÜTÜN şikayətlərə baxmaq (Yalnız Admin üçün)
@app.route('/api/tickets/all', methods=['GET'])
@admin_required
def get_all_tickets(current_user):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    query = """
        SELECT t.id, t.title, t.description, t.department, t.status, t.created_at, 
               u.fullname, u.email 
        FROM tickets t
        JOIN users u ON t.user_id = u.id
        ORDER BY t.created_at DESC
    """
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()

    # Frontend-in istədiyi nested (iç-içə) JSON formatı
    formatted_tickets = []
    for row in results:
        formatted_tickets.append({
            "id": row['id'],
            "title": row['title'],
            "description": row['description'],
            "department": row['department'],
            "status": row['status'],
            "created_at": row['created_at'],
            "student": {
                "fullname": row['fullname'],
                "email": row['email']
            }
        })
        
    return jsonify(formatted_tickets), 200

# 4. Şikayətin statusunu dəyişmək (Yalnız Admin üçün)
@app.route('/api/tickets/<int:ticket_id>', methods=['PUT'])
@admin_required
def update_ticket_status(current_user, ticket_id):
    data = request.get_json()
    new_status = data.get('status')

    if not new_status:
        return jsonify({'error': 'Yeni status göndərilməyib'}), 400

    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE tickets SET status = %s WHERE id = %s", (new_status, ticket_id))
    mysql.connection.commit()
    
    if cursor.rowcount == 0:
        cursor.close()
        return jsonify({'error': 'Şikayət tapılmadı'}), 404
        
    cursor.close()
    return jsonify({'message': 'Status uğurla yeniləndi'}), 200

# ==========================================
# 🏢 XİDMƏT KATALOQU (SERVICES) API-ləri
# ==========================================

# 1. Bütün xidmətləri gətirmək (Hər kəs görə bilər)
@app.route('/api/services', methods=['GET'])
def get_services():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, name, description, created_at FROM services")
    services = cursor.fetchall()
    cursor.close()
    
    return jsonify(services), 200

# 2. Yeni xidmət əlavə etmək (Yalnız Admin üçün)
@app.route('/api/services', methods=['POST'])
@admin_required
def create_service(current_user):
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')

    if not name or not description:
        return jsonify({'error': 'Xidmət adı və təsviri daxil edilməlidir'}), 400

    cursor = mysql.connection.cursor()
    cursor.execute("INSERT INTO services (name, description) VALUES (%s, %s)", (name, description))
    mysql.connection.commit()
    service_id = cursor.lastrowid
    cursor.close()

    return jsonify({'message': 'Xidmət uğurla yaradıldı', 'id': service_id}), 201


# 3. Xidməti silmək (Yalnız Admin üçün)
@app.route('/api/services/<int:service_id>', methods=['DELETE'])
@admin_required
def delete_service(current_user, service_id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM services WHERE id = %s", (service_id,))
    mysql.connection.commit()

    if cursor.rowcount == 0:
        cursor.close()
        return jsonify({'error': 'Xidmət tapılmadı'}), 404

    cursor.close()
    return jsonify({'message': 'Xidmət uğurla silindi'}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
