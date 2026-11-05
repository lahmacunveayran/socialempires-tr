"""PR'daki değişikliği Claude API'ye inceletir, bulguları PR'a Türkçe yorum olarak yazar.

Claude Code yerine doğrudan Messages API çağrılır: Max planıyla gelen API kredisi Claude Code'da
geçmiyor, API çağrısında geçiyor (S-45). Böylece inceleme sahibinin Claude Code kullanım hakkından yemez.

Akış:
1. `gh` ile PR'ın farkı (diff), başlığı ve önceki inceleme yorumları alınır.
2. Fark, değişen dosyaların tam hâli (sınır içinde) ve CLAUDE.md ile tek bir istek gönderilir;
   cevap JSON şemasına bağlıdır (özet + bulgular).
3. Bulgular farkta yorum yazılabilen satırlara satır içi yorum olarak, diğerleri özette yazılır.
   Özet tek yorumdur; her koşuda güncellenir (gizli işaretle bulunur).

Ortam: ANTHROPIC_API_KEY, GH_TOKEN, REPO (sahip/ad), PR (numara), MODEL (depo değişkeni).

Komut satırı (yerelde yalnızca istemi görmek için, API çağrılmaz; `gh` girişi gerekir):
    REPO=sahip/ad PR=31 python araclar/pr_inceleme.py --kuru
"""

import argparse
import json
import os
import re
import subprocess
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISARET = "<!-- pr-inceleme -->"
BOT = "github-actions[bot]"
# Bağlam sınırları (karakter). Fark sığmazsa kesilmez; inceleme yapılmadığı açıkça yazılır.
FARK_SINIRI = 600_000
DOSYA_SINIRI = 300_000

SEMA = {
    "type": "object",
    "properties": {
        "ozet": {"type": "string"},
        "bulgular": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "dosya": {"type": "string"},
                    "satir": {"type": "integer"},
                    "onem": {"type": "string", "enum": ["Yüksek", "Orta", "Düşük"]},
                    "tur": {"type": "string", "enum": ["hata", "güvenlik", "kalite"]},
                    "metin": {"type": "string"},
                },
                "required": ["dosya", "satir", "onem", "tur", "metin"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["ozet", "bulgular"],
    "additionalProperties": False,
}

TALIMAT = """Sen bu depo için kod inceleyicisin. Depo, Social Empires oyununun tek kişilik, çevrimdışı
Türkçe yerel sunucusu (Python/Flask + tarayıcı JS). Depo kuralları aşağıdaki CLAUDE.md'de.

Yalnızca bu PR'da değişen koda bak. Öncelik sırasıyla:
1. Hatalar: yanlış mantık, unutulmuş durum, çökme, bozulan çağrılar, kayıt (save) verisinin bozulması
   ya da kaybolması.
2. Güvenlik: istemciden gelen veriyi doğrulamadan kullanmak, dosya yolu ile oynama, tehlikeli eval/exec.
3. Kalite: tekrar eden kod, gereksiz karmaşıklık, eksik test (testler tests/ altında).

Kurallar:
- Her bulgu somut olsun: ne yanlış, hangi durumda ortaya çıkıyor, nasıl düzelir.
- "satir", bulgunun farktaki yeni dosyada (+ tarafı) geçtiği satır numarası olsun.
- Emin olmadığın şeyi kesin gibi yazma; "olabilir" de.
- Zevk meselesi ve küçük biçim önerileri yazma.
- "Önceki inceleme yorumları"nda geçen bir bulguyu yeniden yazma: master'a birleştirmek için her satır
  içi yorumun çözülmesi gerekiyor, tekrar sahibine iş çıkarır. Önceki bir bulgu düzeltilmişse özette
  kısaca söyle.
- "ozet" kısa olsun (en çok birkaç madde). Sorun yoksa bunu açıkça söyle.
- Her şeyi Türkçe yaz."""


def gh(*args, girdi=None):
    """`gh` komutunu çalıştırır, çıktıyı metin olarak döndürür."""
    sonuc = subprocess.run(["gh", *args], input=girdi, capture_output=True, text=True,
                           encoding="utf-8", check=True)
    return sonuc.stdout


def gh_json(*args, girdi=None):
    return json.loads(gh(*args, girdi=girdi) or "null")


# ---------------------------------------------------------------------------
# Fark
# ---------------------------------------------------------------------------

def yorumlanabilir_satirlar(fark):
    """Birleşik farkta yeni dosya tarafında yorum yazılabilen satırlar: {dosya: {satır, ...}}.

    GitHub satır içi yorumu yalnızca farkın parçalarında (eklenen ya da bağlam satırı) kabul eder.
    Parçanın içi, başlığındaki satır sayılarıyla izlenir: içeriği "++ " ya da "-- " ile başlayan bir satır
    ("+++ ...", "--- ...") dosya başlığı sanılmaz.
    """
    satirlar = {}
    dosya = None
    yeni = eski_kalan = yeni_kalan = 0
    for s in fark.splitlines():
        if eski_kalan > 0 or yeni_kalan > 0:
            if s.startswith("\\"):
                continue  # "\ No newline at end of file"
            if s.startswith("-"):
                eski_kalan -= 1  # yeni tarafta yer tutmaz
                continue
            if s.startswith("+"):
                yeni_kalan -= 1
            else:  # bağlam satırı (" " ya da boş)
                eski_kalan -= 1
                yeni_kalan -= 1
            if dosya is not None:
                satirlar[dosya].add(yeni)
            yeni += 1
        elif s.startswith("+++ "):
            yol = s[4:].strip()
            dosya = None if yol == "/dev/null" else re.sub(r"^b/", "", yol)
            if dosya is not None:
                satirlar.setdefault(dosya, set())
        elif s.startswith("@@"):
            m = re.match(r"@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", s)
            if m:
                eski_kalan = int(m.group(1) or 1)
                yeni, yeni_kalan = int(m.group(2)), int(m.group(3) or 1)
    return satirlar


def dosya_baglami(dosyalar, sinir=DOSYA_SINIRI):
    """Değişen dosyaların tam hâli (silinenler ve ikili dosyalar hariç), toplamda sınır içinde.

    Sembolik bağlar ve depo dışına çıkan yollar okunmaz: iş, PR'ın kodunu secret'larla çalıştırıyor;
    `/proc/self/environ`'a giden bir bağ anahtarları isteme, oradan da herkese açık yoruma taşıyabilir.
    """
    parcalar, toplam, atlanan = [], 0, []
    kok = os.path.realpath(KOK)
    for yol in dosyalar:
        tam = os.path.join(KOK, yol)
        if os.path.islink(tam) or os.path.commonpath([kok, os.path.realpath(tam)]) != kok:
            continue
        try:
            with open(tam, encoding="utf-8") as f:
                icerik = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        if toplam + len(icerik) > sinir:
            atlanan.append(yol)
            continue
        parcalar.append(f'<dosya yol="{yol}">\n{icerik}\n</dosya>')
        toplam += len(icerik)
    return "\n".join(parcalar), atlanan


# ---------------------------------------------------------------------------
# Yorumlar
# ---------------------------------------------------------------------------

def onceki_yorumlar(repo, pr):
    """Botun daha önce yazdığı satır içi yorumlar ve özet yorumu."""
    satir_ici = gh_json("api", "--paginate", "--slurp", f"repos/{repo}/pulls/{pr}/comments")
    satir_ici = [y for sayfa in satir_ici for y in sayfa if y["user"]["login"] == BOT]
    genel = gh_json("api", "--paginate", "--slurp", f"repos/{repo}/issues/{pr}/comments")
    genel = [y for sayfa in genel for y in sayfa if y["user"]["login"] == BOT]
    ozet = next((y for y in reversed(genel) if ISARET in y["body"]), None)
    return satir_ici, ozet


def onceki_metni(satir_ici, ozet):
    satirlar = [f"- {y['path']}:{y.get('line') or y.get('original_line')}: {y['body'][:400]}"
                for y in satir_ici]
    if ozet:
        satirlar.append("- Önceki özet: " + ozet["body"].replace(ISARET, "").strip()[:1500])
    return "\n".join(satirlar) or "(yok)"


def ayir(bulgular, satirlar):
    """Bulguları satır içi yazılabilenler ve özete düşenler olarak ikiye ayırır."""
    icerde, disarda = [], []
    for b in bulgular:
        (icerde if b["satir"] in satirlar.get(b["dosya"], ()) else disarda).append(b)
    return icerde, disarda


def bulgu_metni(b):
    return f"**{b['onem']} · {b['tur']}**\n\n{b['metin']}"


def ozet_metni(ozet, disarda, maliyet):
    parcalar = [ISARET, "## İnceleme özeti", "", ozet.strip()]
    if disarda:
        parcalar += ["", "Farkta satırı olmayan bulgular:"]
        parcalar += [f"- `{b['dosya']}:{b['satir']}` ({b['onem']}, {b['tur']}): {b['metin']}"
                     for b in disarda]
    if maliyet:
        parcalar += ["", f"<sub>{maliyet}</sub>"]
    return "\n".join(parcalar)


def ozet_yaz(repo, pr, govde, onceki):
    if onceki:
        gh("api", "-X", "PATCH", f"repos/{repo}/issues/comments/{onceki['id']}", "--input", "-",
           girdi=json.dumps({"body": govde}))
    else:
        gh("api", "-X", "POST", f"repos/{repo}/issues/{pr}/comments", "--input", "-",
           girdi=json.dumps({"body": govde}))


def satir_ici_yaz(repo, pr, sha, icerde):
    if not icerde:
        return
    govde = {
        "commit_id": sha,
        "event": "COMMENT",
        "comments": [{"path": b["dosya"], "line": b["satir"], "side": "RIGHT", "body": bulgu_metni(b)}
                     for b in icerde],
    }
    gh("api", "-X", "POST", f"repos/{repo}/pulls/{pr}/reviews", "--input", "-", girdi=json.dumps(govde))


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def istem(pr_bilgi, fark, baglam, onceki, claude_md):
    return (f"<claude_md>\n{claude_md}\n</claude_md>\n\n"
            f"<pr baslik=\"{pr_bilgi['title']}\">\n{pr_bilgi.get('body') or ''}\n</pr>\n\n"
            f"<onceki_inceleme_yorumlari>\n{onceki}\n</onceki_inceleme_yorumlari>\n\n"
            f"<degisen_dosyalar>\n{baglam}\n</degisen_dosyalar>\n\n"
            f"<fark>\n{fark}\n</fark>")


def incele(model, metin):
    """Messages API'yi çağırır; (cevap sözlüğü ya da None, durum metni, maliyet metni) döndürür."""
    import anthropic  # yalnızca CI'da kurulu; testler içe aktarmadan çalışsın

    istemci = anthropic.Anthropic()
    try:
        cevap = _akis(istemci, model, metin)
    except anthropic.APIStatusError as e:  # kredi bitmesi (400), 401, 429, 5xx
        return None, f"API hatası ({e.status_code}): {e.message}", ""
    except anthropic.APIConnectionError:
        return None, "API'ye bağlanılamadı.", ""
    k = cevap.usage
    maliyet = (f"{cevap.model} · girdi {k.input_tokens:,} · çıktı {k.output_tokens:,} token · "
               f"ileti {cevap.id}")
    print(maliyet, "· durma:", cevap.stop_reason)
    if cevap.stop_reason == "refusal":
        return None, "Model isteği reddetti; inceleme yapılamadı.", maliyet
    if cevap.stop_reason == "max_tokens":
        return None, "Cevap çıktı sınırına takıldı; inceleme tamamlanamadı.", maliyet
    sonuc, hata = cevabi_coz(next((b.text for b in cevap.content if b.type == "text"), ""))
    return sonuc, hata, maliyet


def cevabi_coz(metin):
    """(sonuç ya da None, hata metni): bozuk ya da şemaya uymayan cevap çökertmez."""
    try:
        sonuc = json.loads(metin)
    except json.JSONDecodeError:
        return None, "Cevap JSON olarak çözülemedi; inceleme tamamlanamadı."
    if not (isinstance(sonuc, dict) and isinstance(sonuc.get("ozet"), str)
            and isinstance(sonuc.get("bulgular"), list)):
        return None, "Cevap beklenen biçimde değil; inceleme tamamlanamadı."
    return sonuc, None


def _akis(istemci, model, metin):
    with istemci.beta.messages.stream(
        model=model,
        max_tokens=32000,
        system=TALIMAT,
        messages=[{"role": "user", "content": metin}],
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": SEMA}},
        # Güvenlik sınıflandırıcısı reddederse istek sunucuda uygun başka modelle yeniden çalışır.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    ) as akis:
        return akis.get_final_message()


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kuru", action="store_true", help="API'yi çağırma, istemin boyutunu yaz")
    a = ap.parse_args()

    repo, pr = os.environ.get("REPO", "").strip(), os.environ.get("PR", "").strip()
    if not repo or not pr:
        sys.exit("REPO (sahip/ad) ve PR (numara) ortam değişkenleri gerekli, ör. REPO=sahip/ad PR=31.")
    model = os.environ.get("MODEL", "").strip()
    if not model and not a.kuru:
        sys.exit("MODEL boş: depo değişkeni INCELEME_MODELI tanımlı değil.")

    pr_bilgi = gh_json("pr", "view", pr, "--repo", repo, "--json", "title,body,headRefOid,files")
    fark = gh("pr", "diff", pr, "--repo", repo)
    satir_ici, onceki_ozet = onceki_yorumlar(repo, pr)

    if len(fark) > FARK_SINIRI:
        govde = ozet_metni(f"Fark çok büyük ({len(fark):,} karakter); otomatik inceleme yapılmadı. "
                           "PR'ı küçük parçalara bölmek gerekir.", [], "")
        if not a.kuru:
            ozet_yaz(repo, pr, govde, onceki_ozet)
        print(govde)
        return

    dosyalar = [f["path"] for f in pr_bilgi["files"]]
    baglam, atlanan = dosya_baglami(dosyalar)
    with open(os.path.join(KOK, "CLAUDE.md"), encoding="utf-8") as f:
        claude_md = f.read()
    metin = istem(pr_bilgi, fark, baglam, onceki_metni(satir_ici, onceki_ozet), claude_md)
    print(f"istem {len(metin):,} karakter, {len(dosyalar)} dosya, bağlama sığmayan: {atlanan or 'yok'}")
    if a.kuru:
        return

    sonuc, hata, maliyet = incele(model, metin)
    if sonuc is None:
        ozet_yaz(repo, pr, ozet_metni(hata, [], maliyet), onceki_ozet)
        sys.exit(hata)

    icerde, disarda = ayir(sonuc["bulgular"], yorumlanabilir_satirlar(fark))
    ozet = sonuc["ozet"]
    if atlanan:
        ozet += "\n\nTam hâli bağlama sığmayan dosyalar (yalnızca farkı okundu): " + ", ".join(atlanan)
    try:
        satir_ici_yaz(repo, pr, pr_bilgi["headRefOid"], icerde)
    except subprocess.CalledProcessError as e:
        # ör. 422: arada yeni commit geldi; bulgular kaybolmasın, özete düşsün
        print("satır içi yorum yazılamadı:", (e.stderr or "").strip()[:500])
        disarda, icerde = icerde + disarda, []
        ozet += "\n\nSatır içi yorumlar GitHub'a yazılamadı; bütün bulgular aşağıda."
    ozet_yaz(repo, pr, ozet_metni(ozet, disarda, maliyet), onceki_ozet)
    print(f"{len(icerde)} satır içi, {len(disarda)} özette bulgu")


if __name__ == "__main__":
    main()
