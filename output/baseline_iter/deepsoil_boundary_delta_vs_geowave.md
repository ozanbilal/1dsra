# DeepSoil Boundary Delta vs GeoWave

## DeepSoil DB Pair
- Elastic peak RS: `1.181128 g` at `0.163884 s`
- Rigid peak RS: `2.565321 g` at `0.185573 s`
- Elastic / rigid peak RS ratio: `0.460421`
- Elastic vs rigid peak-period shift: `-11.687584%`
- Elastic / rigid surface PGA ratio: `0.606463`
- Elastic / rigid PGD ratio: `0.491265`

## GeoWave Clean Pair
- Elastic / rigid peak RS ratio: `1.0187699443702471`
- Elastic vs rigid peak-period shift: `3.8853177865280846`%
- Elastic / rigid surface PGA ratio: `1.48349444274311`
- Applied input history NRMSE: `0.05713149409835331`
- Applied input PSA NRMSE: `0.17061324322917135`

## Verdict
- DeepSoil: elastic halfspace reduces peak spectral amplification and shifts the peak to a shorter period relative to rigid.
- GeoWave: the current clean pair slightly increases peak spectral amplification and shifts the peak to a longer period relative to rigid.
- Conclusion: boundary sensitivity parity is not closed; the current GeoWave rigid/elastic response has the wrong directional signature against DeepSoil for the primary spectral delta.
