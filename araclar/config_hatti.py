"""Config hattı ölçümü: bizim config yamalarımız 1.4.07'nin config'inde ne durumda (GEC-01).

1.4.07'nin config'i (C₁₄₀₇) upstream'deki gibi kurulur: taban `config/game_config_20120826.json` (upstream'in
`main.json`'u ile birebir aynı), üstüne upstream'in yamaları ve `goals.json`. Her bir yamamızın her işlemi
C₁₄₀₇'ye karşı sınıflanır:

- **aynı**: işlemin koyacağı değer C₁₄₀₇'de zaten var;
- **kapsanıyor**: C₁₄₀₇'deki eş, bizim değerimizin bütün alanlarını aynı değerle içeriyor (fazlası olabilir);
- **farklı**: aynı yerde (aynı anahtar, aynı `id` ya da yerelleştirmede aynı `name`) başka bir değer var;
- **yeni**: C₁₄₀₇'de karşılığı yok;
- **yolu yok**: işlemin yolu C₁₄₀₇'de bulunmuyor (yama uygulanamaz).

Yamanın hükmü: hepsi aynı ya da kapsanıyorsa **gider**, farklı varsa **çatışır** (karar gerekir), yalnızca aynı ve yeniyse
**kalır**, yolu olmayan varsa **uygulanamaz**.

Yamanın dokunduğu config anahtarlarının istemcide geçip geçmediğine de bakılır (dize havuzunda adın bulunması;
◐: adın geçmesi okunduğunu kanıtlamaz). 0926'da geçmeyip 1.4.07'de geçen anahtar o yamayı "canlandırabilir".

Komut satırı:
    python araclar/config_hatti.py --yama <upstream config/patch> --hedefler goals.json \\
        --istemci 1.4.07.swf --eski 0926.swf [--md docs/inceleme/1407-config-hatti.md]
"""

import argparse
import json
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "araclar"))
import abc_okur  # noqa: E402
import ceviri_kapsami  # noqa: E402

BIZIM_YAMALAR = os.path.join(KOK, "config", "patch")
_YOK = object()


def _yol(isaretci):
    return [p.replace("~1", "/").replace("~0", "~") for p in isaretci.split("/")[1:]]


def _esini_bul(liste, deger, kap_adi):
    """Listede değerin eşini bulur: yerelleştirmede `name`, başka yerde `id` ile."""
    if not isinstance(deger, dict):
        return deger if deger in liste else _YOK
    anahtar = "name" if kap_adi == "localization_strings" else "id"
    if anahtar not in deger:
        return deger if deger in liste else _YOK
    for x in liste:
        if isinstance(x, dict) and x.get(anahtar) == deger[anahtar]:
            return x
    return _YOK


def _kiyas(var, deger):
    if var is _YOK:
        return "yeni"
    if var == deger:
        return "aynı"
    if isinstance(var, dict) and isinstance(deger, dict) and all(k in var and var[k] == v for k, v in deger.items()):
        return "kapsanıyor"
    return "farklı"


def _alan_farki(var, deger):
    """İki sözlükte değeri farklı ya da yalnızca bizde olan alanların adları."""
    if isinstance(var, dict) and isinstance(deger, dict):
        return sorted(k for k, v in deger.items() if var.get(k, _YOK) != v)
    return ["<değer>"]


def islem_durumu(config, islem):
    """(durum, ayrıntı): yukarıdaki dört durumdan biri; liste değerlerinde öğe öğe sayım."""
    yol = _yol(islem["path"])
    kap, ust_ad = config, None
    for parca in yol[:-1]:
        if isinstance(kap, dict) and parca in kap:
            kap, ust_ad = kap[parca], parca
        elif isinstance(kap, list) and parca.isdigit() and int(parca) < len(kap):
            kap, ust_ad = kap[int(parca)], ust_ad
        else:
            return "yolu yok", None
    son = yol[-1] if yol else None
    op, deger = islem["op"], islem.get("value")
    if isinstance(kap, list):
        if op == "add":
            var = _esini_bul(kap, deger, ust_ad)
            durum = _kiyas(var, deger)
            return durum, ({"alanlar": _alan_farki(var, deger)} if durum == "farklı" else None)
        if not son.isdigit() or int(son) >= len(kap):
            return "yolu yok", None
        var = kap[int(son)]
    elif isinstance(kap, dict):
        var = kap.get(son, _YOK)
    else:
        return "yolu yok", None
    if op == "remove":
        return ("farklı" if var is not _YOK else "aynı"), None
    if op == "replace" and var is _YOK:
        return "yolu yok", None
    durum = _kiyas(var, deger)
    ayrinti = None
    if durum == "farklı" and isinstance(deger, list) and isinstance(var, list):
        ayrinti = {"aynı": 0, "kapsanıyor": 0, "farklı": 0, "yeni": 0}
        for x in deger:
            ayrinti[_kiyas(_esini_bul(var, x, son), x)] += 1
    elif durum == "farklı":
        ayrinti = {"alanlar": _alan_farki(var, deger)}
    return durum, ayrinti


def hukum(sayim):
    if sayim.get("yolu yok"):
        return "uygulanamaz"
    if sayim.get("farklı"):
        return "çatışır"
    if sayim.get("yeni"):
        return "kalır"
    return "gider"


def dokunulan_anahtarlar(yama):
    """Yamanın dokunduğu config adları: üst anahtar ve `globals` altındakiler."""
    adlar = set()
    for islem in yama:
        yol = _yol(islem["path"])
        if yol:
            adlar.add(yol[0])
            if yol[0] == "globals" and len(yol) > 1:
                adlar.add(yol[1])
    return adlar


def istemci_dizeleri(veri):
    dizeler = set()
    for abc in abc_okur.swf_abc(veri):
        dizeler |= {d for d in abc.dizeler if d}
    return dizeler


def olc(c1407, yama_klasoru=BIZIM_YAMALAR, yeni_dizeler=None, eski_dizeler=None):
    satirlar = []
    for ad in sorted(os.listdir(yama_klasoru)):
        if not ad.endswith(".json"):
            continue
        with open(os.path.join(yama_klasoru, ad), encoding="utf-8") as f:
            yama = json.load(f)
        sayim, ayrintilar, alanlar = {}, [], {}
        for islem in yama:
            durum, ayrinti = islem_durumu(c1407, islem)
            sayim[durum] = sayim.get(durum, 0) + 1
            if ayrinti and "alanlar" in ayrinti:
                for a in ayrinti["alanlar"]:
                    alanlar[a] = alanlar.get(a, 0) + 1
            elif ayrinti:
                ayrintilar.append((islem["path"], ayrinti))
        anahtarlar = sorted(dokunulan_anahtarlar(yama))
        okuma = {}
        if yeni_dizeler is not None and eski_dizeler is not None:
            okuma = {k: (k in eski_dizeler, k in yeni_dizeler) for k in anahtarlar}
        satirlar.append({"yama": ad[:-5], "islem": len(yama), "sayim": sayim, "hukum": hukum(sayim),
                         "ayrinti": ayrintilar, "alanlar": alanlar, "anahtarlar": anahtarlar, "okuma": okuma})
    return satirlar


def markdown(satirlar, notlar=()):
    s = ["# 1.4.07 config hattı: bizim yamalarımız", "",
         "Bu dosya `araclar/config_hatti.py` ile üretilir; elle düzenlenmez.", ""]
    s += list(notlar) + [""] if notlar else []
    s += ["| Yama | İşlem | aynı | kapsanıyor | farklı | yeni | yolu yok | Hüküm | Farklı alanlar (işlem sayısı) |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in satirlar:
        c = r["sayim"]
        sirali = sorted(r["alanlar"].items(), key=lambda x: (-x[1], x[0]))
        alanlar = ", ".join("`%s` %d" % (a, n) for a, n in sirali[:8])
        if len(sirali) > 8:
            alanlar += " … (+%d alan)" % (len(sirali) - 8)
        s.append("| `%s` | %d | %d | %d | %d | %d | %d | **%s** | %s |" % (
            r["yama"], r["islem"], c.get("aynı", 0), c.get("kapsanıyor", 0), c.get("farklı", 0),
            c.get("yeni", 0), c.get("yolu yok", 0), r["hukum"], alanlar or "—"))
    s += ["", "## Bütün listeyi koyan işlemlerde öğe sayımı", ""]
    s += ["| Yama | Yol | aynı | kapsanıyor | farklı | yeni |", "|---|---|---|---|---|---|"]
    for r in satirlar:
        for yol, a in r["ayrinti"]:
            s.append("| `%s` | `%s` | %d | %d | %d | %d |" % (r["yama"], yol, a["aynı"], a["kapsanıyor"],
                                                          a["farklı"], a["yeni"]))
    if any(r["okuma"] for r in satirlar):
        s += ["", "## Dokunulan config adları istemcide geçiyor mu (◐)", "",
              "| Yama | Ad | 0926 | 1.4.07 |", "|---|---|---|---|"]
        for r in satirlar:
            for k, (eski, yeni) in sorted(r["okuma"].items()):
                s.append("| `%s` | `%s` | %s | %s |%s" % (r["yama"], k, "✔" if eski else "—", "✔" if yeni else "—",
                                                         " **canlanır**" if yeni and not eski else ""))
    return "\n".join(s) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--yama", required=True, action="append", help="upstream'in config/patch klasörü")
    ap.add_argument("--hedefler", help="upstream'in goals.json'u")
    ap.add_argument("--istemci", help="1.4.07 SWF (ad taraması için)")
    ap.add_argument("--eski", help="0926 SWF (ad taraması için)")
    ap.add_argument("--md")
    a = ap.parse_args(argv)
    c1407 = ceviri_kapsami.config_kur(a.yama)
    if a.hedefler:
        with open(a.hedefler, encoding="utf-8") as f:
            c1407["goals"] = json.load(f)
    yeni = eski = None
    if a.istemci and a.eski:
        with open(a.istemci, "rb") as f:
            yeni = istemci_dizeleri(f.read())
        with open(a.eski, "rb") as f:
            eski = istemci_dizeleri(f.read())
    satirlar = olc(c1407, BIZIM_YAMALAR, yeni, eski)
    for r in satirlar:
        print("%-18s %-12s %s" % (r["yama"], r["hukum"], r["sayim"]))
    if a.md:
        notlar = ["- C₁₄₀₇: taban + upstream `54df29e` `config/patch` (%s)%s." % (
            ", ".join(sorted(x[:-5] for y in a.yama for x in os.listdir(y) if x.endswith(".json"))),
            " + `goals.json`" if a.hedefler else "")]
        with open(a.md, "w", encoding="utf-8", newline="\n") as f:
            f.write(markdown(satirlar, notlar))
    return satirlar


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
