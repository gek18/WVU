# Proje 14 — İlerleme ve Rubrik Değerlendirmesi

Bu belge, `akış.pdf` içindeki Proje 14 tanımı, genel asgari proje koşulları ve 100 puanlık rubrik karşılaştırılarak hazırlanmıştır. Değerlendirme, depodaki kod ve dokümanlarda görülebilen kanıtlara dayanır; ders teslimi, canlı sunum ve sözlü savunma gibi repo dışı çalışmalar doğrulanamaz.

## Kısa özet

- **Genel rubrik:** 23 ölçütün **17'si doğrulanabilir biçimde tamam**, **2'si kısmen tamam**, **4'ü henüz kanıtlanmamış**.
- **Ağırlıklı ilerleme tahmini:** **77/100 (%77)**. Kısmi puan varsayımları aşağıda belirtilmiştir; bu resmi ders notu değildir.
- **Genel asgari koşullar:** **10 koşulun 8'i tamam**, 1'i kısmi, 1'i bekliyor.
- **Proje 14'ün sekiz işlevi:** 7'si tamam, 1'i kısmi. Ek teknisyen puanlama işlevi de tamam.

## Genel rubrik (100 puan)

| Aşama | Ölçüt | Puan | Durum | Kanıt / not |
|---|---|---:|---|---|
| 1 — Konu ve kapsam | Konunun açıklığı ve özgünlüğü | 2/2 | Tamam | Proje 14'e uygun yurt bakım yönetimi uygulaması ve üç rol mevcut. |
| 1 — Konu ve kapsam | Gerçekçi ve ölçülebilir kapsam | 2/2 | Tamam | Özellikler ve iş akışları README'de tanımlı. |
| 1 — Konu ve kapsam | Yazılı bildirimin zamanında ve eksiksiz teslimi | 0/1 | Kanıtlanamadı | Depoda teslim tarihi veya ders platformu kanıtı yok. |
| 2 — Veritabanı | ER diyagramının doğruluğu | 5/5 | Tamam | `docs/database-design.md` ilişkili varlıkları ve kardinaliteleri gösteriyor. |
| 2 — Veritabanı | 3NF normalizasyonu | 4/4 | Tamam | Aynı dokümanda 1NF, 2NF ve 3NF gerekçeleri yazılı. |
| 2 — Veritabanı | PostgreSQL'de çalışan PK/FK/kısıtlı şema | 2/4 | Kısmi | PostgreSQL sürücüsü ve `DATABASE_URL` desteği var; doğrulanan yerel kurulum SQLite. PostgreSQL üzerinde migration çalıştırıldığı kanıtlanmadı. |
| 2 — Veritabanı | Tasarım kararlarının yazılı açıklaması | 2/2 | Tamam | Atama geçmişi, N:N beceriler, indeks ve puanlama kararları belgelenmiş. |
| 3 — Backend CRUD | Ana varlıkların tamamında CRUD | 4/8 | Kısmi | Oda ve arıza kayıtlarında CRUD mevcut; üçüncü bir ana varlık için tam CRUD doğrulanmadı. |
| 3 — Backend CRUD | Güvenli, parametreli veritabanı erişimi | 5/5 | Tamam | SQLAlchemy ORM sorguları kullanılıyor; interpolasyonlu SQL tespit edilmedi. |
| 3 — Backend CRUD | Route, form ve hata yönetimi | 4/4 | Tamam | Doğrulama, rol kontrolleri ve hata yanıtları mevcut; iş akışı testleri geçiyor. |
| 3 — Backend CRUD | Kod düzeni ve okunabilirlik | 3/3 | Tamam | Flask blueprint'leri, modeller, şablonlar, testler ve dokümantasyon ayrılmış. |
| 4 — Kimlik ve güvenlik | Kayıt, giriş, çıkış ve oturum | 7/7 | Tamam | Ayrı rol girişleri ve oturum akışları test ediliyor. |
| 4 — Kimlik ve güvenlik | Rol tabanlı yetkilendirme | 5/5 | Tamam | Öğrenci, teknisyen ve yönetici yetkileri hem sayfa hem API testlerinde kontrol ediliyor. |
| 4 — Kimlik ve güvenlik | Parola hash'i | 4/4 | Tamam | Parolalar hash doğrulamasıyla saklanıyor. |
| 4 — Kimlik ve güvenlik | SQLi ve XSS önlemleri | 4/4 | Tamam | ORM parametreleri, şablon kaçışları, CSRF ve sunucu tarafı doğrulama kullanılıyor. |
| 5 — API ve ORM | Uygun HTTP yöntemleri ve durum kodları | 8/8 | Tamam | GET/POST/PATCH uçları ve hata kodları test ediliyor. |
| 5 — API ve ORM | ORM kullanımı | 6/6 | Tamam | Veri erişimi SQLAlchemy modelleri üzerinden yapılıyor. |
| 5 — API ve ORM | Transaction ve indeksler | 3/3 | Tamam | ORM transaction'ları ve şemadaki indeks/kısıtlar mevcut. |
| 5 — API ve ORM | API'nin test edilmesi | 3/3 | Tamam | Yetki, doğrulama, oluşturma ve durum geçişi API testleri mevcut. |
| 6 — Teslim ve sunum | HTTPS ile canlıya dağıtım | 0/6 | Bekliyor | Depoda dağıtılmış uygulama adresi veya HTTPS kanıtı yok. |
| 6 — Teslim ve sunum | 12–15 dakikalık demo | 0/6 | Kanıtlanamadı | Repo dışı sunum henüz doğrulanmadı. |
| 6 — Teslim ve sunum | README, commit geçmişi ve yapı | 4/4 | Tamam | README, migration geçmişi, testler ve düzenli proje yapısı mevcut. |
| 6 — Teslim ve sunum | Sözlü savunma | 0/4 | Kanıtlanamadı | Bu ölçüt repo üzerinden değerlendirilemez. |

**Ağırlıklı hesap:** 4/5 + 13/15 + 16/20 + 20/20 + 20/20 + 4/20 = **77/100**. Kısmi puan varsayımları: PostgreSQL 2/4 ve üçüncü ana varlığın CRUD kapsamı 4/8. PostgreSQL ölçütünde SQLite beklentisiyle genel rubrikteki PostgreSQL şartı çelişiyor; öğretim elemanından teyit edilmesi gerekiyor.

## Proje 14'ün özellikleri

| Proje 14 işlevi | Durum | Açıklama |
|---|---|---|
| Öğrenciye oda atama ve doluluğu izleme | Tamam | Oda kapasitesi, etkin atama ve atama geçmişi yönetiliyor. |
| Fotoğraflı bakım talebi açma | Tamam | JPG/PNG/WEBP yükleme ve boyut sınırı var. |
| Talep durum akışı | Tamam | Açık → atanmış → işlemde → kapalı; her değişiklik geçmişe yazılıyor. |
| Yöneticinin uygun teknisyeni ataması | Tamam | Uzmanlığa göre atama yapılabiliyor. |
| Yalnız atanmış teknisyenin durumu güncellemesi | Tamam | Yetki kontrolleri sayfa/API akışlarında test ediliyor. |
| Odaya göre arıza geçmişini görüntüleme | Kısmi | Talepler oda ile ilişkili ve listelerde oda gösteriliyor; ayrı oda geçmişi görünümü teyit edilmedi. |
| Teknisyen iş yükü ve performans raporu | Tamam | Atama, kapatma ve ortalama çözüm süresi raporlanıyor. |
| Ortalama çözüm süresi istatistiği | Tamam | Kapanan taleplerin çözüm süresi hesaplanıyor. |
| Ek puan: kapanıştan sonra teknisyeni değerlendirme | Tamam | Öğrenci, atanmış teknisyen için 1–5 yıldız ve isteğe bağlı yorum bırakabiliyor. |

## Genel asgari koşullar

| Koşul | Durum |
|---|---|
| En az 3 ilişkili tablo (tercihen 5+) | Tamam — şemada 8 ilişkili tablo var. |
| En az bir 1:N ve bir N:N ilişki | Tamam — ör. oda-talep 1:N ve teknisyen-beceri N:N. |
| ERD ve 3NF açıklaması | Tamam — `docs/database-design.md`. |
| Kayıt, giriş, çıkış | Tamam — rol bazlı akışlar mevcut ve testli. |
| En az iki rol | Tamam — üç rol ve yetkilendirme mevcut. |
| En az üç varlıkta tam CRUD | Kısmi — oda ve arızada doğrulandı; üçüncü varlık eksik. |
| REST API | Tamam — uçlar, yetki ve doğrulama mevcut. |
| Sunucu doğrulaması, hash, ORM ve SQLi/XSS temelleri | Tamam. |
| JOIN ve GROUP BY ile anlamlı rapor | Tamam — teknisyen iş yükü, çözümler ve puan özeti. |
| Dağıtım ve canlı demo | Bekliyor — canlı dağıtım henüz kanıtlanmadı. |

## İlerlemeyi artıracak işler

1. Öğretim elemanından SQLite/PostgreSQL beklentisini netleştirip istenen veritabanında migration ve akış testlerini çalıştırmak.
2. Oda detayında odaya bağlı arıza geçmişi görünümü eklemek.
3. Üçüncü ana varlık için tam CRUD akışını tamamlamak.
4. HTTPS dağıtımı hazırlamak ve demo/savunma kanıtlarını teslim dosyalarına eklemek.
