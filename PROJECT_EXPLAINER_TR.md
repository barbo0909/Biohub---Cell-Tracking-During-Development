# Biohub Hucre Takibi Projesi: Teknik ve Kavramsal Rehber

## 1. Projenin Amaci

Bu projede gelismekte olan zebra baligi embriyosunun zaman icinde cekilmis 3 boyutlu mikroskop goruntulerini analiz ediyoruz. Hucreler floresan isaretleme sayesinde parlak yapilar olarak gorunuyor.

Gorev uc ana parcadan olusuyor:

1. Her zaman noktasindaki hucreleri bulmak.
2. Ayni hucreyi sonraki karelerde takip etmek.
3. Hucre bolundugunde anne hucreyi iki yavru hucreye baglamak.

Nihai cikti, hucrelerin zaman icindeki hareketini ve soy iliskilerini gosteren bir takip ve lineage grafidir.

## 2. Embriyo ve Ornek Kimligi

Embriyo, dollenmeden sonra gelismekte olan canlidir. Buradaki canli zebra baligidir. Gelisim sirasinda hucreler hareket eder, sekil degistirir, goruntu alanina girip cikabilir ve bolunebilir.

Dosya isimleri su yapidadir:

```text
44b6_0113de3b
6bba_09961292
```

Ilk bolum embriyo kimligidir:

```text
44b6       -> embriyo kimligi
0113de3b   -> goruntu alani/ornek kimligi
```

Ayni embriyodan birden fazla goruntu alani bulunabilir. Ayni embriyodan gelen ornekler birbirine daha cok benzeyebilecegi icin validation ayrimlarinda embriyo kimligini dikkate almak gerekir. Hidden test farkli embriyolardan geldigi icin asil hedef ezberlemek degil, yeni embriyolara genellemektir.

## 3. Goruntu Verisinin Yapisi

Her `.zarr` ornegi tipik olarak su sekle sahiptir:

```text
(T, Z, Y, X) = (100, 64, 256, 256)
```

- `T=100`: zaman noktasi sayisi
- `Z=64`: her zamandaki derinlik katmani
- `Y=256`: goruntu yuksekligi
- `X=256`: goruntu genisligi

Bu normal bir 2D video degil, zaman serili 3D hacimdir. Bu nedenle veri 3D+time veya 4D microscopy olarak adlandirilabilir.

Fiziksel voksel olcegi:

```text
Z = 1.625 um
Y = 0.40625 um
X = 0.40625 um
```

Z eksenindeki bir voksel adimi X/Y adimindan dort kat buyuktur. Mesafeler ham voksel uzayinda degil, bu olcekler kullanilarak mikrometre cinsinden hesaplanmalidir.

## 4. Ground Truth ve GEFF Grafigi

Train goruntulerinin yaninda `.geff` takip grafikleri bulunur.

Bir node ornegi:

```text
node_id = 123
t = 20
z = 31
y = 145
x = 92
```

Bu, 20. zaman noktasinda belirtilen koordinatta bir hucre merkezi oldugu anlamina gelir.

Bir edge ornegi:

```text
source_id = 123
target_id = 456
```

Bu, 123 numarali hucrenin sonraki karede 456 numarali hucre olarak devam ettigi anlamina gelir.

Bolunme yapisi:

```text
anne -> yavru 1
anne -> yavru 2
```

Iki veya daha fazla outgoing edge'i olan node division adayidir.

Ground truth sparse'tir. Goruntudeki tum hucreler etiketlenmemistir. Bu nedenle etiketsiz bir tahmin otomatik olarak yanlis kabul edilemez. Yerel degerlendirme ve hata analizi bu gercegi dikkate almalidir.

## 5. Modelin Takip Ettigi Nesne

Model dogrudan sabit bir hucre kimligini okumaz. Once her karede hucre merkezlerini bulur, ardindan zamanlar arasindaki olasi baglantilari puanlar.

Ornek:

```text
t=10: A, B, C
t=11: D, E, F
```

Model `A -> D`, `A -> E`, `A -> F` gibi adaylari puanlar. Goruntu ozellikleri, fiziksel mesafe, hareket ve grafik kurallari kullanilarak en tutarli baglantilar secilir. Division varsa bir anne node iki yavru node'a baglanabilir.

## 6. Kullandigimiz Uctan Uca Pipeline

```text
Zarr 3D+time goruntu
-> goruntu on isleme
-> 3D UNet hucre merkezi heatmap'i
-> hucre merkezi detection'lari
-> node-transformer edge olasiliklari
-> ILP ile tutarli takip grafigi
-> motion/gap/division/short-track postprocess
-> submission.csv
```

### 6.1 Goruntu on isleme

Mikroskop orneklerinin parlaklik ve gurultu dagilimlari farklidir. Normalizasyon, modelin mutlak parlaklik yerine hucre yapilarina odaklanmasini saglar.

### 6.2 3D UNet detection modeli

UNet her voksel icin hucre merkezi olasiligini temsil eden bir center heatmap uretir. Lokal maksimumlar bulunarak hucre node'lari olusturulur.

Exact public `0.900` d3ac1a pipeline detection esigi `0.97`, eski `0.889` pipeline esigi `0.99` idi. Esigi dusurmek recall'i artirabilir, fakat fazla detection node overprediction cezasina neden olabilir.

### 6.3 Sekiz gorunumlu TTA

Test-time augmentation sirasinda ayni hacim sekiz uzamsal gorunumle modele verilir:

- orijinal
- X flip
- Y flip
- X+Y flip
- 90 derece rotasyon
- 270 derece rotasyon
- transpose
- anti-transpose

Heatmap'ler tekrar orijinal koordinat sistemine donusturulup ortalanir. Amac yon hassasiyetini azaltmak, zayif merkezleri daha guvenilir bulmak ve tek gorunum hatalarini ortalamaktir. Bunun bedeli daha uzun inference suresidir.

### 6.4 Node-transformer association modeli

UNet hucreleri bulur; node-transformer hangi hucrenin bir sonraki karede hangi hucre olarak devam ettigini puanlar. Koordinat, zaman ve goruntu ozelliklerinden candidate edge olasiliklari uretilir.

Kullandigimiz public support pack yaklasik 400 epoch egitilmis bir agirlik icerir. Su ana kadar modeli sifirdan yeniden egitmedik. Public checkpoint'i analiz edip inference ve postprocess seviyesinde gelistiriyoruz.

### 6.5 ILP grafik optimizasyonu

Integer Linear Programming aday edge'leri birlikte degerlendirerek celiskisiz bir grafik secmeye calisir. Bu asama iki annenin ayni hucreye baglanmasi, anlamsiz dal sayisi ve tutarsiz baslangic/bitis gibi problemlere karsi global kisitlar uygular.

Temel agirliklar:

```text
edge weight          = -1.0
appearance weight    = 0.1
disappearance weight = 0.1
division weight      = 1.0
```

## 7. Postprocess Asamalari

### Motion relink

Hucrenin onceki hareketine bakarak sonraki konumu tahmin eder. Ham model edge'i hareket acisindan tutarsizsa daha uygun bir baglanti arar.

### Gap close

Bir track tek kareligine kopmussa mevcut veya sentetik bir ara node kullanarak baglantiyi onarmaya calisir.

### Safe divisions

Anne-yavru mesafesi, yavrular arasi mesafe ve kare/global division limitleri uygunsa ikinci yavru edge'i ekleyerek division kurtarmaya calisir.

### Short-track filtresi ve adaptive rescue

Cok kisa track'ler gurultu olabilecegi icin silinir. Exact public `0.900` d3ac1a pipeline temel siniri `minimum track length = 6` degeridir. Adaptive rescue, guclu edge olasiligi ve uygun hareket mesafesi tasiyan bazi 4-5 node uzunlugundaki component'leri geri alabilir.

Yeni d3ac1a uzerinde min-track `6 -> 5` Kaggle deneyi ayrica calistirilmistir. Bu, dogru kisa track'lerin gereksiz silinip silinmedigini test eden bagimsiz bir public probe'dur.

### Line-fit smoothing

Track icindeki centroid titresimlerini azaltmak icin dogrusal track ic kisimlarini zaman ekseninde yumusatir. Grafik topolojisini degistirmez.

## 8. DeepCenter ve Ranker

Eski `0.889` pipeline ek bir full-frame center modelinden yararlaniyordu. Exact d3ac1a `0.900` secili preset'inde DeepCenter add-only gate kapatilmistir. Kazanc esas olarak threshold, 8-view TTA, adaptive short-track rescue ve division ayarlarindan gelmektedir.

Ayrica indirdigimiz association ranker 22 hareket, mesafe, yogunluk ve grafik ozelligiyle edge adaylarini siralar. Bu ranker exact public `0.900` pipeline'da kullanilmamaktadir. Planlanan guvenli kullanim, sadece mevcut linkerin kararsiz oldugu durumlarda confidence-gated tie-breaker olarak calistirmaktir.

## 9. Submission Formati

Node satirlari hucre merkezlerini, edge satirlari zamanlar arasi baglantilari tasir:

```text
dataset,row_type,node_id,t,z,y,x,source_id,target_id
sample_1,node,123,20,31,145,92,-1,-1
sample_1,edge,-1,-1,-1,-1,-1,123,456
```

## 10. Yarisma Metrigi

Her zaman noktasinda tahmin ve GT node'lari fiziksel centroid mesafesine gore optimal bipartite assignment ile eslestirilir. Maksimum eslesme mesafesi `7.0 um` degeridir.

```text
edge_jaccard = TP / (TP + FP + FN)
score = adjusted_edge_jaccard + 0.1 * division_jaccard
```

Fazla toplam node tahmini ayrica cezalandirilir. Division grafigi connected-component mantigiyla degerlendirilir.

Division Jaccard'daki `+0.05` iyilesme toplam skora `+0.005` getirebilir. Bu miktar public `0.900` seviyesinden ilk 7 hedefi olan yaklasik `0.905+` seviyesine cikmak icin yeterli olabilir.

Yerel sparse-GT edge scorer hata analizi icin yararlidir, fakat resmi node penalty ve connected-component division metriginin birebir kopyasi degildir.

## 11. Su Ana Kadar Yapilanlar

1. Veri butunlugu 199 Zarr + 199 GEFF olarak dogrulandi.
2. Boyut, dtype, chunk, fiziksel olcek ve koordinat yapisi incelendi.
3. Basit detection/linking baseline Kaggle'da `0.631` aldi.
4. Public learned DeepCenter pipeline Kaggle'da `0.889` aldi.
5. Yeni d3ac1a pipeline Kaggle'da `0.900` aldi.
6. Iki pipeline'in ayni temel model agirligini kullandigi dogrulandi.
7. Artisin yeni model agirligindan degil inference ve postprocess degisikliklerinden geldigi bulundu.
8. Eski pipeline'da min-track `7 -> 5` targeted local skoru artirdi.
9. Exact `0.900` pipeline icin min-track `6 -> 5` Kaggle deneyi baslatildi.
10. Exact `0.900` d3ac1a Full199 tanisal kosusu baslatildi.
11. Inference GEFF'leri Zarr uyumlu yerel diskte olusturulup her 10 sample'da Drive checkpoint'ine kalici yaziliyor.
12. Kosu sonunda eski `0.889` ve yeni `0.900` local sonuclari ayni scorer altinda sample bazinda karsilastirilacak.

## 12. Full199 Kosusunun Karar Mantigi

Full199 kosusunun amaci yalnizca tek bir ortalama skor almak degildir. Her sample'daki baskin hata tipini belirlemektir:

```text
node recall dusuk
-> detection problemi

node recall yuksek, edge FN yuksek
-> association problemi

centroid eslesme mesafesi yuksek
-> localization/refinement problemi

division agirlikli sample'lar dusuk
-> division problemi

local edge sonucu yuksek, Kaggle sonucu dusuk
-> node overprediction, resmi division metrigi veya dagilim farki
```

Bu ayrimdan sonra detection probleminde TTA belirsizligi ve sample-adaptive threshold; association probleminde confidence-gated ranker; motion probleminde cok kareli velocity modeli; division probleminde parent/daughter olay modeli; metric probleminde resmi node adjustment ve division scorer'a daha yakin yerel degerlendirme gelistirilecektir.

## 13. Hedef

Ilk ara hedef public leaderboard'da ilk 7'dir. 12 Temmuz 2026 goruntusunde bu esik yaklasik `0.905` idi; leaderboard hareketine karsi guvenli hedef `0.907+` olarak alinmalidir.

Nihai hedef yalnizca hucre bulmak degil, yogun ve gurultulu 3D mikroskop verisinde hareket eden, kaybolan ve bolunen hucrelerden fiziksel olarak tutarli bir soy grafigi uretmektir.
