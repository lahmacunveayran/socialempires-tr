"""İstemcinin gönderdiği komutlar (G) ile sunucunun işledikleri (H): küme farkı ve argüman uyumu.

G, istemcinin bayt kodundaki `addCommand({cmd: ..., args: [...]})` çağrılarından çıkarılır
(`araclar/abc_okur.py`); her komut için çağrı yerleri ve gönderilen argüman sayıları tutulur.
Ayrıca `Constants` sınıfındaki `CMD_*` sabitleri ve kodda başvurulanları sayılır.

H, `oyun/komutlar.py`'deki `@komut(...)` işleyicilerinden **çalıştırılmadan** (AST ile) çıkarılır:
işleyicinin belge dizesindeki `[...]` argüman listesi ve `a.tam(i)`, `a.metin(i)` gibi okumalardaki en
büyük sıra. İşleyici `a`'yı aynı dosyadaki bir yardımcıya geçiriyorsa yardımcının okumaları da sayılır.

Kapılar (`docs/YOL_HARITASI_1407.md` §2.1):
- kapsama: `|G ∖ H| = 0`;
- imza: sunucunun okuduğu en büyük sıra < istemcinin o komutta gönderdiği en büyük argüman sayısı.

Komut satırı:
    python araclar/komut_imzalari.py istemci.swf [--eski 0926.swf] [--md docs/inceleme/1407-komutlar.md]
        [--json docs/inceleme/1407-komutlar.json]

JSON dosyası istemcinin komut listesini depoda tutar; böylece SWF'si olmayan CI da kapıları sınar
(`tests/test_komut_imzalari.py`).
"""

import argparse
import ast
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import abc_okur  # noqa: E402

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KOMUTLAR_PY = os.path.join(KOK, "oyun", "komutlar.py")
ARG_YONTEMLERI = {"ham", "tam", "ondalik", "metin", "json"}


# ---------------------------------------------------------------------------
# İstemci (G)
# ---------------------------------------------------------------------------

def istemci_komutlari(veri: bytes):
    """SWF baytlarından {komut: [çağrı yeri]}, çözülemeyenler ve CMD_ sabitleri.

    Çağrı yeri: {"yer": "Sınıf/yöntem@ofset", "argsayisi": int|None, "args": [ifade]}.
    """
    komutlar = defaultdict(list)
    cozulemeyen = []
    sabit_tanimli, sabit_kullanilan = {}, set()
    for abc in abc_okur.swf_abc(veri):
        sabitler = abc.sabitler("Constants")
        cmd_sabitleri = {k: v for k, v in sabitler.items() if k.startswith("CMD_")}
        sabit_tanimli.update(cmd_sabitleri)
        adlar = abc.yontem_adlari()
        for c in abc.cagrilar("addCommand"):
            if not c.argumanlar or not isinstance(c.argumanlar[0], abc_okur.Nesne):
                continue  # yönetici konsolunun addCommand('ad', işlev) çağrıları
            alanlar = {abc_okur.yaz(k).strip("'"): d for k, d in c.argumanlar[0]}
            if "cmd" not in alanlar:
                continue
            yer = "%s@%d" % (adlar.get(c.yontem, "yontem%d" % c.yontem), c.ofset)
            ad = _komut_adi(alanlar["cmd"], cmd_sabitleri)
            args = alanlar.get("args")
            kayit = {"yer": yer,
                     "argsayisi": len(args) if isinstance(args, abc_okur.Dizi) else None,
                     "args": [abc_okur.yaz(x) for x in args] if isinstance(args, abc_okur.Dizi) else
                     [abc_okur.yaz(args)] if args is not None else []}
            if ad is None:
                cozulemeyen.append(dict(kayit, cmd=abc_okur.yaz(alanlar["cmd"])))
            else:
                komutlar[ad].append(kayit)
        sabit_kullanilan |= _kullanilan_cmd_sabitleri(abc, cmd_sabitleri)
    return {"komutlar": dict(komutlar), "cozulemeyen": cozulemeyen,
            "sabit_tanimli": sabit_tanimli, "sabit_kullanilan": sabit_kullanilan}


def _komut_adi(deger, cmd_sabitleri):
    if isinstance(deger, abc_okur.Sabit) and isinstance(deger.deger, str):
        return deger.deger
    m = re.fullmatch(r"(?:Constants\.)?(CMD_\w+)", str(deger))
    if m and m.group(1) in cmd_sabitleri:
        return cmd_sabitleri[m.group(1)]
    return None


def _kullanilan_cmd_sabitleri(abc, cmd_sabitleri):
    """Constants sınıfı dışında kodda okunan CMD_ sabitlerinin adları."""
    sinif_init = set()
    for i, ornek in enumerate(abc.ornekler):
        if abc.ad(ornek["ad"]) == "Constants":
            sinif_init = {abc.siniflar[i][0], ornek["iinit"]}
    kullanilan = set()
    for yontem, g in abc.govdeler.items():
        if yontem in sinif_init:
            continue
        for isl in abc.coz(g).values():
            if isl.ad in ("getproperty", "getlex") and abc.ad(isl.isl[0]) in cmd_sabitleri:
                kullanilan.add(abc.ad(isl.isl[0]))
    return kullanilan


# ---------------------------------------------------------------------------
# Sunucu (H)
# ---------------------------------------------------------------------------

def sunucu_komutlari(yol=KOMUTLAR_PY):
    """{komut: {"islev", "belge_args", "en_buyuk_sira", "satir"}} (dosya çalıştırılmadan okunur)."""
    with open(yol, encoding="utf-8") as f:
        agac = ast.parse(f.read())
    islevler = {n.name: n for n in agac.body if isinstance(n, ast.FunctionDef)}
    cikti = {}
    for islev in islevler.values():
        adlar = _komut_adlari(islev)
        if not adlar:
            continue
        param = islev.args.args[1].arg if len(islev.args.args) > 1 else "a"
        sira = _en_buyuk_sira(islev, param, islevler, set())
        belge = _belge_args(ast.get_docstring(islev) or "")
        for ad in adlar:
            cikti[ad] = {"islev": islev.name, "belge_args": belge, "en_buyuk_sira": sira,
                         "satir": islev.lineno}
    return cikti


def _komut_adlari(islev):
    adlar = []
    for d in islev.decorator_list:
        if isinstance(d, ast.Call) and getattr(d.func, "id", None) == "komut":
            adlar += [x.value for x in d.args if isinstance(x, ast.Constant)]
    return adlar


def _en_buyuk_sira(islev, param, islevler, gezilen):
    """`param.tam(i)` gibi okumaların en büyük sırası (-1: hiç okumaz). Yardımcılara geçirilen
    `param` izlenir; sıra sabit değilse None (bilinemez)."""
    if islev.name in gezilen:
        return -1
    gezilen = gezilen | {islev.name}
    en = -1
    for n in ast.walk(islev):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == param \
                and f.attr in ARG_YONTEMLERI and n.args:
            if not isinstance(n.args[0], ast.Constant):
                return None
            en = max(en, n.args[0].value)
            continue
        hedef = getattr(f, "id", None)
        for i, arg in enumerate(n.args):
            if isinstance(arg, ast.Name) and arg.id == param:
                if hedef not in islevler:
                    return None
                yardimci = islevler[hedef]
                if i >= len(yardimci.args.args):
                    return None
                alt = _en_buyuk_sira(yardimci, yardimci.args.args[i].arg, islevler, gezilen)
                if alt is None:
                    return None
                en = max(en, alt)
    return en


def _belge_args(belge):
    """Belge dizesinin ilk satırındaki `[a, b, (c)]` listesinden (zorunlu, toplam) sayıları."""
    m = re.match(r"\s*\[(.*?)\]", belge)
    if not m:
        return None
    ic = m.group(1).strip()
    if not ic:
        return (0, 0)
    parcalar = _ust_duzey_virgul(ic)
    zorunlu = sum(1 for p in parcalar if not p.strip().startswith("("))
    return (zorunlu, len(parcalar))


def _ust_duzey_virgul(metin):
    parcalar, derinlik, bas = [], 0, 0
    for i, ch in enumerate(metin):
        if ch in "([{":
            derinlik += 1
        elif ch in ")]}":
            derinlik -= 1
        elif ch == "," and derinlik == 0:
            parcalar.append(metin[bas:i])
            bas = i + 1
    parcalar.append(metin[bas:])
    return parcalar


# ---------------------------------------------------------------------------
# Karşılaştırma ve tablo
# ---------------------------------------------------------------------------

def karsilastir(istemci, sunucu):
    """Her G komutu için satır; kapsama ve imza kapılarının sonuçları."""
    satirlar, eksik, uyumsuz = [], [], []
    for ad in sorted(istemci["komutlar"]):
        yerler = istemci["komutlar"][ad]
        sayilar = sorted({y["argsayisi"] for y in yerler if y["argsayisi"] is not None})
        s = sunucu.get(ad)
        durum = "var"
        if s is None:
            durum = "eksik"
            eksik.append(ad)
        elif sayilar and s["en_buyuk_sira"] is not None and s["en_buyuk_sira"] >= max(sayilar):
            durum = "imza"
            uyumsuz.append(ad)
        satirlar.append({"ad": ad, "yer_sayisi": len(yerler), "argsayilari": sayilar,
                         "ornek": yerler[0], "sunucu": s, "durum": durum})
    G, H = set(istemci["komutlar"]), set(sunucu)
    return {"satirlar": satirlar, "eksik": eksik, "uyumsuz": uyumsuz,
            "G": G, "H": H, "fazla": sorted(H - G)}


def surum_farki(yeni, eski):
    """İki istemcinin komut kümeleri ve argüman sayısı değişenler."""
    Y, E = set(yeni["komutlar"]), set(eski["komutlar"])

    def sayilar(k, ad):
        return sorted({y["argsayisi"] for y in k["komutlar"][ad] if y["argsayisi"] is not None})
    degisen = [(ad, sayilar(eski, ad), sayilar(yeni, ad)) for ad in sorted(Y & E)
               if sayilar(eski, ad) != sayilar(yeni, ad)]
    return {"yeni": sorted(Y - E), "kalkan": sorted(E - Y), "degisen": degisen}


def json_verisi(ad, sha, istemci):
    """Depoda tutulan makinece okunur liste: komut -> çağrı yerleri ve argüman sayıları."""
    st = istemci["sabit_tanimli"]
    return {
        "istemci": ad,
        "sha256": sha,
        "uretici": "araclar/komut_imzalari.py",
        "komutlar": {k: [{"yer": y["yer"], "argsayisi": y["argsayisi"]} for y in v]
                     for k, v in sorted(istemci["komutlar"].items())},
        "kullanilmayan_sabitler": {k: st[k] for k in sorted(set(st) - istemci["sabit_kullanilan"])},
    }


def json_oku(yol):
    """json_verisi'nin yazdığı dosyadan istemci_komutlari biçimi (karsilastir'a verilebilir)."""
    import json
    with open(yol, encoding="utf-8") as f:
        veri = json.load(f)
    return veri, {"komutlar": veri["komutlar"]}


def _hucre(metin):
    return str(metin).replace("|", "\\|").replace("\n", " ")


def markdown(ad, sha, istemci, sonuc, fark=None, eski_ad=None):
    G, H = sonuc["G"], sonuc["H"]
    st = istemci["sabit_tanimli"]
    satir = [
        "# %s: istemci komutları ve sunucu işleyicileri" % ad,
        "",
        "Bu dosya `araclar/komut_imzalari.py` ile üretilir; elle düzenlenmez.",
        "",
        "- İstemci: `%s`, SHA-256 `%s`." % (ad, sha),
        "- Sunucu: `oyun/komutlar.py` (`@komut` işleyicileri, AST ile okunur).",
        "",
        "## Özet",
        "",
        "| Ölçü | Değer |",
        "|---|---|",
        "| G: istemcinin gönderdiği komut (çağrı yerinden) | %d |" % len(G),
        "| `addCommand` çağrı yeri | %d |" % sum(len(v) for v in istemci["komutlar"].values()),
        "| `Constants.CMD_*` sabiti / farklı değer | %d / %d |" % (len(st), len(set(st.values()))),
        "| Kodda okunan `CMD_*` sabiti | %d |" % len(istemci["sabit_kullanilan"]),
        "| Komut adı çözülemeyen çağrı | %d |" % len(istemci["cozulemeyen"]),
        "| H: sunucunun işlediği komut | %d |" % len(H),
        "| G ∩ H | %d |" % len(G & H),
        "| **G ∖ H** (eksik) | **%d** |" % len(sonuc["eksik"]),
        "| İmza uyumsuzluğu (sunucu, istemcinin göndermediği sırayı okuyor) | %d |" % len(sonuc["uyumsuz"]),
        "| H ∖ G (istemcinin bu sürümde göndermediği) | %d |" % len(sonuc["fazla"]),
        "",
        "Kapılar (`docs/YOL_HARITASI_1407.md` §2.1): `|G ∖ H| = 0` ve imza uyumsuzluğu 0.",
        "",
    ]
    if fark is not None:
        satir += [
            "## Sürüm farkı (%s → %s)" % (eski_ad, ad),
            "",
            "- Yeni komut (%d): %s" % (len(fark["yeni"]), ", ".join("`%s`" % x for x in fark["yeni"]) or "yok"),
            "- Kalkan komut (%d): %s" % (len(fark["kalkan"]),
                                          ", ".join("`%s`" % x for x in fark["kalkan"]) or "yok"),
            "- Argüman sayısı değişen (%d):" % len(fark["degisen"]),
            "",
        ]
        if fark["degisen"]:
            satir += ["| Komut | Eski | Yeni |", "|---|---|---|"]
            satir += ["| `%s` | %s | %s |" % (a, e, y) for a, e, y in fark["degisen"]]
            satir.append("")
    satir += [
        "## Komutlar",
        "",
        "Durum: **var** işleyici var ve imza uyumlu; **eksik** işleyici yok; **imza** sunucu fazla sıra okuyor.",
        "Argüman sayısı: o komutun çağrı yerlerinde görülen farklı sayılar. Sunucu sırası: işleyicinin okuduğu",
        "en büyük argüman sırası (0'dan; -1 hiç okumaz, ? bilinemez).",
        "",
        "| Komut | Durum | Çağrı yeri | Arg. sayısı | Sunucu işlevi | Belge | Sunucu sırası | Örnek çağrı |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in sonuc["satirlar"]:
        sv = s["sunucu"]
        islev = "`%s` (%d)" % (sv["islev"], sv["satir"]) if sv else "—"
        belge = ("%d/%d" % sv["belge_args"]) if sv and sv["belge_args"] else "—"
        sira = "—" if not sv else ("?" if sv["en_buyuk_sira"] is None else sv["en_buyuk_sira"])
        ornek = "%s: [%s]" % (s["ornek"]["yer"], ", ".join(s["ornek"]["args"]))
        satir.append("| `%s` | %s | %d | %s | %s | %s | %s | %s |" % (
            s["ad"], s["durum"], s["yer_sayisi"], ", ".join(map(str, s["argsayilari"])) or "?",
            islev, belge, sira, _hucre(ornek)))
    satir += ["", "## H ∖ G: sunucuda olup bu istemcinin göndermediği", ""]
    satir.append(", ".join("`%s`" % x for x in sonuc["fazla"]) or "yok")
    kullanilmayan = sorted(set(st) - istemci["sabit_kullanilan"])
    satir += ["", "## Kodda okunmayan `CMD_*` sabitleri (%d)" % len(kullanilmayan), ""]
    satir.append(", ".join("`%s` = `%s`" % (k, st[k]) for k in kullanilmayan) or "yok")
    if istemci["cozulemeyen"]:
        satir += ["", "## Komut adı çözülemeyen çağrılar", ""]
        satir += ["- %s: cmd = `%s`" % (c["yer"], c["cmd"]) for c in istemci["cozulemeyen"]]
    return "\n".join(satir) + "\n"


def main(argv=None):
    import hashlib
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("swf")
    ap.add_argument("--eski", help="karşılaştırılacak eski istemci")
    ap.add_argument("--md", help="tabloyu bu dosyaya yaz")
    ap.add_argument("--json", help="makinece okunur listeyi bu dosyaya yaz")
    a = ap.parse_args(argv)
    with open(a.swf, "rb") as f:
        veri = f.read()
    istemci = istemci_komutlari(veri)
    sonuc = karsilastir(istemci, sunucu_komutlari())
    fark = eski_ad = None
    if a.eski:
        with open(a.eski, "rb") as f:
            fark = surum_farki(istemci, istemci_komutlari(f.read()))
        eski_ad = os.path.basename(a.eski)
    ad, sha = os.path.basename(a.swf), hashlib.sha256(veri).hexdigest()
    md = markdown(ad, sha, istemci, sonuc, fark, eski_ad)
    if a.json:
        import json
        with open(a.json, "w", encoding="utf-8", newline="\n") as f:
            json.dump(json_verisi(ad, sha, istemci), f, ensure_ascii=False, indent=1)
            f.write("\n")
    if a.md:
        with open(a.md, "w", encoding="utf-8", newline="\n") as f:
            f.write(md)
    print("G=%d H=%d G∖H=%d imza=%d H∖G=%d" % (len(sonuc["G"]), len(sonuc["H"]), len(sonuc["eksik"]),
                                               len(sonuc["uyumsuz"]), len(sonuc["fazla"])))
    if fark:
        print("yeni=%d kalkan=%d degisen=%d" % (len(fark["yeni"]), len(fark["kalkan"]), len(fark["degisen"])))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
