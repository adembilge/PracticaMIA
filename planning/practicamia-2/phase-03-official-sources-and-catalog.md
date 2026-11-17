# PracticaMIA 2.0 — Faz 3 · Resmî kaynaklar ve İtalya işlem kataloğu

**Yol haritası görevleri 21–30.** Kullanıcı “Bunu hangi kurum söylüyor, nerede geçerli ve nerede yazıyor?” diye sorduğunda PracticaMIA ilgili hizmeti, yetkili kurumu, uygulanabilir kaynak sürümünü ve dayanak pasajını gösterebilmeli. Faz 2’nin gerçek pilot vakaları ilk kapsamı belirler. Aynı katalog, Faz 4’te tek ajan ve kullanıcı arayüzü tarafından sorgulanır.

## 21. İşlem, kurum, kaynak ve kanıt veri modelini kur

| Kayıt | Tuttuğu bilgi |
| --- | --- |
| Kurum | Resmî ad, kurum kimliği, alternatif adlar, alan adları, bağlı birimler |
| Yetki alanı | İtalya, bölge, il, belediye veya kuruma özgü hizmet alanı |
| İşlem | Kullanıcının yaptığı iş, resmî İtalyanca ad, alternatif ifadeler, kurumlar |
| Hizmet kanalı | Portal, indirilebilir form, randevu, ofis veya resmî iletişim |
| Kaynak ve sürüm | Kalıcı kimlik, URL, yayımlayan kurum, gözlenen sürüm, inceleme |
| Kanıt parçası | Başlık, paragraf, tablo satırı veya PDF sayfası |
| Kural ve form referansı | Desteklenen koşul, belge gerekliliği veya form sürümü |

- **21.1** İşlem ile kurum ilişkisinde hizmeti yayımlayan ve başvuruyu alan kurum gibi rolleri kaydet.
- **21.2** Bir işlemin birden fazla geçerli kanalını ve her kanalın kapsamını kaydet.
- **21.3** Kaynak kimliğini sürümden ayır. Aynı URL’de içerik değişince yeni sürüm oluştur ve önceki vaka atıflarını koru.
- **21.4** Yayın veya güncelleme, gözlem ve yürürlük tarihlerini ayrı tut. Kaynak vermiyorsa ilgili alan boş kalabilsin.
- **21.5** Belirli iddiayı destekleyen kaynak bölümünü ilişkilendir. Örneğin form açıklaması, bir ücretin güncelliğini ayrı kanıt gerektirmeden desteklemez.
- **21.6** Faz 1’de korunan kayıtları taşıma kurallarını yaz. Onay kapsamı belirsizse yeniden incele.

**Kabul.** İşlem, birden fazla kurum rolü, yer ve kaynakla kaydedilebilir. Her iddiadan sürüm, pasaj ve inceleme kararına gidilebilir.

## 22. İtalya kurum ve coğrafya kimliklerini içe aktar

- **22.1** Kurumlar için [IPA](https://indicepa.gov.it/ipa-dati/dataset/amministrazioni), idari birimler için [ISTAT](https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/) kayıtlarını başlangıç girdisi al. Yayını, URL’yi ve alma zamanını kaydet.
- **22.2** Dış kimlik, katalog kimliği ve görünen adı ayrı tut. Ad değişince vaka bağlantıları korunabilsin.
- **22.3** Resmî ve eski ad, kısaltma, dil ve yazım varyantlarını eşle. Belirsizlik varsa adayları döndür ve ayırt edici konumu sor.
- **22.4** Kurumun adresini hizmet alanından ayır. Yer ve işlem farklı alanları işaret edebilir.
- **22.5** İçe aktarımı idempotent yap. Yeni, değişen, birleşen ve pasif kayıtları tespit et.
- **22.6** Aynı isimli yer, şehir ve il ayrımı, yeniden adlandırma ve birden fazla belediyeye hizmet veren kurum vakalarını test et.

**Kabul.** Açık bir isim kararlı biçimde aynı kimliğe bağlanır. Belirsiz eşleşmeler ilgili adayları verir.

## 23. Pilot işlemler için resmî kaynak kayıtlarını oluştur

- **23.1** Her pilot vaka için yanıtlanacak soruları yaz. Yetkili kurum, güncel form ve koşullu gereklilik örnektir.
- **23.2** Soruyu uygun kanıt türüne bağla. Kurum dizini kurum kimliğini, hizmet sayfası kanalı, form kendi alanlarını, talimat veya kural gerekliliği desteklesin.
- **23.3** Kaynak kaydına kurum, resmî URL, belge türü, dil, erişim, işlem, yer, varsa yeniden kullanım koşulu ve son inceleme tarihi ekle.
- **23.4** İşlem keşfi için [Single Digital Gateway](https://www.agid.gov.it/it/agenzia/attuazione-misure-pnrr/sportello-digitale-unico-single-digitale-gateway) ve benzeri dizinleri değerlendir. Belge, tarih ve ücret iddialarını ilgili kurum kanıtına bağla.
- **23.5** Vaka bazında kaynak açığını yaz. Kurum doğrulanmış, yerel form doğrulanamamışsa yönlendirme yeteneğini kaydet.
- **23.6** Bulunabilen işlemleri, doğrulanmış açıklamaları, kural kanıtlarını ve form sürümlerini ölç.

**Kabul.** Her pilot vaka için yetkili hizmet bulunuyor ya da doğrulamayı engelleyen kaynak açığı görünür.

## 24. HTML ve PDF kaynak alma hattını geliştir

- **24.1** Kaynak alma işini arka planda yürüt. URL, kaynak kimliği, deneme zamanı, sonuç ve hata kaydedilsin. Tek kaynak hatası diğer işleri durdurmasın.
- **24.2** HTTP kodu, yönlendirme, içerik türü, boyut, kodlama ve zaman aşımını işle. Başka alan adına geçişte hedefi doğrula.
- **24.3** Erişimi uygun kaynakları al. Oturum isteyen, otomasyonu engelleyen veya kullanımı belirsiz sayfayı incelemeye gönder. Uygun koşullarda elle kanıt eklenebilsin.
- **24.4** Ham içeriği ve temiz metni ayrı parmak izleriyle izle. Çerez bildirimi veya menü değişikliğinin asıl içeriğe etkisini ayırt et.
- **24.5** Aynı içerik için ikinci sürüm açma. Değişiklikte eski sürümü koruyup yenisini incelemeye al.
- **24.6** Boru hattını resmî kaynaklarla sınırla. Kullanıcı belgesi depolama ve işleme akışı Faz 6’ya aittir.
- **24.7** 404, geçici sunucu hatası, bozuk PDF, beklenmeyen dosya, yönlendirme döngüsü ve değişmemiş içerik durumlarını test et.

**Kabul.** Tekrarlanan içerik çoğalmaz. Değişen içerik inceleme kaydı üretir. Alma hatası önceki kanıtı değiştirmez.

## 25. Kaynak içeriğini atıf yapılabilir kanıta dönüştür

- **25.1** HTML’de başlıklar, paragraflar, listeler, tablo ve bağlantıları yapısal olarak çıkar. Tekrar eden site öğelerini ayıkla.
- **25.2** PDF’de özgün sayfa, metin bloğu ve tablo ilişkisini koru. Kullanılan OCR’ı kaydet ve kritik alanı incelemeye çıkar.
- **25.3** Pasajla birlikte kuralın koşulunu ve istisnasını taşı. Tablo hücresini satır ve kolon başlığıyla sakla.
- **25.4** Kanıt parçasına kararlı kimlik ve konum ver. URL, kaynak sürümü, bölüm veya sayfaya dönülebilsin.
- **25.5** Resmî İtalyanca ifadeyi koru. Çeviri gösterildiğinde dayanılan orijinal metin açılabilsin.
- **25.6** Belge başlığına dayanan fakat ilgili paragrafı bulunmayan bir iddianın atıf doğrulamasından geçmediğini test et.

**Kabul.** Aramadan resmî konuma gidilip ilgili talimatın bağlamı ve koşulu okunabiliyor.

## 26. İnceleme, onay ve geri çekme sürecini kur

- **26.1** Sürüm durumlarını yeni, incelemede, onaylı, reddedildi, arşivlendi ve geri çekildi olarak modelle. Arama ve cevap üzerindeki etkilerini tanımla.
- **26.2** İnceleyene eski ve yeni içerik, değişiklikler, kaynak sahibi, işlem ve önerilen coğrafi kapsamı göster.
- **26.3** Onayı işlem, bölge, koşul, tarih ve kanıt türüyle kaydet. Form açıklaması ve zorunluluk iddiası kendi dayanağıyla değerlendirilsin.
- **26.4** İnceleyen, zaman, karar, gerekçe ve sürümü denetim geçmişine yaz.
- **26.5** Geri çekilen sürümü yeni cevaplardan çıkar. Açık vakada bağlı adımı yeniden doğrulamaya al.
- **26.6** Yetkili onay akışını ve hangi sürümlerin doğrulanmış olarak yayımlanabileceğini test et.

**Kabul.** Bir kaynağın neden ve hangi kapsamda kullanılabileceği izlenebilir. Onaysız ve geri çekilmiş sürümler doğrulanmış bilgi sağlayamaz.

## 27. Uygulanabilirlik ve kaynak çelişkisi mantığını geliştir

- **27.1** İstekle beraber işlem, yer, tarih ve bilinen koşulları tipli alanlar olarak taşı. İkamet yeri ile hizmetin yürütüldüğü yer gerektiğinde ayrışabilsin.
- **27.2** Ulusal genel talimatla ilgili yerel kanal veya ofis bilgisini birlikte değerlendir ve her birinin kapsamını koru.
- **27.3** Eksik bağlam sonucu değiştiriyorsa ilgili netleştirme bilgisini döndür.
- **27.4** Eski ve yeni sürüm, yerel uygulama varyasyonu ve gerçek çelişki senaryoları için örnekler oluştur.
- **27.5** Çözülemeyen çelişkide iki dayanağı ve farkı incelemeye gönder. Kullanıcıya doğrulanabilen resmî kanalı göster.
- **27.6** Belediye, tarih veya işlem değişince bağlı kanıt ve hazırlık adımlarını yeniden değerlendir.

**Kabul.** İki belediyeye ait yerel kanıtlar karışmaz. Eksik bilgi ve gerçek çelişki gözlemlenebilir farklı sonuç verir.

## 28. Hibrit arama ve ajan sorgu API’sini kur

- **28.1** PostgreSQL tam metin aramasıyla İtalyanca terim, kısaltma, form kodu ve kurum adlarında temel performansı ölç.
- **28.2** Gündelik ifadeler, eş anlamlar ve diller arası sorgular için semantik aramanın katkısını değerlendir. Yeterli kazanım varsa pgvector ekle.
- **28.3** İşlem, yetki alanı ve inceleme durumunu arama öncesi filtrele.
- **28.4** Sonuçları ilgililik, kapsam, kaynak türü ve güncellikle sırala. Tekrarlanan içeriklerin sonuçları doldurmasını önle.
- **28.5** Faz 4 için tipli arama yanıtı ver. İşlem, kurum, yer, kanal, kaynak sürümü, pasaj, konum ve eksik bağlam taşıyabilsin.
- **28.6** UI ve ajanın aynı kaynak ve sürüm kimliğini çözmesini API testleriyle doğrula.
- **28.7** Faz 2 vakalarında doğru işlem ve pasajın ilk sonuçlarda bulunmasını, yanlış yetki alanı ve yanıtsız sorguları ölç. Hedefleri ilk setin sonuçlarından çıkar.

**Kabul.** Resmî İtalyanca ve gündelik İngilizce karşılıklar aynı uygulanabilir hizmete ulaşır. Filtre nedeniyle dışarıda kalan sonuçlar incelenebilir.

## 29. Güncellik, URL ve form sürümü takibini kur

- **29.1** Kaynak türü ve kullanıcı işinin etkisine göre kontrol aralığı belirle.
- **29.2** URL, yönlendirme, sürüm ve ilgili metin farkını izle. Görünüm değişikliğini işlem talimatından ayır.
- **29.3** Etkilenen kural, form alanı, işlem ve vakaları çıkar. Tarih, ücret, belge ve form değişikliğini önce incele.
- **29.4** Geçici kesinti, taşınmış sayfa ve doğrulanmış içerik değişikliği için farklı yeniden deneme veya inceleme yolu tanımla.
- **29.5** Geri çekmede indeksi ve önbelleği güncelle. Gecikmiş arama sonucu varsa cevap öncesi sürüm durumunu kontrol et.
- **29.6** Açık vakada yalnız etkilenen adım ve tekrar incelenecek alanları göster.

**Kabul.** Değişiklikten etkilenen kayıtlar bulunur. Yeni cevaplar geri çekilmiş sürüme dayanamaz ve önceki vakaların dayanağı geçmişte görülebilir.

## 30. Resmî Kaynaklar görünümünü tamamla ve fazı kapat

- **30.1** Tek uygulama kabuğunda kurum, işlem, bölge, belediye ve belge türüyle aranabilen Resmî Kaynaklar görünümünü oluştur.
- **30.2** Detayda yayımlayan, resmî bağlantı, işlem, kapsam, son kontrol ve ulaşılabilir pasajı göster.
- **30.3** Ajanın üreteceği atıf kimliğini aynı kaynak sürümü ve pasaja bağla. Bu sözleşmeyi Faz 4’e ver.
- **30.4** İşlemin hangi bölgelerde ve hangi yetenek için doğrulanmış kaynağı olduğunu göster.
- **30.5** Kaynak ekleme, onay, arama, yeni sürüm ve geri çekme yolculuğunu uçtan uca çalıştır.
- **30.6** Arama API’sini, katalog kimliklerini, atıf şemasını, belirsizlik sonuçlarını, regresyon vakalarını ve pilot kapsamını Faz 4’e devret.

**Kabul.** UI ve ajan API’si aynı sürüm, kapsam ve pasajı gösterir. Pilot setinde yanlış yer, geçersiz form, değişiklik ve geri çekme vakaları geçer.

## Faz 3 kapanış kontrolü

- Kurum ve yer dizini, pilot işlem kataloğu, sürümlü kaynak ve pasaj kayıtları var.
- İnceleme, geri çekme ve güncellik akışları doğrulandı.
- Arama API’si, değerlendirme seti ve Resmî Kaynaklar görünümü aynı kanıt kimliklerini kullanıyor.
- Bir pilot vakada doğru işlem, yetkili kurum, uygulanabilir kaynak, ilgili pasaj ve geçerli kanal elde edildi. Belediye veya form sürümü değiştirildiğinde sonuç beklenen şekilde değişti.
