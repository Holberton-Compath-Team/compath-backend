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
    
    existing_users = users_ref.where('email', '==', email).limit(1).get()
    if len(existing_users) > 0:
        return jsonify({'error': 'Bu email artıq mövcuddur'}), 409

    hashed_password = generate_password_hash(password)

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

@app.route('/api/tickets', methods=['POST'])
@token_required
def create_ticket(current_user):
    data = request.get_json()
    title = data.get('title')
    description = data.get('description')
    department = data.get('department')
    priority = data.get('priority', 'low')

    if not title or not description or not department:
        return jsonify({'error': 'Məlumatlar əskikdir'}), 400

    user_doc = db.collection('users').document(current_user['user_id']).get()
    author_name = user_doc.to_dict().get('fullname', 'Tələbə') if user_doc.exists else 'Tələbə'

    # Axtarış üçün sözləri kiçik hərflərlə massivə yığırıq
    search_string = f"{title} {author_name}".lower()
    search_terms = search_string.split()

    ticket_ref = db.collection('tickets').document()
    
    ticket_data = {
        'ticketId': ticket_ref.id,
        'userId': current_user['user_id'],
        'authorName': author_name,
        'title': title,
        'description': description,
        'department': department,
        'status': 'pending',
        'priority': priority,
        'createdAt': firestore.SERVER_TIMESTAMP,
        'attachedFiles': [],
        'searchTerms': search_terms
    }

    if department == 'Finance':
        ticket_data['customFields'] = {
            'documentType': data.get('documentType', ''),
            'educationType': data.get('educationType', ''),
            'finCode': data.get('finCode', '').upper()
        }

    ticket_ref.set(ticket_data)

    return jsonify({'message': 'Müraciət uğurla yaradıldı', 'ticketId': ticket_ref.id}), 201

@app.route('/api/tickets', methods=['GET'])
@token_required
def get_my_tickets(current_user):
    tickets_ref = db.collection('tickets').where('userId', '==', current_user['user_id'])
    docs = tickets_ref.stream()
    
    tickets = []
    for doc in docs:
        t_data = doc.to_dict()
        t_data['id'] = doc.id
        if 'createdAt' in t_data and t_data['createdAt']:
            t_data['createdAt'] = t_data['createdAt'].strftime('%Y-%m-%d %H:%M:%S')
        tickets.append(t_data)
        
    tickets.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
    return jsonify(tickets), 200

# FİLTERLƏMƏ VƏ AXTARIŞ BURA ƏLAVƏ EDİLDİ
@app.route('/api/tickets/all', methods=['GET'])
@admin_required
def get_all_tickets(current_user):
    # Frontend-dən gələn parametrləri oxuyuruq
    status = request.args.get('status')
    department = request.args.get('department')
    search_query = request.args.get('search')
    
    query = db.collection('tickets')
    
    # Əgər status göndərilibsə və "Bütün statuslar" deyilsə, filterlə
    if status and status != 'Bütün statuslar':
        query = query.where('status', '==', status)
        
    # Əgər department göndərilibsə və "Bütün şöbələr" deyilsə, filterlə
    if department and department != 'Bütün şöbələr':
        query = query.where('department', '==', department)
        
    # Axtarış sözü (searchTerms) üzrə axtarış
    if search_query:
        query = query.where('searchTerms', 'array_contains', search_query.lower())

    docs = query.stream()
    
    formatted_tickets = []
    for doc in docs:
        t_data = doc.to_dict()
        t_data['id'] = doc.id
        if 'createdAt' in t_data and t_data['createdAt']:
            t_data['createdAt'] = t_data['createdAt'].strftime('%Y-%m-%d %H:%M:%S')
        formatted_tickets.append(t_data)
        
    # Tarixə görə Python tərəfində sıralayırıq (Firestore composite index errorundan qaçmaq üçün)
    formatted_tickets.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
        
    return jsonify(formatted_tickets), 200

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
# 💬 ÇAT (MESAJLAŞMA) API-ləri
# ==========================================

@app.route('/api/tickets/<ticket_id>/messages', methods=['POST'])
@token_required
def add_message(current_user, ticket_id):
    data = request.get_json()
    text = data.get('text')
    
    if not text:
        return jsonify({'error': 'Mesaj mətni boş ola bilməz'}), 400
        
    ticket_ref = db.collection('tickets').document(ticket_id)
    if not ticket_ref.get().exists:
        return jsonify({'error': 'Şikayət tapılmadı'}), 404
        
    msg_ref = ticket_ref.collection('messages').document()
    msg_ref.set({
        'messageId': msg_ref.id,
        'senderId': current_user['user_id'],
        'senderRole': current_user.get('role', 'student'),
        'text': text,
        'timestamp': firestore.SERVER_TIMESTAMP
    })
    
    return jsonify({'message': 'Mesaj uğurla göndərildi', 'messageId': msg_ref.id}), 201

@app.route('/api/tickets/<ticket_id>/messages', methods=['GET'])
@token_required
def get_messages(current_user, ticket_id):
    ticket_ref = db.collection('tickets').document(ticket_id)
    if not ticket_ref.get().exists:
        return jsonify({'error': 'Şikayət tapılmadı'}), 404
        
    docs = ticket_ref.collection('messages').order_by('timestamp', direction=firestore.Query.ASCENDING).stream()
    
    messages = []
    for doc in docs:
        m_data = doc.to_dict()
        if 'timestamp' in m_data and m_data['timestamp']:
            m_data['timestamp'] = m_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        messages.append(m_data)
        
    return jsonify(messages), 200

# ==========================================
# 🏢 XİDMƏT KATALOQU (SERVICES) API-ləri
# ==========================================

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