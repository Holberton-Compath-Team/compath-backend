# COMPATH — Student Portal (Backend)

COMPATH tələbə problemlərini avtomatik doğru universitet xidmətinə yönləndirən platformadır. Bu repo layihənin yalnız **Backend** (Server, API və Verilənlər Bazası) hissəsini əhatə edir.

**Texnologiyalar:** Python, Flask, MySQL, Flask-CORS, JWT/Hash

---

## 🚀 Başlamaq Üçün Təlimatlar

Kodu öz kompüterinizdə işə salmaq üçün aşağıdakı addımları izləyin:

### 1. Reponu Klonlayın və Mühiti Qurun
```bash
git clone <sizin-repo-linkiniz>
cd compath-backend
python -m venv venv
venv\Scripts\activate      # Windows üçün
pip install -r requirements.txt
```

### 2. Məxfi Məlumatları (.env) Təyin Edin
Layihənin ana qovluğunda yeni bir `.env` faylı yaradın və aşağıdakıları öz MySQL məlumatlarınıza uyğun doldurun (şifrəniz yoxdursa boş saxlayın):
```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=
DB_NAME=compath_db
```

### 3. Verilənlər Bazasını Qurun
XAMPP (və ya başqa MySQL serveri) işə salın, `compath_db` adlı baza yaradın və bu SQL kodunu işlədərək cədvəli qurun:
```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fullname VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password VARCHAR(200) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4. Serveri İşə Salın
```bash
python app.py
```
Server `http://127.0.0.1:5000` ünvanında işə düşəcək.

---

## 📡 API Endpoint-lər
*Backend komandası yaxın zamanda bura Swagger/OpenAPI sənədləşdirməsi əlavə edəcək.*
- **POST `/api/signup`** - Yeni istifadəçi qeydiyyatı
- **POST `/api/login`** - Mövcud istifadəçi girişi
