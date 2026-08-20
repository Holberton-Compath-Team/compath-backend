import os
import datetime
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from dotenv import load_dotenv
from flask_swagger_ui import get_swaggerui_blueprint

# 🔥 Firebase paketləri
import firebase_admin
from firebase_admin import credentials, firestore

# Mühit dəyişənlərini (.env) yükləyirik
load_dotenv()

app = Flask(__name__)
CORS(app)

# ==========================================
# 📚 SWAGGER SƏNƏDLƏŞMƏSİ (DOCS)
# ==========================================
SWAGGER_URL = '/api/docs'
API_URL = '/static/swagger.json'
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "COMPATH API Docs"}
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

# Təhlükəsizlik açarı
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'CompathKey2026')

# ==========================================
# 🔥 FİREBASE BAĞLANTISI
# ==========================================
cred = credentials.Certificate("compath-ee7c5-firebase-adminsdk-fbsvc-85b5ad0528.json")
firebase_admin.initialize_app(cred)

# Verilənlər bazasına referans
db = firestore.client()

# ==========================================
# 🛡️ QORUYUCU FUNKSİYALAR (DECORATORS)
# ==========================================

# 1. Ümumi Token Yoxlaması
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

    users_ref = db.collection('users')
    
    # Emailin olub-olmadığını yoxlayırıq
    existing_users = users_ref.where('email', '==', email).limit(1).get()
    if len(existing_users) > 0:
        return jsonify({'error': 'Bu email artıq mövcuddur'}), 409

    hashed_password = generate_password_hash(password)

    # Yeni istifadəçini əlavə edirik
    users_ref.add({
        'fullname': fullname,
        'email': email,
        'password': hashed_password,
        'role': 'student',
        'created_at': firestore.SERVER_TIMESTAMP
    })

    return jsonify({'message': 'Qeydiyyat uğurla tamamlandı'}), 201


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email və şifrə daxil edilməlidir'}), 400

    # Firebase-dən istifadəçini email-ə görə tapırıq
    users = db.collection('users').where('email', '==', email).limit(1).get()

    if len(users) == 0:
        return jsonify({'error': 'Email və ya şifrə yanlışdır'}), 401

    user_doc = users[0]
    user_data = user_doc.to_dict()

    if not check_password_hash(user_data['password'], password):
        return jsonify({'error': 'Email və ya şifrə yanlışdır'}), 401

    token = jwt.encode({
        'user_id': user_doc.id,
        'role': user_data.get('role', 'student'),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['JWT_SECRET_KEY'], algorithm="HS256")

    return jsonify({
        'token': token,
        'user': {
            'id': user_doc.id,
            'fullname': user_data.get('fullname'),
            'email': user_data.get('email'),
            'role': user_data.get('role', 'student')
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

    db.collection('tickets').add({
        'user_id': current_user['user_id'],
        'title': title,
        'description': description,
        'department': department,
        'status': 'Gözləmədə',
        'created_at': firestore.SERVER_TIMESTAMP
    })

    return jsonify({'message': 'Müraciət uğurla yaradıldı'}), 201

# 2. Tələbənin ÖZ şikayətlərinə baxması
@app.route('/api/tickets', methods=['GET'])
@token_required
def get_my_tickets(current_user):
    tickets_ref = db.collection('tickets').where('user_id', '==', current_user['user_id'])
    docs = tickets_ref.stream()
    
    tickets = []
    for doc in docs:
        t_data = doc.to_dict()
        t_data['id'] = doc.id
        if 'created_at' in t_data and t_data['created_at']:
            t_data['created_at'] = t_data['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        tickets.append(t_data)
        
    tickets.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return jsonify(tickets), 200

# 3. BÜTÜN şikayətlərə baxmaq (Yalnız Admin üçün)
@app.route('/api/tickets/all', methods=['GET'])
@admin_required
def get_all_tickets(current_user):
    # Ən yeniləri birinci gətiririk
    docs = db.collection('tickets').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
    
    formatted_tickets = []
    users_cache = {} 

    for doc in docs:
        t_data = doc.to_dict()
        user_id = t_data.get('user_id')
        
        student_info = {"fullname": "Bilinmir", "email": "Bilinmir"}
        if user_id:
            if user_id not in users_cache:
                user_doc = db.collection('users').document(user_id).get()
                if user_doc.exists:
                    u_data = user_doc.to_dict()
                    users_cache[user_id] = {
                        "fullname": u_data.get('fullname', 'Bilinmir'),
                        "email": u_data.get('email', 'Bilinmir')
                    }
            if user_id in users_cache:
                student_info = users_cache[user_id]

        formatted_tickets.append({
            "id": doc.id,
            "title": t_data.get('title'),
            "description": t_data.get('description'),
            "department": t_data.get('department'),
            "status": t_data.get('status'),
            "created_at": t_data.get('created_at').strftime('%Y-%m-%d %H:%M:%S') if t_data.get('created_at') else None,
            "student": student_info
        })
        
    return jsonify(formatted_tickets), 200

# 4. Şikayətin statusunu dəyişmək (Yalnız Admin üçün)
@app.route('/api/tickets/<ticket_id>', methods=['PUT'])
@admin_required
def update_ticket_status(current_user, ticket_id):
    data = request.get_json()
    new_status = data.get('status')

    if not new_status:
        return jsonify({'error': 'Yeni status göndərilməyib'}), 400

    ticket_ref = db.collection('tickets').document(ticket_id)
    
    if not ticket_ref.get().exists:
        return jsonify({'error': 'Şikayət tapılmadı'}), 404

    ticket_ref.update({'status': new_status})
    return jsonify({'message': 'Status uğurla yeniləndi'}), 200

# ==========================================
# 🏢 XİDMƏT KATALOQU (SERVICES) API-ləri
# ==========================================

# 1. Bütün xidmətləri gətirmək (Hər kəs görə bilər)
@app.route('/api/services', methods=['GET'])
def get_services():
    docs = db.collection('services').stream()
    services = []
    
    for doc in docs:
        s_data = doc.to_dict()
        s_data['id'] = doc.id
        if 'created_at' in s_data and s_data['created_at']:
            s_data['created_at'] = s_data['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        services.append(s_data)
        
    return jsonify(services), 200

# 2. Yeni xidmət əlavə etmək (Yalnız Admin üçün) - FİREBASE VERSIYASI
@app.route('/api/services', methods=['POST'])
@admin_required
def create_service(current_user):
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')

    if not name or not description:
        return jsonify({'error': 'Xidmət adı və təsviri daxil edilməlidir'}), 400

    new_service_ref = db.collection('services').document()
    new_service_ref.set({
        'name': name,
        'description': description,
        'created_at': firestore.SERVER_TIMESTAMP
    })

    return jsonify({'message': 'Xidmət uğurla yaradıldı', 'id': new_service_ref.id}), 201

# 3. Xidməti silmək (Yalnız Admin üçün) - FİREBASE VERSIYASI
# Diqqət: id Firebase-də string olduğu üçün <int:service_id> əvəzinə <service_id> oldu
@app.route('/api/services/<service_id>', methods=['DELETE'])
@admin_required
def delete_service(current_user, service_id):
    service_ref = db.collection('services').document(service_id)
    
    if not service_ref.get().exists:
        return jsonify({'error': 'Xidmət tapılmadı'}), 404

    service_ref.delete()
    return jsonify({'message': 'Xidmət uğurla silindi'}), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)