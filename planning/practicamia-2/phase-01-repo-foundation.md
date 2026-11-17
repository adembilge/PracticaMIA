# PracticaMIA 2.0 — Faz 1: Repo temizliği ve yeniden kurulum

Bu fazın sonucu PracticaMIA 2.0 geliştirmesine başlanabilecek temiz bir repodur. Milano prototipinin ekranları, sabit kuralları ve önceki proje dokümantasyonu aktif kod tabanından çıkarılır. Yeniden kullanılabilir altyapı, doğrulanabilir resmî kaynak kayıtları ve güvenli test belgeleri incelenip korunur. Faz, temiz bir checkout’tan çalışan uygulama ve boş veritabanı kurulabildiğinde kapanır.

**Başlangıç envanteri.** Önceki repo taramasında 348 dosya ve 41 Markdown dosyası vardı. Eski 94 görevlik plan `AGENTS.md`, `docs/MASTER_PLAN.md`, `docs/TASKS.yaml` ve CI doğrulamasına bağlı. Uygulamaya başlarken envanteri güncelle. Temizlik kapsamı aktif kod tabanıdır. Önceki sürümün Git referansı geri dönüş ve karar geçmişi için saklanır.

## 1. Mevcut sürümü sabitle ve çalışma dalını aç

- **1.1** `main` commit’ini, açık PR’ları ve son başarılı frontend, backend ve tarayıcı testlerini kaydet. Açık PR’ların temizlenecek dosyalarla çakışıp çakışmadığını kontrol et.
- **1.2** Canlı web ve API dağıtım kimliklerini, bağlı alan adlarını ve veritabanı migration sürümünü kaydet. Ortam değişkenlerinin adlarını envantere al. Gizli değerleri repo ve PR dışında tut.
- **1.3** Başlangıç commit’ini `archive/practicamia-v1` gibi bir Git etiketiyle işaretle. Eski plan, kaynak kayıtları ve çalışan sürümün koduna bu referanstan ulaşılabilsin.
- **1.4** Sabitlenen commit’ten `rebuild/phase-01-repo-foundation` gibi bir çalışma dalı aç. Preview ve CI tetikleyicilerini incele ve testlerin koşacağı ayrı ortamı doğrula.

**Kabul ölçütü.** Eski kod sürümü, canlı dağıtımlar ve veritabanı sürümü ayrı ayrı tanımlanır. Temizlik dalının başlangıç commit’i bilinir.

## 2. Repoyu dosya ve bağımlılık düzeyinde incele

- **2.1** `frontend/`, `backend/`, `requirements/`, `audit/`, `evals/`, `scripts/`, `docs/` ve `.github/workflows/` için envanter çıkar. Her öğeye Sil, Koru, Taşı veya Test edip karar ver durumu ver.
- **2.2** Frontend’de sayfa rotalarını, API proxy’lerini, oturum kontrolünü, çeviri anahtarlarını ve paylaşılan bileşenleri eşleştir. Her eski ekranın hangi bileşenlere ve API’ye bağlı olduğunu çıkar.
- **2.3** Backend’de endpoint, servis, tablo, migration ve test bağımlılıklarını haritala. Milano’ya sabitlenen kurallarla ortak kullanılabilecek güvenlik ve veri erişimi parçalarını belirle.
- **2.4** CI, derleme komutları, deployment ayarları ve fixture’ların tükettiği yolları kontrol et. Üretim kodunca kullanılmayan dosyaları test ve derleme bağımlılıkları açısından da incele.

**Kabul ölçütü.** Her dosya grubu için çağıran kod, beklenen değişiklik etkisi ve doğrulama adımı bilinir.

## 3. Korunacak resmî belgeleri ve kanıtları ayır

| Malzeme | Faz 1 işlemi |
| --- | --- |
| Eski ürün planı, ilerleme raporu veya runbook | Aktif daldan çıkar |
| Resmî form, kamuya açık kılavuz veya kaynak kaydı | Kaynağı ve sürümü doğrulanabiliyorsa koru |
| İnceleme kararı veya resmî kaynak kanıtı | İlgili kaynak, sürüm ve kapsamla birlikte koru |
| Yapay PDF, fotoğraf veya OCR fixture’ı | Tekrarlanabilir bir testte kullanılıyorsa koru |
| Kullanıcı belgesi veya kişisel veri içeren çıktı | Özel veri envanterine al, repo ağacının dışında tut |

- **3.1** Kaynak kayıtlarının ve belge kopyalarının repoya ek olarak veritabanı veya depolamada bulunup bulunmadığını kontrol et.
- **3.2** Korunacak kaynak için kurum, resmî URL, belge adı, kapsam, sürüm, varsa alınma tarihi ve inceleme durumunu kaydet. Dosya saklanıyorsa içerik parmak izini al.
- **3.3** Eski bir kaynağa verilmiş onayı yalnızca onaylandığı işlem ve yetki alanıyla birlikte taşı. Belirli bir Milano senaryosuna ait onayın geçerlilik kapsamı kayıt üzerinde görünsün.
- **3.4** Resmî kayıtlarla test fixture’larını ayrı konumlarda tut. Sentetik OCR metninin resmî kataloğa giremediğini doğrula.

**Kabul ölçütü.** Her korunmuş belgenin veya kaynak kaydının kökeni ve kullanım amacı izlenebilir. Bu kayıtlar eski dokümantasyon çıkarıldıktan sonra erişilebilir.

## 4. Eski dokümantasyonu ve roadmap otomasyonunu kaldır

- **4.1** `docs/` içindeki eski plan, ilerleme raporu, uygulama kılavuzu ve pilot raporlarını aktif daldan çıkar. Kökteki `PracticaMIA_Complete_Project_Specification.md` ile eski frontend ve backend dokümanlarını envantere göre kaldır.
- **4.2** `docs/TASKS.yaml`, `scripts/validate_roadmap.py`, script testleri ve `.github/workflows/roadmap-governance.yml` dosyalarını aynı değişiklik grubunda ele al. Silinen scriptleri çağıran işleri de temizle.
- **4.3** Eski CI kontrolünün dal korumasında zorunlu olup olmadığını doğrula. Zorunluysa yeni kontrolü çalıştır ve başarıyı gördükten sonra eski referansı değiştir.
- **4.4** Eski `AGENTS.md` yerine kısa bir çalışma kılavuzu oluştur. Yeni `README.md` ürün amacı, repo yapısı ve kurulum komutlarını içersin. Yüz görevlik plan için bir güncel ana dosya kullan.
- **4.5** `MASTER_PLAN.md`, `TASKS.yaml`, `validate_roadmap` ve eski spesifikasyon başvurularını ara. CI, import, script, uygulama metni ve Markdown bağlantılarındaki kalıntıları gider.

**Kabul ölçütü.** Aktif dal eski plana başvurmadan kurulup derlenir ve test edilir. Yeni dokümantasyonun başlangıç noktası açıktır.

## 5. Milano prototipini uygulama kodundan çıkar

- **5.1** Eski Start a case, kurgu senaryolar, sabit Yes/No süreci ve hazırlık PDF’i için sayfa → bileşen → proxy → backend → veri zincirini çıkar.
- **5.2** Yalnız eski akışa ait menü, bağlantı, yönlendirme, çeviri ve görsel varlıkları kaldır. Geçiş için gerekli eski URL’leri belirle ve ilgili yeni girişe yönlendir.
- **5.3** Sabit Milano soru setini, varsayılan prosedürü, senaryoya bağlı checklist’i ve kurgu paket üretimini ayır. Genel kullanım için doğrulanabilecek belge işlevlerini görev 6’da değerlendir.
- **5.4** Eski akışa özel testleri çıkar. Hesap izolasyonu, dosya güvenliği ve kaynak doğrulama testlerini koru veya bağımsız giriş noktalarına taşı.
- **5.5** Kod kaldırmanın mevcut kayıtlar üzerindeki etkisini incele. Uygulama kodu temizliği ve veri silme işlemlerini ayrı değişiklikler olarak planla. Eski şemaya dönmek veya veriyi okumak için gereken migration geçmişini ayrıca değerlendir.

**Kabul ölçütü.** Yeni uygulamanın açılması, oturum ve temel sayfa için eski Milano senaryosuna, demo durumuna veya PDF üretim zincirine ihtiyaç kalmaz.

## 6. Yeniden kullanılabilir altyapıyı seç ve test et

- **6.1** Oturum doğrulama, kullanıcıya ait kayıtların sahipliği, PostgreSQL bağlantısı, kaynak erişim izinleri ve CI kurulumunu incele. Kullanılan şema ve ortam değişkenlerini kaydet.
- **6.2** Bağımsızlık ölçütü belirle. Eski prosedür adı, şehir, demo bayrağı veya durum modeline bağlı bileşenlerin ayrıştırma maliyetini değerlendir.
- **6.3** Korunan her bileşenin sözleşme testini ekle veya taşı. Oturumda geçerli, süresi dolan ve yetkisiz durumları, kayıt erişiminde iki farklı hesabı test et.
- **6.4** Taşınan bileşenlerin en küçük bağımlılık kümesini belirle. Kullanılmayan paketleri, ayarları ve yardımcı scriptleri çıkar. Paket kilitlerini temiz kurulumla doğrula.
- **6.5** Dosya yükleme, OCR ve PDF araçlarını envantere al ve kullanılabilirliğini belirle. Kullanıcıya dönük işleme yeteneklerini ilgili sonraki fazlarda devreye al.

**Kabul ölçütü.** Taşınan her parçanın yeni amacı ve çalışan testi var. Genel altyapı eski demo verisine bağlı çalışmaz.

## 7. Yeni repo iskeletini oluştur

- **7.1** Mevcut `frontend/` ve `backend/` köklerini kullan. Frontend’de sohbetin açılacağı tek uygulama kabuğunu oluştur. Kaynaklar, belgeler ve formlar sonraki fazlarda bu kabuğa eklenecek.
- **7.2** Backend’de giriş noktası, doğrulanmış yapılandırma, API sürümleme, hata biçimi ve sağlık kontrolü kur. İşlem kataloğu, vakalar, belgeler ve ajan araçları için modül sınırlarını tanımla.
- **7.3** Frontend–backend API sözleşmesinin ilk parçasını oluştur. Sağlık isteğinin başarı ve hata yanıtlarını test et.
- **7.4** Kurulum ve test örneklerini çalışır hale getir. Kaynak verileri, fixture’lar ve migration dosyaları için anlaşılır dizin düzeni kullan. Dizinleri ilk dosyayla birlikte ekle.

**Kabul ölçütü.** Bir web uygulaması ve bir backend çalışıyor. Tarayıcıdan backend’e gerçek bir sağlık isteği yapılabiliyor.

## 8. Ortam ve veritabanı kurulumunu tekrarlanabilir yap

- **8.1** Yerel geliştirme, CI, preview ve canlı ortam için veritabanı, kimlik sağlayıcı ve depolama hedeflerini belirle. Kritik ayar yanlış veya eksikse anlaşılır hata ver.
- **8.2** `.env.example` dosyalarını gerekli anahtar adları ve güvenli örneklerle güncelle. Gerçek kimlik ve test hesabı bilgilerini ortamın gizli değişkenlerinde tut.
- **8.3** Yeni geliştirme şemasını boş veritabanına kur. Önceki migration zincirini sürdürmekle ayrı bir 2.0 şeması kullanmak arasındaki kararı, eski veriyi okuma ve geri dönüş gerekçesiyle kaydet.
- **8.4** Migration ve test verisi hazırlama komutlarını ayır. Test verisi yüklemesinin canlı hedefi reddettiğini ve yeniden çalıştırılınca kopya kayıt oluşturmadığını test et.
- **8.5** Temiz checkout’tan bağımlılık kurulumu, ortam ayarı, migration, test verisi ve ilk çalıştırma adımlarını `README.md` üzerinden doğrula. İkinci kurulumda yerel ayar kalıntısı gerekmediğini göster.

**Kabul ölçütü.** Boş test ortamı sıfırdan kurulabilir. Kurulum için eski Milano vakası veya canlı gizli değer gerekmez.

## 9. CI kontrollerini yeni repo temeline bağla

- **9.1** Frontend CI’da paket kurulumu, tip kontrolü, test ve üretim derlemesini çalıştır. Yeni ana sayfayı ve sağlık bağlantısını HTTP üzerinden doğrula.
- **9.2** Backend CI’da boş PostgreSQL’e migration, API sağlığı ve korunan oturum ve erişim testlerini çalıştır.
- **9.3** Eski dosya yolları, kırık repo içi bağlantılar, kaldırılmış rotalara giden istekler ve gizli bilgi kalıntıları için tarama yap. Sonuçları PR’a yaz.
- **9.4** Uygulama kabuğu, doğru giriş hedefi ve backend erişilemediğinde görülen durum için küçük tarayıcı doğrulaması ekle.
- **9.5** Yeni CI işlerini dal kontrolleriyle eşleştir. Bir hata olduğunda derleme, migration, yetki, test veya dağıtım adımı ayırt edilebilsin.

**Kabul ölçütü.** Yeni dalın CI doğrulaması temiz kurulumdan geçer. Eski roadmap ve demo akışına bağımlılık kalmaz.

## 10. Temizlik PR’ını tamamla ve Faz 1’i kapat

- **10.1** PR’a kaldırılan bileşenleri, taşınan kaynak kayıtlarını, kullanılan altyapıyı ve önceki sürümün Git referansını ekle.
- **10.2** Başlangıç commit’ine göre farkı incele. Kaynak kayıtları, dal koruması ve ortam hedeflerini yeniden doğrula.
- **10.3** Temiz checkout, boş veritabanı migration’ı, frontend derlemesi, backend testi, tarayıcı kontrolü ve preview sağlık sonuçlarını PR’a bağla.
- **10.4** Doğrulanan temizlik PR’ını birleştir ve `main` sonuçlarını kontrol et. Faz 2’nin repo yapısını, komutlarını ve başlangıç commit’ini sabitle.

| Kapanış kontrolü | Beklenen kanıt |
| --- | --- |
| Eski dokümantasyon ve otomasyon temiz | Eski plana bağlı dosya, CI işi ve referans kalmamış |
| Resmî belgeler ve kanıtlar korunmuş | Kayıtlar kurum, kaynak, sürüm ve kullanım kapsamıyla bulunabiliyor |
| Eski Milano akışı kaldırılmış | Yeni uygulama demo sayfası, sabit soru seti veya eski PDF akışına bağlı değil |
| Yeni temel çalışıyor | Temiz checkout, boş veritabanı, açılan web uygulaması ve başarılı API sağlık kontrolü |
| Geri dönüş noktası mevcut | Önceki Git sürümü, dağıtım kimlikleri ve şema sürümü kayıtlı |

**Uygulama sırası.** Önce 1 → 2 → 3. Ardından dokümantasyon ve prototip temizliği, taşınacak bileşenlerin doğrulanması, yeni iskelet ve CI. Faz 2, temiz kurulum ve CI sonuçları `main` üzerinde doğrulandıktan sonra başlar.
