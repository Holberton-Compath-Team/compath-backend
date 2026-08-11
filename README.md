# 🚀 COMPATH - Backend API

COMPATH layihəsinin tələbə müraciətləri və autentifikasiya sistemini idarə edən Flask (Python) və MySQL əsaslı Backend API xidməti.

---

## 🛠 Texnologiya Steki

* **Language:** Python 3.x
* **Framework:** Flask
* **Database:** MySQL (XAMPP)
* **Authentication:** JWT (JSON Web Token) & Passwords Hashing (`werkzeug.security`)
* **Documentation:** Swagger UI (OpenAPI 3.0)
* **CORS:** Flask-CORS

---

## 📌 Sprint 2 Yenilikləri (Core Features Integration)

* 🔒 **JWT Autentifikasiyası:** Login olan istifadəçilərə 24 saatlıq Token verilir və qorunan API-lərə müraciət bu tokenlə təmin edilir.
* 📋 **Tickets CRUD API:** Tələbələrin yeni müraciət yaratması, öz müraciətlərini görməsi, statusun yenilənməsi və silinməsi dəstəklənir.
* 🛡 **Error Handling & Validasiya:** Giriş məlumatlarının tamlığı yoxlanılır, uyğun HTTP status kodları (400, 401, 404, 409) ilə xətalar idarə olunur.
* 📚 **Swagger Sənədləşməsi:** Bütün Auth və Tickets endpoint-ləri Swagger UI sənədləşməsinə inteqrasiya edilib.

---

## 🔗 API Endpoint-ləri

### Auth (Açıq API-lər)
* `POST /api/signup` - Yeni istifadəçi qeydiyyatı
* `POST /api/login` - Giriş və JWT Token alması

### Tickets (Qorunan API-lər - Bearer Token Tələb Olunur 🔒)
* `POST /api/tickets` - Yeni müraciət yaratmaq (Create)
* `GET /api/tickets` - İstifadəçinin öz müraciətlərinə baxması (Read)
* `PUT /api/tickets/<ticket_id>` - Müraciət statusunun yenilənməsi (Update)
* `DELETE /api/tickets/<ticket_id>` - Müraciətin silinməsi (Delete)

---

## 🚀 Lokal Mühitdə İşə Salmaq

### 1. Repozitoriyanı klonlayın
```bash
git clone https://github.com/Holberton-Compath-Team/compath-backend.git
cd compath-backend
```

### 2. Virtual Mühiti (venv) aktivləşdirin və Asılılıqları (Dependencies) Yükləyin
```bash
python -m venv venv
# Windows üçün:
venv\Scripts\activate
# Mac/Linux üçün:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Mühit Dəyişənlərini (`.env`) Qurun
Kök qovluqda `.env` faylı yaradın və bu məlumatları əlavə edin:
```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=
DB_NAME=compath_db
JWT_SECRET_KEY=CompathKey2026
```

### 4. Verilənlər Bazası (MySQL)
XAMPP-da `compath_db` bazasını yaradın və aşağıdakı cədvəlləri icra edin:

```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fullname VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tickets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    department VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'Gözləmədə',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### 5. Serveri İşə Salın
```bash
python app.py
```
Server `[http://127.0.0.1:5000](http://127.0.0.1:5000)` üzərində işə düşəcək.

---

## 📖 Swagger API Sənədləşməsi
Server işlək vəziyyətdə olarkən canlı API sənədləşməsini görmək üçün brauzerdə bu ünvana keçin:
👉 `[http://127.0.0.1:5000/api/docs](http://127.0.0.1:5000/api/docs)`
