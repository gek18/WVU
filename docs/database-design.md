# Veritabanı Tasarımı — Proje 14

## ER Diyagramı

```mermaid
erDiagram
    USERS ||--o{ ROOM_ASSIGNMENTS : receives
    ROOMS ||--o{ ROOM_ASSIGNMENTS : hosts
    USERS ||--o{ ROOM_ASSIGNMENTS : assigns
    USERS ||--o{ ISSUES : reports
    ROOMS ||--o{ ISSUES : contains
    USERS o|--o{ ISSUES : handles
    ISSUES ||--o{ ISSUE_STATUS_HISTORY : records
    USERS o|--o{ ISSUE_STATUS_HISTORY : changes
    ISSUES ||--o| ISSUE_RATINGS : receives
    USERS ||--o{ ISSUE_RATINGS : is_rated
    USERS ||--o{ TECHNICIAN_SKILLS : has
    MAINTENANCE_SKILLS ||--o{ TECHNICIAN_SKILLS : maps

    USERS {
        int id PK
        string name
        string email UK
        string password_hash
        string role
    }
    ROOMS {
        int id PK
        string building
        string number
        int floor
        int capacity
        bool is_active
    }
    ROOM_ASSIGNMENTS {
        int id PK
        int student_id FK
        int room_id FK
        date start_date
        date end_date
        int assigned_by_id FK
    }
    MAINTENANCE_SKILLS {
        int id PK
        string name UK
    }
    TECHNICIAN_SKILLS {
        int technician_id PK,FK
        int skill_id PK,FK
    }
    ISSUES {
        int id PK
        int student_id FK
        int room_id FK
        int technician_id FK
        string title
        text description
        string status
        datetime created_at
        int resolution_minutes
    }
    ISSUE_STATUS_HISTORY {
        int id PK
        int issue_id FK
        int changed_by_id FK
        string from_status
        string to_status
        datetime created_at
    }
    ISSUE_RATINGS {
        int issue_id PK,FK
        int technician_id FK
        int stars
        string comment
        datetime created_at
    }
```

`users` tablosu üç rolü de saklar. `room_assignments` önceki oda atamalarını korur; kısmi benzersiz indeks her öğrenci için en fazla bir etkin atama olmasını sağlar. Atama sırasında odanın kapasitesi kontrol edilir. `technician_skills`, teknisyenler ile bakım uzmanlıkları arasındaki N:N ilişkisini çözer. `issue_status_history`, her durum değişikliğini ayrı kaydeder.

## İlişkiler ve kardinaliteler

- Öğrenci 1:N OdaAtaması; Oda 1:N OdaAtaması. Atama geçmişi öğrenci-oda ilişkisini dönemler boyunca korur.
- Öğrenci 1:N Arıza; Oda 1:N Arıza; Teknisyen 1:N Arıza (atama öncesinde teknisyen boş olabilir).
- Arıza 1:N DurumGeçmişi; Kullanıcı 1:N DurumGeçmişi (silinmiş hesaplarda işlem yapan kullanıcı boş olabilir).
- Teknisyen N:N BakımUzmanlığı; ara tablo `technician_skills`.

## 3NF normalizasyon gerekçesi

- **1NF:** Her alan tek bir değer taşır. Tekrarlanan durum değişiklikleri, teknisyen uzmanlıkları ve oda atama geçmişi ayrı satır ve tablolarda tutulur.
- **2NF:** Anahtar olmayan alanlar anahtarın tamamına bağlıdır. `technician_skills` birleşik anahtarı `(technician_id, skill_id)` kullanır ve anahtar dışı alan içermez. Diğer tablolarda tek sütunlu birincil anahtar vardır.
- **3NF:** Oda bilgileri yalnızca `rooms` tablosunda; kullanıcı ve rol bilgileri `users` tablosunda; uzmanlık adı `maintenance_skills` tablosunda tutulur. Arıza geçmişi `issues` tablosunda yinelenmez. Anahtar olmayan alanlar anahtara, anahtarın tamamına ve yalnızca anahtara bağlıdır.

`issue_ratings`, kapatılmış bir talep için öğrenci puanını ve değerlendirilen teknisyeni tek satırda tutar; `issue_id` birincil anahtarı her talebe en fazla bir değerlendirme bağlar. Böylece teknisyen sonradan değişse bile değerlendirme hangi teknisyene ait olduğunu korur. Puan 1–5 aralığındadır; yorum isteğe bağlıdır ve 1000 karakterle sınırlıdır.

Şemada sekiz ilişkili tablo, PK/FK'ler, benzersizlik ve kontrol kısıtları ile e-posta, yabancı anahtarlar ve arıza durumu/tarihi için indeksler kullanılır. ORM sorguları SQLAlchemy parametreli ifade API'si üzerinden çalışır.
