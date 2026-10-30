"""Oyun varlıklarının indirildiği koruma deposu, sabitlenmiş commit'i ve oyunun istemcisi.

Varlıklar AcidCaos/socialemperors deposunun assets/ klasöründen iner. Dal adı değişebilir; dosyalar
sessizce değişmesin diye bir commit'e sabitlenir (KYN-03). Bu modül yan etkisizdir: sunucuyu başlatmadan
betiklerden de içe aktarılabilir.
"""

DEPO = "AcidCaos/socialemperors"
# nerroth-rewrite dalı, 1.4.07 istemcisinin yamalı hâlini taşıyan commit (GEC-02). Varlık ağacı 0.04a'nın
# (f642e0b) içerik olarak üst kümesidir: ortak 4.478 dosyada blob farkı 0, 347 yeni dosya (KYN-03, GEC-01).
COMMIT = "54df29e1bc5905c72a55a5fd0dda449e7a419019"
DEPO_URL = f"https://github.com/{DEPO}.git"
HAM_KOK = f"https://raw.githubusercontent.com/{DEPO}/{COMMIT}/"
HAM_VARLIK = HAM_KOK + "assets/{path}"

# Oyunun tek istemcisi (KAR-08). Social Point'in SWF'si GPL kapsamında değildir; upstream'in yamalı hâli
# olduğu gibi kullanılır ve özeti denetlenir: özet uymayan dosya sunulmaz.
ISTEMCI = "SocialEmpires1.4.07sec_fixed.swf"
ISTEMCI_YOLU = "flash/" + ISTEMCI
ISTEMCI_SHA256 = "0e4cc17893b1f266b920213d75b0c943f32c3c0d4cf9b994f6a88cab25c76a15"
ISTEMCI_BOYUTU = 4288777
