# Compath Backend API

Bu repository Compath layihəsinin arxa uç (backend) API-ni özündə cəmləşdirir. Layihə **Python (Flask)** və **MySQL** istifadə edilərək yazılmışdır. Sistemə JWT əsaslı autentifikasiya və Rol (Admin/Student) idarəetməsi daxildir.

## 🛠 Texnologiyalar
* **Dil:** Python 3.x
* **Freymvörk:** Flask
* **Verilənlər Bazası:** MySQL (Flask-MySQLdb)
* **Təhlükəsizlik:** PyJWT (Token), Werkzeug (Şifrə heşləmə)

---

## ⚙️ Lokal Quraşdırma (Frontend & Backend Komandası üçün)

Layihəni öz kompüterinizdə işə salmaq üçün aşağıdakı addımları ardıcıl izləyin:

### 1. Repository-ni klonlayın
```bash
git clone https://github.com/Holberton-Compath-Team/compath-backend.git
cd compath-backend
```

### 2. Virtual Mühiti yaradın və aktivləşdirin
* **Windows üçün:**
```bash
python -m venv venv
venv\Scripts\activate
```
* **Mac/Linux üçün:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Asılılıqları (Dependencies) yükləyin
*(Qeyd: Əgər `requirements.txt` yoxdursa, aşağıdakı paketləri yükləyin)*
```bash
pip install flask flask-cors flask-mysqldb pyjwt werkzeug python-dotenv
```

### 4. Mühit Dəyişənlərini (.env) hazırlayın
Layihənin ana qovluğunda yeni bir `.env` faylı yaradın və içinə bunları əlavə edin:
```env
JWT_SECRET_KEY=CompathKey2026
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=
DB_NAME=compath_db
```

### 5. Verilənlər Bazasını (MySQL) Quraşdırın
XAMPP (və ya başqa MySQL serveri) işə salın, `compath_db` adlı baza yaradın və aşağıdakı SQL kodlarını icra edin:

```sql
-- İstifadəçilər Cədvəli
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fullname VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'student'
);

-- Şikayətlər (Tickets) Cədvəli
CREATE TABLE tickets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    department VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'Gözləmədə',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Xidmət Kataloqu Cədvəli
CREATE TABLE services (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 6. Serveri İşə Salın
```bash
python app.py
```
Server `[http://127.0.0.1:5000](http://127.0.0.1:5000)` ünvanında işləməyə başlayacaq.

---

## 🔑 Test Hesabları
Frontend komandasının yönləndirmələri (Admin Panel) test edə bilməsi üçün hazır admin hesabı:
* **Email:** `admin@compath.az`
* **Şifrə:** `Admin123!`
* **Rol:** `admin`

---

## 📡 Əsas API Endpoint-ləri

### Autentifikasiya
* `POST /api/signup` - Yeni tələbə qeydiyyatı (Body: `fullname`, `email`, `password`)
* `POST /api/login` - Sistemə giriş. Cavabda `token` və `user` (id, fullname, email, role) qaytarır.

### Şikayətlər (Tickets)
* `POST /api/tickets` - Yeni şikayət yaratmaq (Tələbə üçün)
* `GET /api/tickets` - İstifadəçinin öz şikayətləri (Tələbə üçün)
* `GET /api/tickets/all` - Bütün tələbələrin şikayətləri (Yalnız Admin)
* `PUT /api/tickets/<id>` - Şikayətin statusunu dəyişmək (Yalnız Admin)

### Xidmət Kataloqu (Services)
* `GET /api/services` - Bütün xidmətlərin siyahısı (Hər kəs üçün)
* `POST /api/services` - Yeni xidmət yaratmaq (Yalnız Admin)
* `DELETE /api/services/<id>` - Xidməti silmək (Yalnız Admin)
