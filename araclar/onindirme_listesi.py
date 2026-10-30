"""Çevrimdışı paketin dosya listesini üretir: config/onindirme.tsv ("yol<TAB>bayt<TAB>öncelik").

Arşivdeki (AcidCaos/socialemperors, assets/) 4.479 dosyanın ~1,3 GB'ı bu sürümde kullanılmaz: başka oyun
sürümlerinin SWF'leri ve yapılandırmada geçmeyen bina/birim çizimleri. Liste yalnızca şunları alır:
- flash/: yükleyici ve oyun (SocialEmpires0926bsec.swf),
- buildingsprites/: yapılandırmadaki (yamalarla) eşya ve büyülerin img_name'i olan çizimler,
- geri kalan klasörlerin hepsi (küçük resimler, efektler, müzik...).
Arşivdeki boş dosyalar ve sunucunun hiç o adla sunmadığı dosyalar (varliklar.ESDEGERLER) alınmaz.

Sıra önemlidir; indirme yarıda kalsa da en çok kullanılanlar inmiş olur: önce oyun, arayüz, efekt ve müzik;
sonra mağazadaki eşyaların, büyülerin ve haritada beliren kayıp eşyaların çizimleri ile küçük resimler; en son geri kalan çizimler. Öncelik 0-1
"temel paket" (~180 MB), hepsi "tam paket"tir (oyun/onindirme.py).

Kullanım:
    python araclar/onindirme_listesi.py [--liste boyutlar.tsv]

--liste verilmezse dosya adları git ile (içerik indirilmeden), boyutlar HEAD istekleriyle alınır.
"""

import argparse
import ast
import concurrent.futures
import os
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

DEPO = "https://github.com/AcidCaos/socialemperors.git"
HAM = "https://raw.githubusercontent.com/AcidCaos/socialemperors/main/"
CIKTI = os.path.join(KOK, "config", "onindirme.tsv")
OYUN_DOSYALARI = {"flash/SELoader.swf", "flash/SocialEmpires0926bsec.swf"}


def arsiv_dosyalari():
    """[(yol, bayt)]; yol 'assets/' olmadan."""
    with tempfile.TemporaryDirectory(prefix="se-liste-") as gecici:
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--no-checkout", DEPO, gecici],
                       check=True)
        adlar = subprocess.run(["git", "-C", gecici, "ls-tree", "-r", "--name-only", "HEAD", "assets"],
                               check=True, capture_output=True, text=True).stdout.split("\n")

    def boyut(yol):
        istek = urllib.request.Request(HAM + urllib.parse.quote(yol), method="HEAD")
        with urllib.request.urlopen(istek, timeout=60) as yanit:
            return yol[len("assets/"):], int(yanit.headers["Content-Length"])

    with concurrent.futures.ThreadPoolExecutor(32) as havuz:
        return list(havuz.map(boyut, [a for a in adlar if a]))


def varlik_esdegerleri():
    """oyun/varliklar.py'deki ESDEGERLER; modül içe aktarılmaz (sunucuyu başlatır)."""
    with open(os.path.join(KOK, "oyun", "varliklar.py"), encoding="utf-8") as f:
        for dugum in ast.parse(f.read()).body:
            if isinstance(dugum, ast.Assign) and getattr(dugum.targets[0], "id", None) == "ESDEGERLER":
                return ast.literal_eval(dugum.value)
    raise LookupError("ESDEGERLER bulunamadı")


def gerekenler(dosyalar, config, esdegerler):
    """Seçilen dosyalar, indirme sırasıyla: [(yol, bayt, öncelik)]."""
    cizimler = {i["img_name"] for i in config["items"] if i.get("img_name")}
    buyuler = {m["img_name"] for m in config.get("magics", []) if m.get("img_name")}
    # Mağazadakiler ve haritada rastgele beliren kayıp eşyalar (yaralı inek, yalnız şövalye...; alt kategori 91)
    magazada = {i["img_name"] for i in config["items"] if i.get("img_name")
                and (str(i.get("in_store")) == "1" or str(i.get("subcategory_id")) == "91")}
    secilen = []
    for yol, bayt in dosyalar:
        klasor, ad = yol.split("/", 1)[0], os.path.splitext(os.path.basename(yol))[0]
        if bayt == 0 or yol in esdegerler or (klasor == "flash" and yol not in OYUN_DOSYALARI):
            continue
        if klasor == "buildingsprites":
            if ad not in cizimler | buyuler:
                continue
            oncelik = 1 if ad in magazada | buyuler else 2
        elif klasor == "buildingthumbs":
            oncelik = 1
        else:
            oncelik = 0
        secilen.append((oncelik, yol, bayt))
    return [(yol, bayt, oncelik) for oncelik, yol, bayt in sorted(secilen)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--liste", help="'bayt<TAB>assets/yol' satırları (önceden ölçülmüş)")
    secenek = ap.parse_args()
    if secenek.liste:
        with open(secenek.liste, encoding="utf-8") as f:
            dosyalar = [(y.strip()[len("assets/"):], int(b)) for b, y in (s.split("\t", 1) for s in f if s.strip())]
    else:
        dosyalar = arsiv_dosyalari()
    from oyun.config import get_game_config
    secilen = gerekenler(dosyalar, get_game_config(), varlik_esdegerleri())
    with open(CIKTI, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Çevrimdışı paket: araclar/onindirme_listesi.py üretir. yol<TAB>bayt<TAB>öncelik (0-1: temel)\n")
        f.writelines(f"{yol}\t{bayt}\t{oncelik}\n" for yol, bayt, oncelik in secilen)
    temel = sum(b for _, b, o in secilen if o <= 1)
    toplam = sum(b for _, b, _ in secilen)
    print(f"[+] {len(secilen)}/{len(dosyalar)} dosya; temel {temel / 1e6:.0f} MB, tam {toplam / 1e6:.0f} MB -> {CIKTI}")
