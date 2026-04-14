# DEEPSOIL Equivalent Reference Pack

Bu klasör, GeoWave/1DSRA için DEEPSOIL-benzeri örnek model setini içerir.

Amaç:
- `linear_reference.yml` ile lineer dalga yayılımını,
- `eql_reference.yml` ile eşdeğer-doğrusal iterasyonu,
- `nonlinear_reference.yml` ile MKZ/GQH zaman tanım alanı davranışını,
- `effective_stress_reference.yml` ile efektif gerilme akışını
tek bir referans pakette göstermek.

Ortak motion:
- `../motions/sample_motion.csv`

Önerilen çalışma klasörü:
- `examples/output/deepsoil_equivalent/`

Smoke validation:
- lineer, EQL, nonlinear ve effective-stress referanslar 2026-03-19 tarihinde CLI ile çalıştırıldı ve çıktı üretti.
- effective-stress örneği, repo içindeki OpenSees çözümleyicisini kullanarak tamamlandı.
Bu klasör, doğrulama ve demonstrasyon amaçlıdır; ürünün zorunlu çalışma akışının parçası değildir.

Çalıştırma örnekleri:

```bash
python -m dsra1d.cli.main run --config examples/deepsoil_equivalent/linear_reference.yml --motion examples/motions/sample_motion.csv --out examples/output/deepsoil_equivalent/linear
python -m dsra1d.cli.main run --config examples/deepsoil_equivalent/eql_reference.yml --motion examples/motions/sample_motion.csv --out examples/output/deepsoil_equivalent/eql
python -m dsra1d.cli.main run --config examples/deepsoil_equivalent/nonlinear_reference.yml --motion examples/motions/sample_motion.csv --out examples/output/deepsoil_equivalent/nonlinear
python -m dsra1d.cli.main run --config examples/deepsoil_equivalent/effective_stress_reference.yml --motion examples/motions/sample_motion.csv --out examples/output/deepsoil_equivalent/effective_stress
```
