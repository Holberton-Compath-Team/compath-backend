# 🎯 COMPATH Helpdesk — Backend API

**COMPATH Helpdesk** tələbə və istifadəçi müraciətlərinin (ticket), anonim şikayətlərin, xidmət kataloqunun və daxili mesajlaşmanın idarə edilməsi üçün hazırlanmış RESTful Backend API sistemidir.

🌐 **Canlı API (Base URL):** `https://compath-api.onrender.com`  
📚 **Swagger Sənədləşməsi:** `https://compath-api.onrender.com/api/docs`

---

## 🛠️ Texnologiya Steki

* **Dil & Freymvork:** Python 3, Flask
* **Verilənlər Bazası:** Firebase Firestore (NoSQL)
* **Autentifikasiya:** JWT (JSON Web Tokens) & Werkzeug Password Hashing
* **Fayl Yaddaşı:** Daxili Statik Fayl Servisi (`/api/upload`)
* **Sənədləşmə:** Swagger UI (`flask-swagger-ui`)
* **Hosting:** Render

---

## ✨ Əsas Xüsusiyyətlər

* **Vahid Data Standartı (`camelCase`):** Bütün endpoint-lər (`createdAt`, `updatedAt`, `userId`, `authorName`, `trackingCode`, `attachedFiles`, `priority`) vahid `camelCase` formatında cavab qaytarır.
* **Anonim Müraciət & İzləmə (Tracking):** Qeydiyyatsız istifadəçilər müraciət yarada bilər və sistem tərəfindən verilən unikal `CP-XXXXXX` kodu ilə müraciətin statusunu izləyə bilər.
* **Prioritet İdarəetməsi:** `"Aşağı"`, `"Orta"`, `"Yüksək"`, `"Təcili"` prioritet səviyyələri (boş göndərildikdə avtomatik `"Orta"` təyin olunur).
* **Kartsız/Birbaşa Fayl Yükləmə:** Xarici storage-dən asılı olmadan birbaşa `/api/upload` üzərindən şəkil və sənəd yükləmə imkanı.

---

## 📌 API Endpoint-ləri

### 1. Autentifikasiya
| Metod | Endpoint | Təsvir | Auth |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/signup` | Yeni istifadəçi qeydiyyatı (`fullname`, `email`, `password`) | Xeyr |
| `POST` | `/api/login` | Sistemə giriş və JWT token əldə edilməsi | Xeyr |

### 2. Fayl Yükləmə (Upload)
| Metod | Endpoint | Təsvir | Auth |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/upload` | `FormData` (`file` key-i) ilə fayl yükləyir və birbaşa URL qaytarır | Xeyr |

### 3. Müraciətlər (Tickets) & İzləmə
| Metod | Endpoint | Təsvir | Auth |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/tickets` | Yeni müraciət yaratmaq (`title`, `description`, `department`, `priority`, `attachedFiles`) | Token |
| `GET` | `/api/tickets` | İstifadəçinin öz müraciətlərini əldə etmək | Token |
| `GET` | `/api/tickets/all` | Bütün müraciətləri gətirmək (Filter: `?status=`, `?department=`, `?priority=`, `?search=`) | Admin |
| `GET` | `/api/tickets/<id>` | Tək müraciətin detallarını gətirmək | Token |
| `PUT` | `/api/tickets/<id>` | Müraciətin `status` və ya `priority` dəyərini yeniləmək | Admin |
| `POST` | `/api/tickets/anonymous` | Token olmadan anonim müraciət yaratmaq (Qaytarır: `trackingCode`) | Xeyr |
| `GET` | `/api/track/<code>` | `CP-XXXXXX` izləmə kodu ilə müraciət detallarını və mesajlarını görmək | Xeyr |

### 4. Çat / Mesajlaşma
| Metod | Endpoint | Təsvir | Auth |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/tickets/<id>/messages` | Müraciət daxilinə yeni mesaj və ya fayl (`text`, `attachedFiles`) göndərmək | Token |
| `GET` | `/api/tickets/<id>/messages` | Müraciətə aid bütün mesaj tarixçəsini əldə etmək | Token |

### 5. Xidmət Kataloqu (Services)
| Metod | Endpoint | Təsvir | Auth |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/services` | Mövcud xidmətlərin siyahısını əldə etmək | Xeyr |
| `POST` | `/api/services` | Yeni xidmət əlavə etmək (`name`, `description`) | Admin |
| `DELETE` | `/api/services/<id>` | Xidməti silmək | Admin |

---

## 📦 Nümunə Data Strukturu (Ticket)

```json
{
  "id": "a1b2c3d4e5",
  "ticketId": "a1b2c3d4e5",
  "trackingCode": "CP-9F4A2C",
  "userId": "u987654321",
  "authorName": "Əli Məmmədov",
  "authorEmail": "ali@example.com",
  "title": "Təhsil haqqı arayışı",
  "description": "Maliyyə şöbəsindən arayış almaq istəyirəm.",
  "department": "Finance",
  "category": "Finance",
  "status": "pending",
  "priority": "Orta",
  "attachedFiles": [
    "[https://compath-api.onrender.com/static/uploads/8f9d2a1b.pdf](https://compath-api.onrender.com/static/uploads/8f9d2a1b.pdf)"
  ],
  "customFields": {
    "documentType": "Arayış",
    "educationType": "Əyani",
    "finCode": "7ABC123"
  },
  "createdAt": "2026-10-17 11:30:00",
  "updatedAt": "2026-10-17 11:30:00"
}
```

---

## 🚀 Lokal Quraşdırma (Local Setup)

1. Repozitoriyanı klonlayın:
   ```bash
   git clone <repo-url>
   cd compath-api
   ```
2. Virtual mühit yaradın və paketləri yükləyin:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Firebase Admin SDK JSON faylını layihənin kök qovluğuna əlavə edin.
4. Serveri işə salın:
   ```bash
   python app.py
   ```
   Server `http://localhost:5000` ünvanında işə düşəcək.
