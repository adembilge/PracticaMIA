# PracticaMIA 2.0 — Faz 2 · Kullanıcı işleri, kapsam ve ürün sözleşmesi

**Yol haritası görevleri 11–20.** Bu faz gerçek bir bürokratik işte PracticaMIA’nın hangi engeli çözebileceğini araştırır ve bulguları ilk sürümün geliştirme sözleşmesine çevirir. İtalya genelindeki ürün kapsamı için ilk pilot, tek ajanın farklı kurumlar, bölgeler ve belge türleriyle nasıl çalışacağını sınar.

## 11. Gerçek kullanıcı vakalarını topla

- **11.1** İtalya’ya yeni gelenler, öğrenciler, çalışanlar, aileler ve küçük işletme sahipleri gibi farklı profillerden yaklaşık 20 vaka hedefle. İtalyanca seviyesi, yerleşim yeri ve dijital hizmet kullanımı farklı katılımcılarla görüş.
- **11.2** Yakın zamanda tamamlanan, bekleyen ve yarıda bırakılan işleri incele. Tamamlanan işte kullanılan yolu, bekleyen işte sıradaki belirsizliği, bırakılan işte tıkanma anını kaydet.
- **11.3** Aynı çekirdek sorularla görüş. Kullanıcı ilk ne yaptı, doğru kuruma nasıl karar verdi, nerede takıldı, kimden yardım aldı ve hâlâ ne eksik? İlk kullanıcı cümlesini doğal dilde olduğu gibi kaydet.
- **11.4** Katılımcının izin verdiği ölçüde kişisel alanları kapatılmış resmî yazı, portal ekranı, form veya makbuz üzerinden adımları yeniden yürüt. Ekranın gösterdiği bilgiyle kullanıcının yorumunu ayrı kaydet.
- **11.5** Asıl engeli belirle. Kurum seçimi, İtalyanca terim, belge listesi, form alanı ve durum takibi örnektir.
- **11.6** Ajanın üstleneceği somut işi yaz. Örneğin istenen eki yazıda işaretlemek, kullanıcının dosyasıyla eşleştirmek ve gönderim kanalını bulmak.

**Çıktı ve kabul.** Vaka kartı anonim ID, ilk kullanıcı cümlesi, kurum, yer, mevcut aşama, engel, kanıt, mevcut çözüm ve beklenen sonucu içerir. Her aday özellik gözlemlenmiş bir engelle ilişkilidir. Vaka sayısı keşif hedefidir ve ülke geneli için talep tahmini üretmez.

## 12. İtalya’daki işlem alanlarının haritasını çıkar

- **12.1** Göç ve oturum, anagrafe ve kimlik, sağlık, eğitim, çalışma, sosyal haklar, vergi, aile, ulaşım ve işletme işlemlerini başlangıç haritasına al.
- **12.2** Günlük kullanıcı ifadelerini olası resmî işlemlerle eşleştir. Tek ifadenin birden fazla resmî işleme işaret ettiği örnekleri kaydet.
- **12.3** Ulusal, bölgesel ve belediye düzeylerini kaydet. Yetkili kurumu belirlemek için gerekli yer veya durum bilgilerini çıkar.
- **12.4** Resmî portal, kurum sayfası, ofis, randevu ve yüz yüze hizmet kanallarını gözlenen vakalar üzerinden haritala.
- **12.5** Bir hayat olayının başlattığı farklı işlemlerde gerçek önkoşulları, ortak belgeleri ve paralel işleri belirle.

**Çıktı ve kabul.** İşlem haritasında konu, kullanıcı ifadesi, işlem adayı, kurum, yetki alanı, kanal ve açık sorular var. Aynı ifadenin farklı yerlerde veya koşullarda farklı rotaya gittiği vakalar da bulunuyor.

## 13. Sohbetin başlangıcını ve ilerlemesini tanımla

| Kullanıcı girişi | Ajanın ilk işi | Görünür çıktı |
| --- | --- | --- |
| Soru | Terimi ve bağlamı bulmak | Açıklama, kaynak ve gerekiyorsa soru |
| Hedef | İlgili işlemleri ve önceliği belirlemek | İlk iş ve onu değiştiren soru |
| Kurum yazısı veya ekran görüntüsü | Kurum ve talebi bulmak | Yapılacak iş ve belgedeki karşılığı |
| Form | Formu, alanı ve sürümü tanımak | Alanın anlamı ve doğrulanabilir değer |
| Makbuz | Belgenin neyi kanıtladığını belirlemek | Gönderim kanıtı ve takip adımı |

- **13.1** Her giriş için normal, eksik bilgili ve yanlış bağlamlı örnek konuşma yaz.
- **13.2** Netleştirme sorusunu yanıtı değiştiren bilgiler için sor. Genel bir açıklama doğrudan yapılabiliyorsa onu ver.
- **13.3** Kullanıcı bilmiyorsa bilginin bulunabileceği yeri ve o bilgi olmadan yapılabilen kısmı göster.
- **13.4** Aynı mesajdaki birden fazla işi tanı. Ajan aktif işlemi görünür kılsın ve konu değişince ilgili bağlama dönebilsin.

**Kabul.** Kullanıcı serbest metinle başlar. Ajan akışı ilerletir veya yalnız sonucu değiştirecek eksik bilgiyi sorar.

## 14. İlk geliştirilecek akışları puanla

| Ölçüt | Önerilen ağırlık |
| --- | ---: |
| Gözlemlenen ihtiyaç | 30 |
| Sağlanabilecek somut ilerleme | 25 |
| Resmî kanıt kalitesi | 20 |
| Başka işlemlerde yeniden kullanım | 15 |
| İlk pilotta uygulanabilirlik | 10 |

- **14.1** Her ölçütü 0–5 arası puanla ve puanın dayanağını kaydet. Ağırlıkları pilot bulguları geldikçe yeniden değerlendir.
- **14.2** İşlem bulma, belge kontrolü, form hazırlığı ve takip için uygulanabilirliği ayrı incele.
- **14.3** Yanlış cevabın etkisini ve dış bağımlılıkları kaydet. Yanlış tarih, yanlış muhatap ve doğrulanmamış form gibi sonuçlar öncelikli.
- **14.4** Kurum, coğrafya ve belge türü çeşitliliğini kontrol et. Çeşitlilik için eklenen vakanın gerekçesini yaz.

**Kabul.** İlk sıradaki işlerin gerekçesi ve ertelenen yeteneklerin hangi kanıta ihtiyaç duyduğu görülebilir.

## 15. İlk pilot vaka setini oluştur

- **15.1** En az üç kurum ve birden fazla bölgeyi kapsa. Ulusal hizmet, yerel uygulama ve kurumlar arası geçiş içeren örnekler seç.
- **15.2** Yanlış kurum, eksik belge bildirimi, okunamayan tarih, eski form ve devam eden başvuru gibi kırılma noktalarını ekle.
- **15.3** Beklenen sonraki adımı resmî dayanağıyla yaz. Kabul edilebilir alternatifleri ve kabul edilemez cevapları tanımla.
- **15.4** Her vakanın ne zaman tamamlandığını belirt. Doğru hizmeti açma, eksik eki saptama veya form alanını doğrulama örnek sonuçlardır.
- **15.5** Yer değiştiğinde, belge başka işleme ait olduğunda veya yeni bildirim geldiğinde ajanın neyi yeniden değerlendireceğini yaz.

**Kabul.** Pilot, birden fazla kurum üzerinde yönlendirme, belgeyle çalışma ve hata sonrası toparlanmayı sınar. Tamamlanma ölçütü gözlemlenebilir.

## 16. İşlem bazında yetenek sözleşmesini çıkar

- **16.1** İşlem bulma, kaynaklı açıklama, belge kontrolü, form hazırlığı ve durum takibi yeteneklerini işlem başına kaydet.
- **16.2** Açılan her yetenek için gerekli girdi, kanıt, çıktı ve kullanıcı onayı koşulunu tanımla.
- **16.3** Bir yetenek doğrulanmamışsa işe yarar sonraki adımı yaz. Örneğin alan eşlemesi doğrulanmadığında güncel resmî formu aç ve açıklanabilen alanı eldeki kanıtla açıkla.
- **16.4** Kullanıcı bildirimi, gönderim makbuzu ve kurumca doğrulanan durumun anlamını ayrı gösterecek kuralları yaz.

**Kabul.** Her işlem kaydı, geliştiricinin kabul edeceği girdiyi ve kullanıcının göreceği çıktıyı, onay noktasıyla birlikte gösterir.

## 17. Başarı metrikleri ve karşılaştırmalı test

- **17.1** Birincil metrik doğru sonraki adıma yardımsız ulaşmadır. Kullanıcı doğru kurumu ve ne yapacağını kendi cümlesiyle açıklayabilsin.
- **17.2** İkincil metrikler süre, yanlış yönlendirme, gereksiz soru, yanlış belge ve dosyaya dönünce devam edebilme olsun.
- **17.3** Benzer vakaları bugün kullanılan yöntemle ve PracticaMIA ile çalıştır. Önceki deneyim ve moderatör yardımı gibi sonucu etkileyen bilgileri kaydet.
- **17.4** Yardımlı ve yardımsız tamamlamayı ayrı ölç.
- **17.5** Başarı eşiğini ilk testten önce yaz. Küçük pilotta yüzdelerin yanında katılımcı ve vaka sayılarını ver.

**Kabul.** Sonuçlar, ajanın cevap üretmesinin ötesinde kullanıcının hangi işi ne ölçüde ilerlettiğini gösterir.

## 18. Kritik hata ve toparlanma davranışını tasarla

- **18.1** Yanlış kurum, belediye veya aynı adlı işlem için beklenen ayırt edici soruyu tanımla.
- **18.2** Eski form, kırık bağlantı, çelişen kaynak ve farklı form sürümlerinde kullanıcının yeniden doğrulayacağı bilgiyi tanımla.
- **18.3** Eksik sayfa, bulanık tarih ve başka vakaya ait belge için kullanıcının göreceği kanıtı ve toparlanma adımını yaz.
- **18.4** PDF üretimi, kullanıcı beyanı, makbuz ve kurum kararının hangi durum değişikliklerine izin verdiğini ayrı örnekle.
- **18.5** Her vaka için girdi, beklenen davranış, kabul edilemez sonuç ve eski kayıtların nasıl korunacağını kaydet.

**Kabul.** Kritik örnekler sonraki ajan, belge, kaynak ve arayüz regresyon testlerine aktarılabilir.

## 19. Dil, ton ve arayüz kurallarını belirle

- **19.1** İlk değerlendirme dilleri İtalyanca ve İngilizce olsun. Her vaka iki dilde aynı kuruma ve aynı sonraki adıma ulaşsın.
- **19.2** Resmî form alanının orijinal İtalyanca adını koru. Açıklama kullanıcının dilinde gösterilsin.
- **19.3** Cevabın ilk cümlesi soruya cevap versin. Sonraki iş eylem olarak görünsün. Kaynak ve belge detayı açılabilir olsun.
- **19.4** Sohbet sırasında dil değişse de vaka, belge ve alan bağlantıları korunsun.
- **19.5** Başka bir dil veya belirsiz ifade geldiğinde anlaşılır bir netleştirme yolu tanımla.

**Kabul.** Kullanıcı her iki değerlendirme dilinde aynı sonraki adıma ulaşabiliyor ve resmî portaldaki alanı orijinal adıyla tanıyor.

## 20. Tek sohbet prototipini test et ve fazı kapat

- **20.1** Ana ekran sohbet olsun. Şimdi ne yapmalıyım, resmî kaynak ve belge veya form incelemesi aynı vakada açılabilsin.
- **20.2** Gerçek bir kurum yazısından başla. Ajanın talebi açıklaması, ilgili bölümü göstermesi, eksik bilgiyi sorması ve gerekli adımı hazırlamaya yardım etmesi gözlemlensin. Kullanıcı değeri düzeltebilsin.
- **20.3** Başka bir kurumdan gelen serbest metin sorusunu aynı sohbet, kaynak ve sonraki işlem bileşenleriyle sınayarak yeniden kullanımı göster.
- **20.4** Kullanıcı dosyayı kapatıp yeniden açsın. Önceki düzeltmeyi, sonraki adımı ve resmî kanalı tekrar anlatmadan bulsun.
- **20.5** Her tıkanmayı kaynak kapsamı, ajan, belge okuma veya arayüz gereksinimine bağla. Faz 3 ve 4’ün iş listesine somut girdi üret.
- **20.6** Pilot kapsamı, belirsizlik ve yeniden test edilecek durumları kaydet. Prototiple gösterilen davranışın yanı sıra gerçekten çalışan özellikleri de açıkça belirt.

**Kabul.** Kullanıcı gözlenen bir ihtiyacıyla başlayıp doğru sonraki adıma ulaşabiliyor. Faz 3’e anonim vaka kartları, işlem ve kurum haritası, yetenek sözleşmeleri, öncelikli pilot seti, ölçüm planı, kritik hata testleri ve tek sohbet prototipinin bulguları devrediliyor.
