# PracticaMIA 2.0 — Faz 4 · Tek uzman ajan ve konuşma motoru

**Yol haritası görevleri 31–40.** Serbest metinle çalışan ilk PracticaMIA ajanı niyeti belirler, Faz 3’teki resmî kataloğu sorgular, gerekiyorsa netleştirir ve kaynağa bağlı bir sonraki adımı gösterir. Kullanıcı geri döndüğünde işini ve bekleyen soruyu bulabilir.

**Önerilen temel.** Mevcut Python backend ve PostgreSQL üzerinde tek LangGraph ajanı. İlk dilim işlem bulma, kaynaklı açıklama ve sonraki adımı kapsar. Belge okuma, form hazırlama ve makbuzla takip sonraki fazlarda aynı ajana araç olarak bağlanır. Kullanılabilir yetenekleri doğrulanmış işlem kapsamı belirler.

## 31. Ajanın API ve arayüz sözleşmesini tanımla

- **31.1** Sohbet için `thread_id`, çalıştırma için `run_id`, dosya için isteğe bağlı `case_id` ve olay için artan sıra numarası kullan. Bir sohbetin birden fazla dosyaya bağlanabilmesini sağla.
- **31.2** Mesaj gönderme, durdurma, sonucu yeniden okuma ve bekleyen onaya yanıt verme isteklerini tiple. Aynı istemci mesaj kimliğiyle tekrar gönderilen isteği tanı.
- **31.3** Kullanıcıya açık olayları tanımla. `run.started`, `progress.updated`, `question.requested`, `approval.requested`, `answer.completed` ve `run.failed` önerilen olaylardır. Sağlayıcı ve grafik olaylarını uygulama sözleşmesine dönüştür.
- **31.4** Cevap kısa açıklama, varsa sonraki iş, resmî kanal, atıflar ve eksik bilgi içerebilsin. İşlem metniyle çalıştırılabilir eylemi ayrı alanlarda taşı.
- **31.5** Ağ bağlantısı koparsa son görülen olaydan devam et. Kullanıcı durdurursa devam eden çalışmanın ve önceden kaydedilmiş değişikliklerin durumunu açıklığa kavuştur.
- **31.6** İlerleme olaylarını hemen gönder. Kurum, ücret ve tarih gibi iddiaları doğrulandıktan sonra sun. [LangGraph streaming](https://docs.langchain.com/oss/python/langgraph/streaming)

**Kabul.** Frontend aynı API sözleşmesiyle cevap, soru, kaynak kartı, onay ve hata durumunu gösterebiliyor.

## 32. Tek LangGraph grafiğini kur

| Düğüm | Sonuç |
| --- | --- |
| Bağlamı yükle | Yetkili sohbet ve vaka bağlamı |
| Niyeti belirle | Niyet, aday işlemler ve bilinen bilgiler |
| İşlemi ve kanıtı bul | Uygulanabilir kurum, işlem, kaynak ve açık sorular |
| Sonraki adımı seç | Cevap, netleştirme, araç çağrısı veya öneri |
| Doğrula ve yanıtla | Kaynaklı cevap veya açık belirsizlik |

- **32.1** Düğümlere tipli girdi ve çıktı ver. Niyet düğümü kalıcı vaka durumuna doğrudan yazamasın.
- **32.2** Doğrudan cevap, eksik bilgi ve araç çağrısı için geçişleri tanımla. Araç sonucu cevap öncesi doğrulansın.
- **32.3** Modelin önerdiği rotayı işlem kapsamı, yetki, araç kullanılabilirliği ve girdi tamlığı açısından sunucuda kontrol et.
- **32.4** Arama, süre, araç ve model çağrısı bütçesi tanımla. Aynı sorgu tekrar ediyorsa mevcut sonucu veya doğrulayamama nedenini göstererek turu bitir.
- **32.5** İlk teknik dilimi çalıştır. Serbest metin → katalog → gerekiyorsa soru → kaynaklı sonraki adım. Yeni araç mevcut cevap yolunu bozmasın.

**Kabul.** Tek sohbet doğrudan cevap ve kullanıcı bilgisi bekleme durumlarını çalıştırır. Araç hatasında bir toparlanma yolu sunar.

## 33. Sohbet, vaka ve devam etme durumunu kur

- **33.1** Mesajlar, checkpoint’ler ve vaka kayıtlarını modelle. Mesaj konuşmayı, checkpoint yürütme durumunu, vaka doğrulanmış bilgiyi ve bekleyen işleri taşır. [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- **33.2** Ajan durumuna aktif vaka, adaylar, bilinen ve eksik alanlar, kaynaklar, bekleyen soru ve öneri kimliğini ekle. Büyük dosyaları yetkili referanslarla temsil et.
- **33.3** Tarayıcı kapanması, işlemci yeniden başlatma ve model kesintisinde son tutarlı noktadan devam et.
- **33.4** İlk sürümde sohbet başına tek aktif çalıştırma kullan. Ayrı sohbetler aynı vakayı düzenliyorsa revizyonla çakışmayı algıla.
- **33.5** Checkpoint’te hassas veri kullanımını azalt. Silme ve saklama süresi dolması için temizleme davranışını tanımla.
- **33.6** Uzun konuşmada ilgili son mesajları, doğrulanmış olguları ve açık işleri aktar. Konuşma özeti vaka kaydının üzerine yazamasın.

**Kabul.** Kullanıcı bekleyen soruya geri dönüyor. Tekrarlanan istek ikinci vaka, görev veya kayıt değişikliği oluşturmuyor.

## 34. Niyet, işlem ve yetkili kurum eşlemesini geliştir

- **34.1** Bilgi isteme, işlem bulma, yazıyı açıklama, form alanını anlama, vakayı sürdürme ve çoklu iş planlama niyetlerini tanımla.
- **34.2** Modelden tipli niyet, kurum ve yer ifadeleri, işlem adayları ve eksik bağlam al. Kayıt kimliklerini katalogda doğrula.
- **34.3** Gündelik ifade, resmî İtalyanca terim ve kısaltmaları Faz 3 aramasıyla eşle. Residenza ve domicilio gibi bağlama duyarlı ifadeleri test et.
- **34.4** Yer, tarih ve durumun adayları nasıl değiştirdiğini taşı. Kullanıcının fiziksel konumunu işlemin yetki alanı olarak varsayma.
- **34.5** Boş veya çelişkili sonuçta adayları açıklama, ayırt edici soru veya doğrulanmış kuruma yönlendirme arasından işe yarayan adımı seç.
- **34.6** İtalyanca, İngilizce, eksik cümle, yazım hatası, kısaltma ve birden fazla kurum adına karşı test et.

**Kabul.** Niyet tanıma ve resmî işlem seçimi ayrı ölçülebilir. Kurum doğrulanınca kesin yönlendirme sunulur.

## 35. Netleştirme ve kullanıcı düzeltme akışını kur

- **35.1** Sormadan önce mesaj, doğrulanmış vaka ve erişilebilir belge sonucunu kontrol et.
- **35.2** Sonucu değiştiren soruyu öne al. Mümkün olduğunda tek ayırt edici soru sor. Birlikte gereken alanların gerekçesini açıkla.
- **35.3** Sorunun kimliğini, yanıt biçimini ve etkilediği alanı kaydet. Serbest metin ve seçenekleri destekle. Geçersiz cevapta gereken bilgiyi açıkla.
- **35.4** Bilmiyorum, şimdilik geç ve konu değiştirme davranışlarını tanımla. Yapılabilen kısmı tamamla ve açık belirsizliği sakla.
- **35.5** Düzeltme gelince etkilenen aday, kanıt ve adımı yeniden değerlendir.
- **35.6** İki sekmeden yanıtlanan eski soru veya yanlış soru kimliğinde sessiz kayıt değişikliğini engelle.

**Kabul.** Kullanıcı doğrulanmış bilgiyi tekrarlamaz. Düzeltme ilgili kaynak ve sonraki adımı günceller.

## 36. Araçları tipli, yetkili ve tekrar güvenli çalıştır

| Araç | İlk işlev |
| --- | --- |
| İşlem ara | İşlem, kurum, yer ve kanal adayları |
| Kanıt ara | İncelenmiş ve uygulanabilir pasajlar |
| Kaynak detayı aç | Sürüm, resmî URL, kapsam ve konum |
| Vaka bağlamını oku | Yetkili bilgiler ve bekleyen işler |
| Vaka güncellemesi öner | Alan veya görev değişikliği taslağı |
| Onaylı güncellemeyi uygula | Geçerli onay ve revizyonla yazma |

- **36.1** Tipli girdi ve çıktı tanımla. Katalog kimliklerini doğrula ve tanımsız parametreleri reddet.
- **36.2** Etkin kullanıcı ve vaka sahipliğini sunucuda doğrula. Model çıktısını erişim kanıtı olarak kullanma.
- **36.3** Salt okunur araçlar ve yazmalar için yürütme koşullarını tanımla. Gerekli onayı sunucuda kontrol et.
- **36.4** Tekrar deneme, ağ kesintisi ve checkpoint dönüşlerinde idempotency anahtarı ve vaka revizyonu ile çift yazmayı önle.
- **36.5** Geçici katalog hatası, doğrulanmış sonuç yok ve geçersiz girdi için farklı toparlanma yolları kur.
- **36.6** Sonraki belge ve form araçlarının bağlanacağı sözleşmeyi tanımla. Kullanılabilirliği doğrulanmamış özellik tamamlanmış iş olarak görünmesin.

**Kabul.** Yetkisiz erişim, geçersiz çağrı ve tekrar yazma test edilir. Görünen durum gerçek işlemi yansıtır.

## 37. Kaynaklı cevap ve iddia doğrulamasını uygula

- **37.1** Kurum, kanal, zorunlu belge, ücret, son tarih, koşul ve form sürümü iddialarını kanıt kimliğine bağla.
- **37.2** O turda alınan veya güncelliği yeniden doğrulanan referansı kabul et. İşlem, yer, tarih ve koşulla uyumu kontrol et.
- **37.3** Pasajın iddiayı gerçekten desteklediğini değerlendir. Genel kurum bağlantısı sayfada yer almayan tarihe kanıt oluşturmaz.
- **37.4** Doğrulanamayan iddiayı çıkar ya da kapsamını daralt. Bilinen resmî kanalı ve eksik kanıtın doğrulama yolunu göster.
- **37.5** Kullanıcı belgesi, resmî kaynak ve ajan önerisinin dayanağını kullanıcı arayüzünde görünür tut.
- **37.6** Kaynak kartını Faz 3’ün tam pasajına bağla. Gerekli İtalyanca terimi koru ve kullanıcının dilinde açıkla.

**Kabul.** Kritik iddialardan geçerli ve erişilebilir pasaja gidilir. Başka belediye, geri çekilmiş kaynak ve eski sürüm vakaları doğrulanmış bilgi olarak gösterilemez.

## 38. Öneri, kullanıcı onayı ve devam akışını kur

- **38.1** Kullanıcının söylediği, belgeden çıkarılan ve kullanıcıca doğrulanan bilgiyi kökeniyle sakla.
- **38.2** Öneri kimliği, değişen alan, mevcut ve önerilen değer, gerekçe ve vaka revizyonunu göster.
- **38.3** Kabul, düzeltme, ret ve iptal davranışlarını uygula. Reddedilen değer uygulanmaz, düzeltilen değer gerektiğinde yeniden doğrulanır.
- **38.4** Vaka veya kaynak değiştiyse eski öneriyi yeniden kontrol et. Güncellik ve yetki doğrulanmadan yazma yapma.
- **38.5** LangGraph `interrupt()` ile bekle ve onayla aynı thread’de devam et. Düğüm yeniden çalışabileceği için kalıcı yazmayı onay sonrasındaki idempotent adımda gerçekleştir. [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- **38.6** Resmî aktarımda kanal ve yapılacak işi ver. Kullanıcı resmî giriş, imza, ödeme ve gönderimi ilgili kanalda tamamlar. Durum eldeki kanıta göre güncellenir.

**Kabul.** Yalnız gösterilip onaylanan değişiklik uygulanır. Tekrar gelen onay veya eski öneri yanlış yazma üretmez.

## 39. Aynı konuşmada birden fazla işi yönet

- **39.1** Mesajdaki hedefleri ayrı aday işlem ve eksik bağlamla tanımla.
- **39.2** Aktif işi göster. Kullanıcı öncelik vermediyse seçenekleri gösterip hangisiyle başlanacağını sor.
- **39.3** Sunucuda vaka seçimini doğrula. Öbür başvuru gibi ifadeler birden fazla kayda uyuyorsa netleştir.
- **39.4** Doğrulanmış ortak bilgiyi yeniden kullan. İşleme özel tarih, belge ve form alanını ilgili vakaya bağlı tut.
- **39.5** Bekleyen soru varken kullanıcı konu değiştirebilsin. Geri döndüğünde ilgili iş ve soru görünür kalsın.
- **39.6** Benzer adlı belgeler, farklı belediyeler ve iki bekleyen soru ile vakalar arası veri karışmasını test et.

**Kabul.** Kullanıcı aynı sohbetten iki işe geçip dönebilir. Atıflar, alanlar ve bekleyen işler doğru vakaya bağlı kalır.

## 40. Ajanı değerlendir ve Faz 4’ü kapat

- **40.1** Faz 2 vakalarını Faz 3’ün doğru kurum ve pasajlarıyla birleştir. Yanlış kurum, eksik yer, eski kaynak, düzeltme, çoklu iş ve devam vakalarını kapsa.
- **40.2** Niyet, işlem arama, kanıt, soru kalitesi ve yetkili araç çağrısını ayrı ölç. Hata kaynağı izlenebilir olsun.
- **40.3** Birincil metrik doğru sonraki adıma yardımsız ulaşmadır. Doğru kurum, desteklenen atıf, gereksiz soru ve düzeltilmeyen yönlendirmeleri izle.
- **40.4** Katalog kesintisi, model zaman aşımı, çift mesaj ve onay sırasında kapanmayı canlandır.
- **40.5** İlk görünür olay, doğrulanmış cevap süresi, çağrı sayısı ve vaka başına maliyeti ölç. Hedefleri pilot ölçümlerine göre belirle.
- **40.6** Hatanın niyet, sorgu, araç ve kaynak sürümüyle ilişkisini kaydet. Gereksiz konuşma ve belge içeriğinin izleme sistemine taşınmadığını doğrula.
- **40.7** Faz 5’e mesaj API’si, olaylar, atıf, soru, onay ve yeniden bağlanma örneklerini teslim et.

**Kabul.** En az üç kurumlu pilot setinde doğru kurum, uygulanabilir resmî kaynak ve somut sonraki adım bulunur. Ajan eksik ve çelişkili bilgide netleştirir. Kullanıcı kapatıp döndüğünde aynı işi sürdürebilir.

## Kapanış senaryosu

Kullanıcı kurumu bilmeden ihtiyacını yazar. Ajan işi ve kaynağı bulur, gerekirse bir soru sorar. Kullanıcı bilgisini düzeltince ilgili sonuçlar yeniden değerlendirilir. Ajan işi, yetkili kanalı ve dayanak pasajı gösterir. Kullanıcı işi kaydedip sohbeti kapatır ve sonra aynı adımdan devam eder.
