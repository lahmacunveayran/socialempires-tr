"""Testlerin hata yakalama gücünü ölçer: araçla üretilmiş mutantlardan rastgele örneklem (cosmic-ray).

Neden: satır kapsamı testin kodu *çalıştırdığını* gösterir, *denetlediğini* değil (Inozemtseva ve Holmes, ICSE 2014).
Mutant öldürme oranı gerçek hataları yakalamayla ilişkili bulunmuştur (Just vd., FSE 2014). Bütün mutantları
koşmak saatler sürer; rastgele birkaç bin mutant aynı sonucu ±%2-3 içinde verir (Gopinath vd., ISSRE 2015).
Ayrıntı ve sonuçlar: docs/TEST_OLCUMU.md.

Kurulum (oyuna gerekmez, yalnızca ölçüm için; ayrı bir sanal ortam önerilir):
    pip install -r requirements.txt cosmic-ray==8.7.0 coverage==7.17.2

Kullanım:
    python araclar/mutasyon_olc.py --ornek 2000 --tohum 20261105 --isci 14
    python araclar/mutasyon_olc.py --rapor ölçüm/oturum.sqlite      (yalnızca özet)

Ne yapar:
1. Testleri coverage.py ile koşar; hangi satırın hiç çalışmadığını bulur.
2. `cosmic-ray init` ile oyun/ altındaki bütün mutantları üretir (operatör seçimi yok: aracın hepsi).
3. Tohumla tekrarlanabilir basit rastgele örneklem seçer. Hiçbir testin çalıştırmadığı satırdaki mutant koşulmaz,
   "kaldı" sayılır (öldürülemez). Diğerleri paralel koşar; her işçi kendi git worktree'sinde, bayt kodu yazmadan.
4. Modül modül öldürme oranını Wilson %95 aralığıyla yazar; kalan mutantları farklarıyla dosyaya döker.

Dikkat: işlenmemiş değişiklikler ölçülmez; worktree'ler HEAD'den kurulur.
"""

import argparse
import collections
import json
import math
import multiprocessing as mp
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
TEST_KOMUTU = f'"{sys.executable}" -B -m unittest discover -s tests -f'
ZAMAN_ASIMI = 120.0


def ortam():
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"  # aynı saniyede değişen kaynak eski .pyc'yle koşmasın
    os.environ["PYTHONUTF8"] = "1"  # test çıktısı Türkçe; cosmic-ray çıktıyı utf-8 çözer
    os.environ["PYTHONIOENCODING"] = "utf-8"


def kapsam_olc(dizin, cikti):
    veri = Path(dizin) / ".coverage"
    subprocess.run([sys.executable, "-m", "coverage", "run", "--branch", "--source=oyun", f"--data-file={veri}",
                    "-m", "unittest", "discover", "-s", "tests"], cwd=KOK, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([sys.executable, "-m", "coverage", "json", f"--data-file={veri}", "-q", "-o", str(cikti)],
                   cwd=KOK, check=True)
    dosyalar = json.load(open(cikti, encoding="utf-8"))["files"]
    return {k.replace("\\", "/"): set(v["executed_lines"]) for k, v in dosyalar.items()}


def worktree_kur(dizin, sayi):
    yollar = []
    for i in range(sayi + 1):
        yol = Path(dizin) / f"w{i}"
        subprocess.run(["git", "worktree", "add", "-q", "--detach", str(yol), "HEAD"], cwd=KOK, check=True)
        yollar.append(yol)
    return yollar


def worktree_kaldir(yollar):
    for yol in yollar:
        subprocess.run(["git", "worktree", "remove", "--force", str(yol)], cwd=KOK)


def _isci(args):
    from cosmic_ray.mutating import mutate_and_test
    no, is_, dizin = args
    os.chdir(Path(dizin) / f"w{mp.current_process()._identity[0]}")
    return no, mutate_and_test(is_.mutations, TEST_KOMUTU, ZAMAN_ASIMI)


def kos(oturum, calisan, ornek, tohum, isci_sayisi, dizin):
    from cosmic_ray.work_db import use_db
    from cosmic_ray.work_item import TestOutcome, WorkerOutcome, WorkResult
    with use_db(str(oturum)) as db:
        hepsi = sorted(db.pending_work_items, key=lambda w: w.job_id)
        secilen = random.Random(tohum).sample(hepsi, min(ornek, len(hepsi)))
        secilen_ids = {w.job_id for w in secilen}
        db.set_multiple_results([w.job_id for w in hepsi if w.job_id not in secilen_ids],
                                WorkResult(worker_outcome=WorkerOutcome.SKIPPED, output="örneklem dışı"))
        kosulacak, kapsamsiz = [], []
        for w in secilen:
            m = w.mutations[0]
            satirlar = set(range(m.start_pos[0], m.end_pos[0] + 1))
            (kosulacak if satirlar & calisan.get(str(m.module_path).replace("\\", "/"), set())
             else kapsamsiz).append(w)
        db.set_multiple_results([w.job_id for w in kapsamsiz], WorkResult(
            worker_outcome=WorkerOutcome.NORMAL, test_outcome=TestOutcome.SURVIVED,
            output="kapsam dışı: hiçbir test bu satırı çalıştırmıyor"))
        print(f"mutant {len(hepsi)}, örneklem {len(secilen)}, kapsam dışı {len(kapsamsiz)}, "
              f"koşulacak {len(kosulacak)}", flush=True)
        bas = time.time()
        with mp.Pool(isci_sayisi) as havuz:
            isler = [(n, w, str(dizin)) for n, w in enumerate(kosulacak)]
            for i, (no, sonuc) in enumerate(havuz.imap_unordered(_isci, isler), 1):
                db.set_result(kosulacak[no].job_id, sonuc)
                if i % 50 == 0 or i == len(kosulacak):
                    gecen = time.time() - bas
                    print(f"{i}/{len(kosulacak)} · {gecen / 60:.0f} dk · kalan ~"
                          f"{gecen / i * (len(kosulacak) - i) / 60:.0f} dk", flush=True)


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    orta = (p + z * z / (2 * n)) / (1 + z * z / n)
    yari = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return orta - yari, orta + yari


def rapor(oturum, kalan_dosyasi=None):
    from cosmic_ray.work_db import use_db
    from cosmic_ray.work_item import TestOutcome, WorkerOutcome
    say = collections.defaultdict(collections.Counter)
    kalanlar = []
    with use_db(str(oturum)) as db:
        for is_, sonuc in db.completed_work_items:
            if sonuc.worker_outcome == WorkerOutcome.SKIPPED:
                continue
            m = is_.mutations[0]
            mod = str(m.module_path).replace("\\", "/")
            if sonuc.worker_outcome != WorkerOutcome.NORMAL:
                tur = "isci_hatasi"
            elif sonuc.test_outcome == TestOutcome.KILLED:
                tur = "oldu"
            elif sonuc.test_outcome == TestOutcome.INCOMPETENT:
                tur = "gecersiz"
            elif (sonuc.output or "").startswith("kapsam dışı"):
                tur = "kapsamsiz"
            else:
                tur = "kaldi"
            say[mod][tur] += 1
            if tur in ("kaldi", "kapsamsiz"):
                kalanlar.append((mod, m.start_pos[0], m.operator_name, tur, sonuc.diff or ""))
    print(f"{'modül':24s} {'n':>5s} {'öldü':>5s} {'kaldı':>5s} {'kapsz':>5s}  öldürme oranı (%95 aralık)")
    toplam = collections.Counter()
    for mod in sorted(say, key=lambda k: -sum(say[k].values())):
        toplam.update(say[mod])
        _satir(mod, say[mod])
    print("-" * 78)
    _satir("TOPLAM", toplam)
    kapsanan = toplam["oldu"] + toplam["kaldi"]
    a, b = wilson(toplam["oldu"], kapsanan)
    print(f"yalnızca kapsanan satırlarda: {toplam['oldu']}/{kapsanan} = {toplam['oldu'] / max(kapsanan, 1):.1%} "
          f"[{a:.1%}, {b:.1%}]")
    if toplam["gecersiz"] or toplam["isci_hatasi"]:
        print(f"sayılmayan: geçersiz {toplam['gecersiz']}, işçi hatası {toplam['isci_hatasi']}")
    if kalan_dosyasi:
        with open(kalan_dosyasi, "w", encoding="utf-8") as f:
            for mod, satir, op, tur, fark in sorted(kalanlar):
                f.write(f"=== {mod}:{satir} {op} [{tur}]\n{fark}\n")


def _satir(ad, c):
    n = c["oldu"] + c["kaldi"] + c["kapsamsiz"]
    a, b = wilson(c["oldu"], n)
    print(f"{ad:24s} {n:5d} {c['oldu']:5d} {c['kaldi']:5d} {c['kapsamsiz']:5d}  "
          f"{c['oldu'] / max(n, 1):6.1%} [{a:.1%}, {b:.1%}]")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--ornek", type=int, default=2000)
    p.add_argument("--tohum", type=int, default=20261105)
    p.add_argument("--isci", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    p.add_argument("--cikti", default=None, help="sonuç klasörü (varsayılan: geçici klasör)")
    p.add_argument("--rapor", default=None, help="yalnızca var olan bir oturumu özetle")
    a = p.parse_args()
    ortam()
    if a.rapor:
        rapor(a.rapor)
        return
    cikti = Path(a.cikti or tempfile.mkdtemp(prefix="mutasyon-"))
    cikti.mkdir(parents=True, exist_ok=True)
    print("klasör:", cikti, flush=True)
    calisan = kapsam_olc(cikti, cikti / "kapsam.json")
    yollar = worktree_kur(cikti, a.isci)
    try:
        ayar = cikti / "cr.toml"
        ayar.write_text("[cosmic-ray]\nmodule-path = \"oyun\"\ntimeout = %.1f\nexcluded-modules = []\n"
                        "test-command = %s\n\n[cosmic-ray.distributor]\nname = \"local\"\n"
                        % (ZAMAN_ASIMI, json.dumps(TEST_KOMUTU)), encoding="utf-8")
        oturum = cikti / "oturum.sqlite"
        subprocess.run([sys.executable, "-m", "cosmic_ray.cli", "init", str(ayar), str(oturum)], cwd=yollar[0],
                       check=True)
        kos(oturum, calisan, a.ornek, a.tohum, a.isci, cikti)
    finally:
        worktree_kaldir(yollar)
        shutil.rmtree(cikti / "w0", ignore_errors=True)
    rapor(oturum, cikti / "kalanlar.txt")
    print("kalan mutantlar:", cikti / "kalanlar.txt")


if __name__ == "__main__":
    main()
