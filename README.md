# YurtTakip — Öğrenci Yurdu Oda ve Bakım Talebi Yönetimi

Web Programlama ve Veritabanı Sistemleri dersi için hazırlanmış çok dilli bir web uygulaması. Öğrenci, teknisyen ve yönetici rolleri; oda yönetimi; bakım talepleri; teknisyen ataması; durum geçmişi ve performans raporlarını içerir. Arayüz Türkçe, İngilizce ve Arapça kullanılabilir; dil seçimi üst menüden yapılır ve Arapça görünüm RTL düzenine geçer.

## Gereksinimler

- Python 3.9 veya üzeri
- Varsayılan yerel veritabanı olarak Python ile gelen SQLite
- Geliştirme sırasında Bootstrap ve Inter yazı tipini CDN'den yüklemek için internet bağlantısı

> Proje 14 açıklamasında SQLite, genel değerlendirme rubriğinde ise PostgreSQL belirtiliyor. Uygulama varsayılan olarak SQLite kullanır. Teslimden önce öğretim elemanınıza hangi veritabanının istendiğini sorun. Bağlantı `DATABASE_URL` ortam değişkeniyle değiştirilebilir.

## Windows'ta çalıştırma (PowerShell)

Proje klasöründe:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
flask --app run.py db init
flask --app run.py db migrate -m "initial schema"
flask --app run.py db upgrade
flask --app run.py create-manager
flask --app run.py run --debug
```

`db init` yalnızca ilk kurulumda bir kez çalıştırılır. Ardından `http://127.0.0.1:5000` adresini açın. Yönetici hesabıyla oturum açıp odaları ve teknisyenleri ekleyin. Sonra bir öğrenci hesabı oluşturup odaya atayın.

PowerShell sanal ortamı etkinleştirmeyi engellerse yalnızca mevcut terminal oturumu için şu komutu çalıştırıp etkinleştirme adımını tekrarlayın:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Roller ve işlevler

- **Öğrenci:** Hesap oluşturur, kendisine atanan odayı görür, fotoğraflı bakım talebi gönderir, yalnızca kendi taleplerini takip eder. Atanmamış açık talebi düzenleyebilir veya silebilir.
- **Yönetici:** Oda ekler, düzenler, siler (yalnızca geçmiş kaydı yoksa), öğrencilere oda atar, atamayı sonlandırır, teknisyen/yönetici hesapları açar, talepleri teknisyenlere yönlendirir ve raporları inceler.
- **Teknisyen:** Yalnızca kendisine atanan talepleri görüntüler; onarıma başlatır ve talebi kapatır.

Durum akışı: `open` → `assigned` → `in_progress` → `closed`. Her geçişte kullanıcı, zaman, önceki ve yeni durum kaydedilir. Görseller JPG/PNG/WEBP olmalı ve 5 MB sınırını aşmamalıdır.

## Veritabanı ve geçişler

Tablolar: `users`, `rooms`, `room_assignments`, `maintenance_skills`, `technician_skills`, `issues`, `issue_status_history`. ER diyagramı ve 3NF gerekçesi [`docs/database-design.md`](docs/database-design.md) dosyasındadır.

Şema modelinde değişiklik yaptıktan sonra:

```powershell
flask --app run.py db migrate -m "describe schema change"
flask --app run.py db upgrade
```

## REST API

API aynı oturum ve rol denetimlerini kullanır. CSRF koruması açıktır. Tarayıcı tabanlı JSON POST/PATCH istekleri `X-CSRFToken` başlığında HTML içindeki `<meta name="csrf-token">` değerini göndermelidir.

| Yöntem | Yol | Yetki |
|---|---|---|
| GET | `/api/issues` | Oturum açmış kullanıcı; sonuçlar role göre süzülür |
| GET | `/api/issues/<id>` | Talebin sahibi öğrenci, atanmış teknisyen veya yönetici |
| POST | `/api/issues` | Etkin oda ataması bulunan öğrenci |
| PATCH | `/api/issues/<id>/status` | Yalnızca o talebe atanmış teknisyen |
| GET | `/api/reports/technicians` | Yönetici |

POST örneği: `{"title":"Su sızıntısı","description":"Lavabonun altında bu sabahtan beri su sızıyor."}`. PATCH örneği: `{"status":"in_progress"}`. API JSON hata metinleri oturum diline göre çevrilir; makine tarafından kullanılan alan adları, durum kodları ve durum değerleri sabit kalır.

## PostgreSQL (öğretim elemanı isterse)

PostgreSQL'i kurun ve `dorm_maintenance` veritabanını oluşturun. `.env` içine bağlantı adresini yazın:

```text
DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/dorm_maintenance
```

İlk kurulumda veritabanını seçtikten sonra `db init`, `db migrate` ve `db upgrade` adımlarını çalıştırın. `.env` dosyasını veya veritabanı dosyasını Git'e eklemeyin.

## Dağıtım notları

- Dağıtım ortamında `SECRET_KEY` değerini uzun ve rastgele bir ortam değişkeniyle değiştirin.
- Üretimde `--debug` kullanmayın; HTTPS ve uygun bir WSGI sunucusu kullanın.
- Oturum çerezlerinin güvenliğini ve veritabanı ayarlarını barındırma ortamınıza göre yapılandırın.

## Testler

Proje kök klasöründe sanal ortam etkin durumdayken tüm birim ve entegrasyon testlerini çalıştırın:

```powershell
python -m unittest discover -v
```

Testler, geçici SQLite veritabanı kullanarak oturum açma, rol yetkileri, oda atamaları, fotoğraflı talepler, teknisyen iş akışı, rapor API'si ve CSRF korumasını denetler.
