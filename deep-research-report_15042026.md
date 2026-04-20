# DeepSoil ile GQ/H + MRDF (UIUC) Nonlineer Histerezis Paritesi: Kalan Farkın En Olası Nedenleri ve Kapatma Yol Haritası

## Executive diagnosis

- Monotonik backbone (GQ/H θ-seti) pariteniz zaten iyi olduğu için kalan farkın ana kaynağı “envelope” değil; döngü içi **unload–reload–reversal** semantiği ve bunun **etkin teğet rijitlik** (effective tangent) evrimine nasıl yansıdığı. citeturn8view1turn7view0  
- +%11.7 “peak period” kayması, spektral pik periyodunun daha uzun çıkması demek; bu genellikle, kontrol eden bandda sistemin **etkin rijitliğinin DeepSoil’e göre daha düşük** (daha yumuşak) hesaplandığını gösterir. Bu büyüklükte bir periyot kayması, yalnız “küçük sönüm matrisi” ayrıntılarıyla açıklanması zor bir seviyededir (linear SDOF’da sönümün doğal frekansa etkisi sınırlıdır); dolayısıyla ana şüpheli histerezis/teğet. citeturn9search0turn6search0  
- DeepSoil’in “Extended Masing” unload–reload semantiği **4 kural** üzerinden tanımlanır: (i) backbone, (ii) reversal sonrası ölçekli/ötelenmiş backbone, (iii) backbone ile kesişmede backbone’a dönüş, (iv) önceki çevrimin unload–reload eğrisiyle kesişmede o önceki eğriyi takip. Bu 3–4. kurallar eksik/gevşek uygulanırsa loop enerjisi kadar **etkin rijitlik tarihi** de sapar. citeturn6search0turn8view1  
- MRDF-UIUC DeepSoil’de “tek skaler” gibi çalışan bir “reload_factor” değildir; **maksimum geçmiş şekil değiştirmeye bağlı (γ_max)** bir azaltma faktörü **F(γ_max)** ile “Masing’in ürettiği unload–reload eğrisini” modifiye eder. Bu nedenle, sizin gözlediğiniz gibi tek bir sabit çarpan tüm metrikleri aynı anda kapatmaz (bu beklenen davranış). citeturn4view0turn0search32turn8view1  
- En kritik teknik nokta: literatürde (GQ/H makalesinde) MRDF unload–reload formu, “yalnızca τ’yu F ile çarp” değil; **Masing eğrisi ile bir referans doğrusu/rijitliği arasındaki farkı F ile ölçekleyip**, referansı geri ekleyen bir “bridge” formudur. Bu formu “salt çarpan” diye uygularsanız **teğet rijitliği gereğinden fazla düşürür** ve periyot uzaması kalıcı olur. citeturn8view1turn6search0  
- “Peak-period mismatch sabit kalıyor ama loop-energy iyileşiyor” paterni, çoğunlukla şunu işaret eder: ya (a) global çözümde kullandığınız **stiffness/tangent** loop-enerji modifikasyonlarınızdan etkilenmiyor (yanlış teğet geri dönüşü / secant–tangent ayrımı), ya da (b) MRDF/extended-Masing kesişme/switch semantiği teğeti DeepSoil’den farklılaştırıyor. citeturn6search0turn8view1  
- Damping matrisi kaynaklı fark tamamen “imkânsız” değil ama +%11.7 periyot kayması için düşük olasılıklı: DeepSoil’in “frequency independent damping + implicit Newmark + no damping-matrix update” seçeneklerinde amaç zaten frekans bağımlı aşırı sönümü azaltmak; bu, spektral pik periyotunu sistematik olarak +%10 mertebesinde kaydırmaktan ziyade yüksek frekans filtrasyonu ve genlikleri etkiler. citeturn3view0turn6search0turn9search0  

## DeepSoil davranışının yeniden inşası

Bu bölümde “dokümante edilmiş” (kaynakta açık olan) kısımları ve “en güçlü çıkarım” (kaynağa dayalı ama kod görmeden) kısımları ayırıyorum.

### Dokümante edilmiş çekirdek: Extended Masing unload–reload ve kesişme kuralları

Phillips & Hashash (2009) DEEPSOIL ve benzeri 1D NL kodlarda kullanılan extended Masing unload–reload kurallarını açıkça listeler: citeturn6search0  

1) **İlk yükleme** backbone üzerinde:  
\[
\tau = F_{bb}(\gamma)
\]

2) **Reversal** (γ_rev, τ_rev) noktasında terslenme olunca unload/reload eğrisi (2. Masing kuralı):  
\[
\frac{\tau-\tau_{rev}}{2} = F_{bb}\!\left(\frac{\gamma-\gamma_{rev}}{2}\right)
\]
eşdeğer yazım:  
\[
\tau(\gamma)=\tau_{rev} + s\; 2\,F_{bb}\!\left(\frac{\gamma-\gamma_{rev}}{2}\right)
\]
burada \(s=\pm 1\) yön işareti.

3) **Unload–reload eğrisi backbone’u keserse**, backbone’u takip eder (bir sonraki reversal’a kadar). citeturn6search0turn8view1  

4) **Unload–reload eğrisi önceki çevrimin unload–reload eğrisiyle kesişirse**, o önceki eğriyi takip eder (cycle-memory). citeturn6search0turn8view1  

Bu 3–4. maddeler, “branch’in ne zaman backbone’a döneceği” sorusunun DeepSoil tarafındaki temel cevabıdır: **kriter kesişme (intersection)** ve literatürde “kesişme” stres-şekil değiştirme düzleminde tanımlanır (tangent sürekliliği şartı değil). citeturn6search0turn8view1  

### Dokümante edilmiş çekirdek: MRDF-UIUC ve “Non-Masing Re/Unloading” mantığı

DeepSoil “Non-Masing Unload-Reload” seçeneğini MRDF yaklaşımı olarak tanımlar ve histeretik sönümü Masing’ten gelen sönümün bir azaltma faktörü ile çarpılması şeklinde ifade eder: citeturn4view0turn0search32  

\[
\xi_{\text{MasingHysteretic}} = F(\gamma_{max})\;\xi_{\text{Masing}}
\]

MRDF-UIUC için azaltma faktörü: citeturn4view0turn0search32  

\[
F(\gamma_m) = P_1 - P_2\left(1-\frac{G(\gamma_m)}{G_0}\right)^{P_3}
\]

- \(\gamma_m\) (dokümanlarda) “herhangi bir anda experienced edilen maksimum shear strain” olarak anlatılır; pratikte en güçlü yorum **\(\gamma_{max}(t)=\max_{0\le \tau\le t}|\gamma(\tau)|\)** türü monoton tarih değişkenidir. citeturn4view0turn0search32  
- \(G(\gamma_m)\) ifadesi, MR (modulus reduction) eğrilerinin tanımıyla tutarlı olarak çoğu pratikte **secant modulus** (G = τ/γ) anlamına gelir (çünkü hedef eğriler G/G_max – γ amp ilişkisi olarak verilir). citeturn0search32turn0search1  

### Dokümante edilmiş kritik detay: GQ/H + MRDF unload–reload formu “salt çarpan” değildir

Groholski vd. (2016) GQ/H modelini ve unload–reload (Masing) ile MRDF modifikasyonunu birlikte verir. Metindeki ana fikir şu: Masing unload–reload loop’ları büyük şekil değiştirmede damping’i fazla büyütebilir; MRDF, unload–reload eğrisini “azaltılmış” hale getirir. citeturn8view1turn7view0  

Metinde teknik olarak görülen yapı (formül yazımı OCR sebebiyle dağınık görünse de) şu “bridge” biçimidir: citeturn8view1  

- Önce Masing unload–reload gerilmesi (reversal etrafında ölçekli backbone) hesaplanır:  
\[
\tau_{M}(\gamma)=\tau_{rev}+ s\,2F_{bb}\!\left(\frac{\gamma-\gamma_{rev}}{2}\right)
\]

- Sonra MRDF ile modifiye edilirken yalnız τ_M çarpılmaz; **τ_M ile bir lineer referans arasındaki fark F ile ölçeklenir**, referans geri eklenir:  
\[
\tau(\gamma) \approx \tau_{rev} + F(\gamma_{max})\Big(\tau_M(\gamma)-\tau_{lin}(\gamma)\Big)+\tau_{lin}(\gamma)
\]
burada tipik lineer referans:  
\[
\tau_{lin}(\gamma)= G_{\gamma_{max}}\;(\gamma-\gamma_{rev})
\]
\(G_{\gamma_{max}}\) seçimi literatürde “γ_max seviyesindeki modulus” olarak görünür. citeturn8view1turn0search1  

Bu formun teğet rijitlik etkisi çok kritik: F sabit kabul edilirse (γ_max sabitken),  
\[
\frac{d\tau}{d\gamma} \approx F\frac{d\tau_M}{d\gamma} + (1-F)G_{\gamma_{max}}
\]
Yani **teğet**, Masing teğeti ile \(G_{\gamma_{max}}\) arasında “konveks kombinasyon”dur. Eğer siz yanlışlıkla  
\[
\tau = \tau_{rev} + F(\gamma_{max})\big(\tau_M(\gamma)-\tau_{rev}\big)
\]
gibi bir “salt çarpan” uygularsanız teğet  
\[
d\tau/d\gamma \approx F\,d\tau_M/d\gamma
\]
olur ve **(1−F)⋅G_ref katkısı kaybolduğu için** unload–reload dalı gereğinden yumuşar. Bu mekanizma “peak period sürekli uzun” kalmasına doğrudan adaydır. citeturn8view1turn6search0  

### DeepSoil’in çözüm seçenekleriyle uyumlu görünen sayısal kabuk

DeepSoil time-domain NL çözümde “implicit Newmark β” kullanabildiğini ve time-step altbölme (sub-increment), interpolasyon gibi seçenekleri olduğunu dokümante eder. citeturn3view0turn4view0  
Ayrıca “Frequency independent damping matrix type” ve “Damping Matrix Update: Yes/No” gibi seçenekleri UI’da verir. citeturn1search0turn3view0  

Bu, sizin “implicit Newmark + frequency-independent damping + no matrix update” hedef semantiğinizle tutarlıdır; kalan farkın daha çok **constitutive/tangent** tarafında olması beklentisini güçlendirir. citeturn3view0turn6search0turn9search0  

## Ranked hypotheses for the remaining mismatch

Buradaki sıralama “peak period +%11.7 sabit kalıyor” gözleminizi merkeze alır ve özellikle “stiffness history”yi en çok etkileyen mekanizmaları üstte tutar.

### MRDF unload–reload formunun “bridge” yapısı eksik ya da yanlış

**Belirtiyle uyumu:** Peak-period kayması kalıcı (+%11.7). Bu, unload–reload boyunca sistemin efektif rijitliğinin sürekli daha düşük kalmasıyla uyumlu. Loop-energy iyileşebiliyor ama periyot değişmiyorsa, enerji/alan ayarlayan ama teğeti doğru geri taşımayan bir MRDF uygulaması çok olasıdır. citeturn8view1turn6search0  

**Teknik gerekçe:** GQ/H + MRDF literatür formu, \(F(\gamma_{max})\) ile **(τ_Masing − G_ref Δγ)** farkını ölçekleyip \(G_ref Δγ\) referansını geri ekleyen bir yapı gösterir. Salt “τ_Masing’i F ile çarpma” teğeti aşırı düşürür. citeturn8view1turn0search32  

**En net doğrulama testi:** Aynı strain history üzerinde (single-element replay) aşağıdaki iki teğeti karşılaştırın:
- sizin kodun ürettiği \(G_t(t)=d\tau/d\gamma\);
- bridge-formdan gelen \(G_t^{bridge}\approx F\,G_t^{Masing}+(1-F)G_{ref}\).
Aradaki fark, rezonans periyodu ölçeğinde (özellikle 0.2–2 s bandında) direkt etki yapar. citeturn8view1turn6search0  

### \(G_{\gamma_{max}}\) seçimi (secant vs tangent, hangi γ’de) DeepSoil’den farklı

**Belirtiyle uyumu:** τ_peak NRMSE ~0.04 gibi iyi iken peak period hatası büyük kalabiliyor; çünkü τ_peak daha çok “envelope/strength” ile ilişkili, peak period ise “band-averaged stiffness history” ile. \(G_{ref}\) seçimi teğeti ve dolayısıyla wave speed’i (Vs∼sqrt(G/ρ)) değiştirir. citeturn8view1turn4view0  

**Teknik gerekçe:** Dokümanlarda \(G(\gamma_m)\) “γ_m’de shear modulus” diye geçiyor; MR eğrileri ile uyumlu okuma secant olsa da, unload–reload bridge’de kullanılan \(G_{\gamma_{max}}\) bazı uygulamalarda tangent veya “o anki secant” olabilir. Bu ayrım F’nin kendisini de, teğet karışımını da değiştirir. citeturn4view0turn0search1turn8view1  

**En net doğrulama testi:** Aynı zaman serisi için üç seçenekle koşturun:
1) \(G_{ref}=G_{secant}(\gamma_{max})=\tau_{bb}(\gamma_{max})/\gamma_{max}\)  
2) \(G_{ref}=G_{tangent}(\gamma_{max})=\left.\frac{d\tau_{bb}}{d\gamma}\right|_{\gamma_{max}}\)  
3) \(G_{ref}=G_{secant}(|\Delta\gamma|)\) (reversal-yerel genliğe bağlı – çoğu zaman yanlış ama “neye hassas?” görmek için)  
Peak period ve “secant_g_over_gmax_nrmse” hangi yönde hareket ediyor bakın. citeturn4view0turn8view1  

### Extended Masing kural-4 (önceki çevrim eğrisiyle kesişmede “eski eğriyi takip”) eksik/yanlış

**Belirtiyle uyumu:** Layer-1 stress_path_nrmse ~0.29–0.32 hâlâ büyük. Bu metrik özellikle “path switching” semantiğine aşırı duyarlıdır. Kural-4’ün eksikliği, döngülerin iç geometrisini ve bazı bölgelerde teğeti sistematik biçimde değiştirir. citeturn6search0turn8view1  

**Teknik gerekçe:** Phillips & Hashash (2009) açıkça “önceki cycle unload–reload eğrisiyle kesişmede o eğriyi izle” diyor. Bu, yalnız enerjiyi değil, cycle-to-cycle rijitlik geri kazanımını/çakışmasını da regüle eder. DeepSoil bu familyadaki kodlarla aynı geleneği takip ediyor. citeturn6search0turn7view0  

**En net doğrulama testi:** Tek elemanda aynı strain history için “branch id” (hangi eğriyi takip ediyor) zaman serisini çıkarın. DeepSoil export’unda doğrudan branch-id yok ama stress–strain loop şekli ve özellikle “loop closure” bölgeleri bunun izini taşır. Kural-4 yoksa genellikle iç içe geçmiş loop’larda gereksiz yere backbone’a dönüş veya yeni branch üretimi görülür. citeturn6search0turn8view1  

### Global çözücüye dönen teğet rijitlik (material tangent) doğru branch türevi değil

**Belirtiyle uyumu:** Loop-energy % farkı iyileştirilebiliyor (yani τ(γ) bir şekilde oynuyor) ama peak period sabit kalıyorsa, global dalga yayılımını belirleyen K matrisini oluşturan \(G_t\) beklediğiniz şekilde değişmiyor olabilir. citeturn6search0turn3view0  

**Teknik gerekçe:** Implicit Newmark + Newton iterasyonunda (tipik) eleman rijitliği \(k_e \propto G_t\) olmalı. Eğer siz secant modulus ile K kuruyor (veya bazı durumlarda K’yı “envelope/skeleton”dan sabit alıyor) ama τ update’i farklı bir rule ile yapıyorsanız, enerji metrikleri hareket ederken doğal periyot çok az hareket edebilir. DeepSoil’in “no matrix update” seçeneği viscous C ile ilgilidir; K’nın teğete göre güncellenmesi NL’de hâlâ şarttır. citeturn3view0turn6search0  

**En net doğrulama testi:** Bir run’da her zaman adımında/layer’da şunları loglayın:
- aktif branch türü (backbone / masing / mrdf / previous-cycle),
- τ, γ,
- rapor edilen \(G_t\),
- K assembly’de kullanılan \(G_t^{used}\).  
Bunlar bire bir aynı değilse, periyot kayması “tangent plumbing” problemidir. citeturn6search0turn8view1  

### Sub-increment / time-step altbölme ve interpolasyon semantiği DeepSoil’den farklı

**Belirtiyle uyumu:** DeepSoil time-domain’de step-control (Flexible/Fixed), max strain increment ve sub-increments gibi seçenekler var. Büyük nonlineerlikte, altbölme stratejisi “etkin teğet” tarihini kaydırabilir. citeturn3view0turn1search0  

**Teknik gerekçe:** DeepSoil dokümanı, time-step subdividing ve interpolasyon yöntemlerinin (özellikle “perfect interpolation” vs linear) hareketin yüksek frekans içeriğini ve sayısal davranışı etkileyebileceğini söylüyor; ayrıca literatürde “timestep significance” vurgulanıyor. citeturn3view0turn1search0turn6search0  

**Neden daha aşağıda?** Siz dt uygulamasını zaten düzelttiniz ve period hatası “branch rule sweep” boyunca çok değişmiyor diyorsunuz; bu, birincil sebepten ziyade ikincil bir katkı olma ihtimalini artırır.

### Damping matrisi (frequency independent, update/no-update) formülasyonu hatalı

**Belirtiyle uyumu:** Damping farklılığı genellikle genlik/frekans içeriğini (özellikle yüksek frekans filtrasyonunu) etkiler; rezonans pik periyodunu +%11.7 gibi sistematik kaydırmak için daha zayıf aday. citeturn9search0turn6search0  

**Teknik gerekçe:** Phillips & Hashash (2009) frequency-independent damping matrisini “over-damping at high frequency”yi azaltmak için öneriyor; bu daha çok spektral genlik/şekil etkisi. Park & Hashash (2004) ve ilgili çalışmalar, Rayleigh türü viscous sönümün frekans bağımlılığı ve yüksek frekans filtrasyonu sorununu vurguluyor. citeturn6search0turn9search0turn9search8  

## Concrete implementation roadmap for your repo

Burada “3 deney”i önceliklendiriyorum. Her biri için (i) peak period hatasına saldırma gerekçesi, (ii) hangi metriklerin iyileşmesini bekleriz, (iii) hangi dosyalara dokunma olasılığı yüksek, (iv) eklenmesi gereken state/ara değişkenler.

### MRDF bridge-formu ve teğetinin bire bir uygulanması

**Neden peak period’a saldırır?**  
Bridge-form, unload–reload dalındaki \(G_t\)’yi doğrudan belirler:  
\[
G_t \approx F\,G_t^{Masing} + (1-F)G_{ref}
\]
Salt çarpan uygulaması varsa, \( (1-F)G_{ref} \) katkısı eksik kalır ve K matrisiniz sistematik olarak daha yumuşak olur → periyot uzar. citeturn8view1turn6search0  

**Beklenen iyileşmeler (hipotez doğruysa):**
- **peak_period_diff_pct** belirgin azalmalı (en kritik kabul ölçütü).  
- **layer-1 stress_path_nrmse** düşmeli (branch şekli daha doğru).  
- “secant_g_over_gmax_nrmse” ve “gamma_max_nrmse” aynı anda iyileşme eğilimi göstermeli (en azından birkaçı birlikte). citeturn8view1turn4view0  

**Muhtemel değişiklik dosyaları (sizin verdiğiniz hedeflere göre):**
- `python/dsra1d/materials/mrdf.py` (F(γ_max) ve parametre modeli)  
- `python/dsra1d/materials/hysteretic.py` (branch τ(γ) ve dτ/dγ)  
- Eğer GQ/H backbone fonksiyonu ayrıysa: ilgili backbone/材料 sınıfı.

**Gerekli state değişkenleri (material point):**
- `gamma_rev`, `tau_rev` (reversal noktası)  
- `gamma_max` (history max; monoton artan)  
- `branch_mode` (BACKBONE / MASING / MRDF / MEMORYCURVE)  
- `G_ref` (o adımda kullanılan \(G_{\gamma_{max}}\) – secant/tangent seçimi açık)  
- `F_mrdf` (o adım F).

**Pseudocode (önerilen minimal, DeepSoil’e yakın):**
```text
Given gamma_n, prev state (gamma_{n-1}, tau_{n-1}, branch_mode, gamma_rev, tau_rev, gamma_max)

1) Update gamma_max:
   gamma_max <- max(gamma_max, abs(gamma_n))

2) Detect reversal (direction change):
   if sign(gamma_n - gamma_{n-1}) != sign(gamma_{n-1} - gamma_{n-2}) then
       gamma_rev <- gamma_{n-1}
       tau_rev   <- tau_{n-1}
       branch_mode <- MRDF (if Non-Masing enabled) else MASING
       push reversal record into memory stack (for rule-4)
   end

3) Compute backbone stress tau_bb = F_bb(gamma_n)

4) If branch_mode == BACKBONE:
       tau <- tau_bb
       G_t <- dF_bb/dgamma at gamma_n
   else:
       Δγ <- gamma_n - gamma_rev

       # Masing branch stress around reversal:
       tau_M <- tau_rev + sign(Δγ_target_direction) * 2 * F_bb(Δγ/2)   (rule-2)

       # Choose G_ref:
       G_ref <- G( gamma_max )  # pick secant or tangent; make explicit

       # MRDF reduction factor:
       F <- P1 - P2*(1 - G(gamma_max)/G0)^(P3)   (UIUC)

       # Bridge form:
       tau <- tau_rev + F*( (tau_M - tau_rev) - G_ref*Δγ ) + G_ref*Δγ

       # Tangent (treat F, G_ref constant within step):
       G_M_t <- d/dgamma [ tau_M ] = dF_bb/dgamma evaluated at (Δγ/2)
       G_t   <- F*G_M_t + (1 - F)*G_ref
   end

5) Apply rule-3 (backbone intersection):
   if branch_mode != BACKBONE and (tau crosses tau_bb in current direction):
        branch_mode <- BACKBONE
        tau <- tau_bb
        G_t <- dF_bb/dgamma
   end

6) Apply rule-4 (memory curve intersection):
   if branch_mode in {MASING, MRDF} and intersects previous stored curve:
        branch_mode <- MEMORYCURVE(k)  # follow that curve
        recompute tau, G_t from that curve's parameters
   end

Return tau, G_t, updated state
```

**Bu aşamada “intersects” tanımı (kesişme kriteri):** literatür “intersects curve” der; uygulamada en sağlam yol, iki eğrinin farkında işaret değişimi aramak ve tek adım içinde lineer interpolasyonla kesişim noktasını yakalayıp o noktadan sonra branch_mode’u switch etmektir. citeturn6search0turn8view1  

### Extended Masing kural-4’ün (previous-cycle curve) deterministik uygulanması

**Neden peak period’a saldırır?**  
Kural-4, özellikle “iç içe geçen loop”larda hangi eğrinin takip edildiğini belirler. Yanlış takip, cycle-to-cycle rijitlik “memory”sini değiştirir; bu da belirli frekans bandında ortalama rijitliği kaydırabilir. citeturn6search0turn8view1  

**Beklenen iyileşmeler:**
- **layer-1 stress_path_nrmse** belirgin düşmeli (en doğrudan).  
- **loop_energy_pct_diff** daha stabil ve daha düşük olmalı.  
- Peak period kayması bir miktar azalabilir; ama asıl sinyal stress-path’te gelir. citeturn6search0turn8view1  

**Dosyalar:**
- `python/dsra1d/materials/hysteretic.py` (branch hafızası ve kesişme semantiği)

**State önerisi: “curve registry”**
- Her reversal’da bir “curve descriptor” kaydedin:
  - `gamma_rev, tau_rev`
  - `mode` (MASING/MRDF)
  - `gamma_max_at_creation`, `F_at_creation`, `G_ref_at_creation`
  - `direction` (unload/reload)
- Sonraki adımlarda, aktif τ(γ) ile önceki curve τ_k(γ) arasında “kesişme” arayın.

**Kesişme analizi (sayısal pratik):**
- Her zaman adımında yalnız “en son 1–3 curve” ile kontrol edin (tam yığın pahalı).
- Kesişme kontrolü: \(\Delta_k = \tau_{active}(\gamma) - \tau_k(\gamma)\).  
  İşaret değişimi varsa, switch.

Bu, DeepSoil’in “cross previous curve, follow previous” kuralını en az sürprizle taklit eder. citeturn6search0turn8view1  

### Global çözücüde kullanılan teğetin “aktif branch türevi” olduğunun garanti edilmesi

**Neden peak period’a saldırır?**  
Peak period, dalga yayılımının efektif Vs tarihine ve dolayısıyla **K(t)**’ye duyarlı. Eğer K(t) için kullandığınız modulus, histerezis branch’ini değil envelope/secant’ı kullanıyorsa, branch deneylerinizin çoğu periyodu değiştirmez. Bu, sizin “energy iyileşiyor ama peak period sabit” gözleminize çok iyi uyar. citeturn3view0turn6search0turn8view1  

**Beklenen iyileşmeler:**
- **peak_period_diff_pct** en çok bu adımda hareket etmeli (eğer sorun plumbing ise).  
- **gamma_max_nrmse** ve “secant_g_over_gmax_nrmse” birlikte toparlanmalı (rijitlik doğruysa strain de değişir). citeturn6search0turn8view1  

**Dosyalar (sizin hedef listenizle uyumlu):**
- `python/dsra1d/newmark_nonlinear.py` (Newton iterasyonunda K_eff kurulumu: \(K_{eff}=K_t+a_0M+a_1C\))  
- `python/dsra1d/nonlinear.py` (assembly ve material update sırası)  
- `python/dsra1d/materials/hysteretic.py` (dτ/dγ’nin doğru dönmesi)

**“No matrix update” ile karışmasın:** DeepSoil UI’da “damping matrix update yes/no” ayrı bir seçenektir; bu C içindir. Nonlineer çözümde K’nin teğete göre güncellenmesi yine beklenir. citeturn3view0turn1search0turn6search0  

**Uygulama kontrol listesi (kısa):**
- Material update → τ ve \(G_t\) üret  
- Element stiffness \(k_e \propto G_t\) ile assemble et  
- Newton iterasyonunda her iterasyonda \(G_t\) refresh ediliyor mu?  
- Yoksa, en azından her subincrement’te refresh ediliyor mu? (DeepSoil’de subincrement seçenekleri bunu ima eder.) citeturn3view0turn6search0  

## What not to waste time on

- “Input motion application / dt / rigid-outcrop semantiği” üzerine geri dönmek: bunları zaten düzelttiniz ve artık ana mismatch driver değil (metrikleriniz de bunu söylüyor).  
- Monotonik backbone’u (θ seti) tekrar kurcalamak: hem sizin bulgunuz hem literatür perspektifi backbone’un doğru olup unload–reload’un kritik olduğunu söylüyor. citeturn6search0turn8view1  
- Tek bir **sabit reload_factor** ile sonsuz sweep: DeepSoil MRDF’de unload–reload davranışı **γ_max tarihine bağlı** ve bridge-form ile teğet karışımı yapıyor; bu yüzden tek skalerle tüm metrikleri aynı anda kapatamamanız beklenen bir şey. citeturn4view0turn0search32turn8view1  
- “Damping matrisi ayarıyla peak period’u %10+ kaydırırım” yaklaşımı: DeepSoil’in viscous damping literatürü (Park & Hashash 2004; Phillips & Hashash 2009) daha çok yüksek frekans sönümleme/filtremeyi hedefler; dominant periyot kayması için birincil kaldıraç değildir. citeturn9search0turn6search0  
- Görselleştirme/UI/raporlamayı genişletmek: compare pipeline’ınız zaten güçlü; şu aşamada en fazla “branch id / F(γ_max) / G_ref / used tangent” gibi çok spesifik debug kanalları eklemek değerli, ama tooling redesign değil. citeturn6search0turn8view1