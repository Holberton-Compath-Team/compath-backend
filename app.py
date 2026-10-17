import os
import uuid
import random
import string
import datetime
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import jwt
from dotenv import load_dotenv
from flask_swagger_ui import get_swaggerui_blueprint

# 🔥 Firebase paketləri
import firebase_admin
from firebase_admin import credentials, firestore

# Mühit dəyişənlərini (.env) yükləyirik
load_dotenv()

app = Flask(__name__)
# Bütün origin-lərə və başlıqlara icazə veririk (CORS problemi olmaması üçün)
CORS(app, resources={r"/*": {"origins": "*"}})

# ==========================================
# 📁 FAYL YÜKLƏMƏ (UPLOAD) KONFİQURASİYASI
# ==========================================
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Maksimum 16 MB fayl

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
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ==========================================
# 🛠️ KÖMƏKÇİ FUNKSİYALAR (FORMAT VƏ KOD)
# ==========================================

VALID_PRIORITIES = ["Aşağı", "Orta", "Yüksək", "Təcili"]
PRIORITY_MAP = {
    "low": "Aşağı",
    "medium": "Orta",
    "high": "Yüksək",
    "urgent": "Təcili",
    "aşağı": "Aşağı",
    "orta": "Orta",
    "yüksək": "Yüksək",
    "təcili": "Təcili"
}

def normalize_priority(val):
    if not val or not str(val).strip():
        return "Orta"
    val_str = str(val).strip()
    if val_str in VALID_PRIORITIES:
        return val_str
    return PRIORITY_MAP.get(val_str.lower(), "Orta")

def generate_tracking_code():
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choices(chars, k=6))
    return f"CP-{random_part}"

def format_timestamp(ts):
    if not ts:
        return ""
    if hasattr(ts, 'strftime'):
        return ts.strftime('%Y-%m-%d %H:%M:%S')
    return str(ts)

def format_ticket(doc):
    """Bütün ticket cavablarını vahid camelCase standartına salır"""
    d = doc.to_dict() if hasattr(doc, 'to_dict') else doc
    doc_id = doc.id if hasattr(doc, 'id') else d.get('id', d.get('ticketId', ''))

    created_raw = d.get('createdAt') or d.get('created_at')
    updated_raw = d.get('updatedAt') or d.get('updated_at') or created_raw

    return {
        'id': doc_id,
        'ticketId': doc_id,
        'trackingCode': d.get('trackingCode') or d.get('tracking_code') or f"CP-{doc_id[:6].upper()}",
        'userId': d.get('userId') or d.get('user_id') or 'anonymous',
        'authorName': d.get('authorName') or d.get('author_name') or d.get('fullname') or 'Anonim',
        'authorEmail': d.get('authorEmail') or d.get('email') or '',
        'title': d.get('title', ''),
        'description': d.get('description', ''),
        'department': d.get('department') or d.get('category', ''),
        'category': d.get('category') or d.get('department', ''),
        'status': d.get('status', 'pending'),
        'priority': normalize_priority(d.get('priority')),
        'attachedFiles': d.get('attachedFiles') if isinstance(d.get('attachedFiles'), list) else [],
        'customFields': d.get('customFields', {}),
        'createdAt': format_timestamp(created_raw),
        'updatedAt': format_timestamp(updated_raw)
    }

def format_message(doc):
    """Bütün mesaj cavablarını vahid camelCase standartına salır"""
    m = doc.to_dict() if hasattr(doc, 'to_dict') else doc
    doc_id = doc.id if hasattr(doc, 'id') else m.get('id', m.get('messageId', ''))
    ts_raw = m.get('createdAt') or m.get('timestamp') or m.get('created_at')
    formatted_time = format_timestamp(ts_raw)

    return {
        'id': doc_id,
        'messageId': doc_id,
        'senderId': m.get('senderId') or m.get('userId') or m.get('user_id') or 'anonymous',
        'userId': m.get('userId') or m.get('senderId') or m.get('user_id') or 'anonymous',
        'authorName': m.get('authorName') or m.get('senderName') or ('Admin' if m.get('senderRole') == 'admin' else 'İstifadəçi'),
        'senderRole': m.get('senderRole') or m.get('role', 'student'),
        'text': m.get('text') or m.get('message', ''),
        'attachedFiles': m.get('attachedFiles') if isinstance(m.get('attachedFiles'), list) else [],
        'createdAt': formatted_time,
        'timestamp': formatted_time
    }

# ==========================================
# 🛡️ QORUYUCU FUNKSİYALAR (DECORATORS)
# ==========================================

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split(" ")
            if len(parts) == 2:
                token = parts[1]
        
        if not token:
            return jsonify({'error': 'Token tapılmadı!'}), 401
            
        try:
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            current_user = data
        except Exception:
            return jsonify({'error': 'Etibarsız və ya vaxtı bitmiş token!'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split(" ")
            if len(parts) == 2:
                token = parts[1]
        
        if not token:
            return jsonify({'error': 'Token tapılmadı!'}), 401
            
        try:
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            if data.get('role') != 'admin':
                return jsonify({'error': 'İcazə rədd edildi! Bu əməliyyat yalnız Adminlər üçündür.'}), 403
            current_user = data
        except Exception:
            return jsonify({'error': 'Etibarsız token!'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

# ==========================================
# 📤 FAYL YÜKLƏMƏ (UPLOAD) API-si (Kartsız/Pulsuz)
# ==========================================

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Fayl göndərilməyib (key olaraq "file" istifadə edin)'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Fayl seçilməyib'}), 400

    original_name = secure_filename(file.filename)
    ext = os.path.splitext(original_name)[1]
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(save_path)

    base_url = request.host_url.rstrip('/')
    if base_url.startswith('http://') and 'onrender.com' in base_url:
        base_url = base_url.replace('http://', 'https://', 1)

    file_url = f"{base_url}/static/uploads/{unique_filename}"
    return jsonify({
        'message': 'Fayl uğurla yükləndi',
        'url': file_url,
        'fileUrl': file_url,
        'fileName': file.filename
    }), 200

@app.route('/static/uploads/<path:filename>', methods=['GET'])
def serve_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ==========================================
# 🔑 AUTENTİFİKASİYA API-ləri
# ==========================================

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json() or {}
    fullname = (data.get('fullname') or '').strip()
    email = (data.get('email') or '').lower().strip()
    password = data.get('password')

    if not fullname or not email or not password:
        return jsonify({'error': 'Məlumatlar əskikdir'}), 400

    users_ref = db.collection('users')
    existing_users = users_ref.where('email', '==', email).limit(1).get()
    if len(existing_users) > 0:
        return jsonify({'error': 'Bu email artıq mövcuddur'}), 409

    hashed_password = generate_password_hash(password)

    _, doc_ref = users_ref.add({
        'fullname': fullname,
        'email': email,
        'password': hashed_password,
        'role': 'student',
        'createdAt': firestore.SERVER_TIMESTAMP
    })

    return jsonify({'message': 'Qeydiyyat uğurla tamamlandı', 'userId': doc_ref.id}), 201


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = (data.get('email') or '').lower().strip()
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
            'userId': user_doc.id,
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
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    description = (data.get('description') or '').strip()
    department = data.get('department') or data.get('category')
    priority = normalize_priority(data.get('priority'))
    attached_files = data.get('attachedFiles', [])

    if not title or not description or not department:
        return jsonify({'error': 'Məlumatlar əskikdir (title, description, department tələb olunur)'}), 400

    user_doc = db.collection('users').document(current_user['user_id']).get()
    user_dict = user_doc.to_dict() if user_doc.exists else {}
    author_name = user_dict.get('fullname', 'Tələbə')
    author_email = user_dict.get('email', '')

    tracking_code = generate_tracking_code()
    search_string = f"{title} {author_name} {tracking_code}".lower()
    search_terms = search_string.split()

    ticket_ref = db.collection('tickets').document()
    
    ticket_data = {
        'ticketId': ticket_ref.id,
        'trackingCode': tracking_code,
        'userId': current_user['user_id'],
        'authorName': author_name,
        'authorEmail': author_email,
        'title': title,
        'description': description,
        'department': department,
        'category': department,
        'status': 'pending',
        'priority': priority,
        'createdAt': firestore.SERVER_TIMESTAMP,
        'updatedAt': firestore.SERVER_TIMESTAMP,
        'attachedFiles': attached_files if isinstance(attached_files, list) else [],
        'searchTerms': search_terms
    }

    if department == 'Finance':
        ticket_data['customFields'] = {
            'documentType': data.get('documentType', ''),
            'educationType': data.get('educationType', ''),
            'finCode': (data.get('finCode') or '').upper()
        }

    ticket_ref.set(ticket_data)
    saved_doc = ticket_ref.get()

    return jsonify({
        'message': 'Müraciət uğurla yaradıldı',
        'ticketId': ticket_ref.id,
        'trackingCode': tracking_code,
        'ticket': format_ticket(saved_doc)
    }), 201


# 🕵️ ANONİM MÜRACİƏT YARATMA (Token tələb etmir)
@app.route('/api/tickets/anonymous', methods=['POST'])
def create_anonymous_ticket():
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    description = (data.get('description') or '').strip()
    department = data.get('department') or data.get('category')
    priority = normalize_priority(data.get('priority'))
    author_name = (data.get('authorName') or data.get('fullname') or 'Anonim İstifadəçi').strip()
    author_email = (data.get('authorEmail') or data.get('email') or '').strip()
    attached_files = data.get('attachedFiles', [])

    if not title or not description or not department:
        return jsonify({'error': 'Məlumatlar əskikdir (title, description, department tələb olunur)'}), 400

    tracking_code = generate_tracking_code()
    search_string = f"{title} {author_name} {tracking_code}".lower()
    search_terms = search_string.split()

    ticket_ref = db.collection('tickets').document()

    ticket_data = {
        'ticketId': ticket_ref.id,
        'trackingCode': tracking_code,
        'userId': 'anonymous',
        'authorName': author_name,
        'authorEmail': author_email,
        'title': title,
        'description': description,
        'department': department,
        'category': department,
        'status': 'pending',
        'priority': priority,
        'createdAt': firestore.SERVER_TIMESTAMP,
        'updatedAt': firestore.SERVER_TIMESTAMP,
        'attachedFiles': attached_files if isinstance(attached_files, list) else [],
        'searchTerms': search_terms
    }

    if department == 'Finance':
        ticket_data['customFields'] = {
            'documentType': data.get('documentType', ''),
            'educationType': data.get('educationType', ''),
            'finCode': (data.get('finCode') or '').upper()
        }

    ticket_ref.set(ticket_data)
    saved_doc = ticket_ref.get()

    return jsonify({
        'message': 'Anonim müraciət uğurla yaradıldı',
        'ticketId': ticket_ref.id,
        'trackingCode': tracking_code,
        'ticket': format_ticket(saved_doc)
    }), 201


# 🔍 İZLƏMƏ KODU İLƏ AXTARIŞ (Token tələb etmir)
@app.route('/api/track/<tracking_code>', methods=['GET'])
def track_ticket(tracking_code):
    code = tracking_code.strip().upper()
    tickets_ref = db.collection('tickets').where('trackingCode', '==', code).limit(1).get()

    if len(tickets_ref) == 0:
        return jsonify({'error': 'Bu izləmə koduna uyğun müraciət tapılmadı'}), 404

    ticket_doc = tickets_ref[0]
    ticket_info = format_ticket(ticket_doc)

    # Həmin ticket-in mesajlarını da əlavə edirik
    msg_docs = ticket_doc.reference.collection('messages').stream()
    messages = [format_message(m) for m in msg_docs]
    messages.sort(key=lambda x: x.get('createdAt', ''))

    ticket_info['messages'] = messages
    return jsonify(ticket_info), 200


@app.route('/api/tickets', methods=['GET'])
@token_required
def get_my_tickets(current_user):
    # Həm yeni userId, həm də köhnə user_id ilə olanları yoxlayırıq
    docs_camel = list(db.collection('tickets').where('userId', '==', current_user['user_id']).stream())
    docs_snake = list(db.collection('tickets').where('user_id', '==', current_user['user_id']).stream())
    
    seen_ids = set()
    tickets = []
    for doc in docs_camel + docs_snake:
        if doc.id not in seen_ids:
            seen_ids.add(doc.id)
            tickets.append(format_ticket(doc))
        
    tickets.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
    return jsonify(tickets), 200


@app.route('/api/tickets/all', methods=['GET'])
@admin_required
def get_all_tickets(current_user):
    status = request.args.get('status')
    department = request.args.get('department')
    priority = request.args.get('priority')
    search_query = request.args.get('search')
    
    query = db.collection('tickets')
    
    if status and status != 'Bütün statuslar':
        query = query.where('status', '==', status)
        
    if department and department != 'Bütün şöbələr':
        query = query.where('department', '==', department)

    if priority and priority != 'Bütün prioritetlər':
        query = query.where('priority', '==', normalize_priority(priority))
        
    if search_query:
        query = query.where('searchTerms', 'array_contains', search_query.lower())

    docs = query.stream()
    formatted_tickets = [format_ticket(doc) for doc in docs]
    formatted_tickets.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
        
    return jsonify(formatted_tickets), 200


@app.route('/api/tickets/<ticket_id>', methods=['GET'])
@token_required
def get_single_ticket(current_user, ticket_id):
    ticket_ref = db.collection('tickets').document(ticket_id).get()
    if not ticket_ref.exists:
        return jsonify({'error': 'Şikayət tapılmadı'}), 404
    return jsonify(format_ticket(ticket_ref)), 200


@app.route('/api/tickets/<ticket_id>', methods=['PUT'])
@admin_required
def update_ticket_status(current_user, ticket_id):
    data = request.get_json() or {}
    new_status = data.get('status')
    new_priority = data.get('priority')

    if not new_status and not new_priority:
        return jsonify({'error': 'Yenilənəcək məlumat (status və ya priority) göndərilməyib'}), 400

    ticket_ref = db.collection('tickets').document(ticket_id)
    if not ticket_ref.get().exists:
        return jsonify({'error': 'Şikayət tapılmadı'}), 404

    update_fields = {'updatedAt': firestore.SERVER_TIMESTAMP}
    if new_status:
        update_fields['status'] = new_status
    if new_priority:
        update_fields['priority'] = normalize_priority(new_priority)

    ticket_ref.update(update_fields)
    return jsonify({
        'message': 'Müraciət uğurla yeniləndi',
        'ticket': format_ticket(ticket_ref.get())
    }), 200

# ==========================================
# 💬 ÇAT (MESAJLAŞMA) API-ləri
# ==========================================

@app.route('/api/tickets/<ticket_id>/messages', methods=['POST'])
@token_required
def add_message(current_user, ticket_id):
    data = request.get_json() or {}
    text = (data.get('text') or data.get('message') or '').strip()
    attached_files = data.get('attachedFiles', [])
    
    if not text and not attached_files:
        return jsonify({'error': 'Mesaj mətni və ya fayl göndərilməlidir'}), 400
        
    ticket_ref = db.collection('tickets').document(ticket_id)
    if not ticket_ref.get().exists:
        return jsonify({'error': 'Şikayət tapılmadı'}), 404

    user_doc = db.collection('users').document(current_user['user_id']).get()
    author_name = user_doc.to_dict().get('fullname', 'İstifadəçi') if user_doc.exists else 'İstifadəçi'
        
    msg_ref = ticket_ref.collection('messages').document()
    msg_data = {
        'id': msg_ref.id,
        'messageId': msg_ref.id,
        'userId': current_user['user_id'],
        'senderId': current_user['user_id'],
        'authorName': author_name,
        'senderRole': current_user.get('role', 'student'),
        'text': text,
        'attachedFiles': attached_files if isinstance(attached_files, list) else [],
        'createdAt': firestore.SERVER_TIMESTAMP,
        'timestamp': firestore.SERVER_TIMESTAMP
    }
    msg_ref.set(msg_data)
    ticket_ref.update({'updatedAt': firestore.SERVER_TIMESTAMP})
    
    saved_msg = msg_ref.get()
    return jsonify({
        'message': 'Mesaj uğurla göndərildi',
        'messageId': msg_ref.id,
        'data': format_message(saved_msg)
    }), 201


@app.route('/api/tickets/<ticket_id>/messages', methods=['GET'])
@token_required
def get_messages(current_user, ticket_id):
    ticket_ref = db.collection('tickets').document(ticket_id)
    if not ticket_ref.get().exists:
        return jsonify({'error': 'Şikayət tapılmadı'}), 404
        
    docs = ticket_ref.collection('messages').stream()
    messages = [format_message(doc) for doc in docs]
    messages.sort(key=lambda x: x.get('createdAt', ''))
        
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
        created_raw = s_data.get('createdAt') or s_data.get('created_at')
        services.append({
            'id': doc.id,
            'name': s_data.get('name', ''),
            'description': s_data.get('description', ''),
            'createdAt': format_timestamp(created_raw)
        })
        
    return jsonify(services), 200


@app.route('/api/services', methods=['POST'])
@admin_required
def create_service(current_user):
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()

    if not name or not description:
        return jsonify({'error': 'Xidmət adı və təsviri daxil edilməlidir'}), 400

    new_service_ref = db.collection('services').document()
    new_service_ref.set({
        'name': name,
        'description': description,
        'createdAt': firestore.SERVER_TIMESTAMP
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