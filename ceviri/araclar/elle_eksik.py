# -*- coding: utf-8 -*-
"""API kotasına takılan son metinlerin elle çevirisi (tr.json'a ekler)."""

import json
import os

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
YOL = os.path.join(KOK, "ceviri", "tr.json")

CEVIRILER = {
    "loc:STORE_EDIFICIO_REFUERZOS": "\n  \n Müttefiklerinizden takviye almanızı sağlar!",
    "loc:STORE_EDIFICIO_SACRIFICIO": "\n  \n Bir birimi feda ederek karşılığında kaynak kazanın",
    "loc:STORE_EDIFICIO_TESORO": "\n  \n Her gün bir koleksiyon eşyası keşfeder",
    "loc:STORE_EDIFICIO_ESTABLO": "\n  \n Kılıçlı ve okçularınızı atlı birimlere dönüştürmenizi sağlar.",
    "loc:STORE_EDIFICIO_CRIADERO": "\n  \n Üretmeleri için içine iki hayvan koyun.",
    "loc:STORE_EDIFICIO_ZEPPELIN": "\n  \n Antik Deniz'i keşfetmek için bir zeplin inşa etmenizi sağlar!",
    "loc:STORE_EDIFICIO_BARCO": "\n  \n Büyük Deniz'i keşfetmek için bir gemi inşa etmenizi sağlar!",
    "loc:STORE_EDIFICIO_COLISEO": "\n  \n Köylülerinizin daha hızlı hareket etmesini ve daha fazla kaynak kuyruğa almasını sağlar.",
    "loc:STORE_EDIFICIO_ESTATUA": "\n  \n Heykel, günlük 3 saldırı sınırınızı 4'e çıkarır.",
    "loc:STORE_EDIFICIO_MINA": "\n  \n Köylülerinizin altın ve taşı çok hızlı kazmasını sağlar.",
    "loc:STORE_EDIFICIO_SERRADERO": "\n  \n Köylülerinizin ağaçları çok hızlı kesmesini sağlar.",
    "loc:STORE_EDIFICIO_MERCADO_ALIADOS": "\n  \n Müttefiklerinizin yardımıyla istediğiniz kaynağı toplamanızı sağlar.",
    "loc:STORE_EDIFICIO_MAQUINA_DEL_TIEMPO": "\n  \n Haritanızın arazi temasını değiştirmenizi sağlar!",
    "loc:STORE_EDIFICIO_RECLUTAMIENTO_ALIADOS": "\n  \n Yeni askerler aracılığıyla güçlü birimler elde etmenizi sağlar!",
    "loc:STORE_EDIFICIO_MESA_REDONDA": "\n  \n Arkadaşlarınızın yardımıyla ödüller kazanmanızı sağlar!",
    "loc:STORE_EDIFICIO_HECHICERIA": "\n  \n Büyü öğrenmenizi ve kullanmanızı sağlar!",
    "loc:STORE_EDIFICIO_MARAVILLA_SOCIAL": "\n  \n Nüfus sınırınızı 50 birim daha artırır!",
    "loc:STORE_EDIFICIO_DESCONOCIDO": "\n  \n DURUM BULUNAMADI!",
    "loc:STORE_EDIFICIO_HEROES_ALTAR": "\n  \n Özel kahramanlar edinmenizi sağlar!",
    "loc:STORE_EDIFICIO_HEROES_CEMENTERIO": "\n  \n  \n Kaybettiğiniz kahramanları diriltmenizi sağlar.",
    "loc:STORE_EDIFICIO_MARAVILLA": "\n  \n Bu mucize, #0# nüfus sınırını #1# artırır",
    "loc:STORE_EDIFICIO_CEMENTERIO": "\n  \n Savaşlarda kaybettiğiniz birimleri burada diriltebilirsiniz!",
    "loc:STORE_EDIFICIO_CRIADERO_DRAGON": "\n  \n  \n Kendi ejderhalarınızı yetiştirin!",
    "loc:STORE_EDIFICIO_MONSTERS_NEST": "\n  \n  \n Kendi canavarlarınızı yetiştirin!",
    "loc:AVISO_POCO_NIVEL_PARA_CONQUISTAR": "\n İmparatorluğunuz dünyayı fethetmek için çok küçük. Dünya gezginini açmak için #0# seviyesine ulaşın.",
    "loc:AVISO_COLECCION_FACCION": "\n  \n Bu fraksiyonun koleksiyonlarına erişemezsiniz",
    "loc:AVISO_TOPE_UNIDADES": "\n Bu türden daha fazla biriminiz olamaz.",
    "loc:AVISO_TOPE_POBLACION": "\n Maksimum nüfusa ulaştınız.",
    "loc:AVISO_TOPE_ALOJAMIENTO": "\n Daha fazla nüfus barındıramazsınız. Daha fazla ev inşa edin.",
    "loc:AVISO_NIVEL_MEJORAR": "\n Bu binayı geliştirmek için #0# seviyesinde olmalısınız.",
    "loc:AVISO_SIN_MADERA_GRANJA": "\n Eyvah! Çiftliği yeniden inşa etmek için yeterli odununuz yok!",
    "loc:AVISO_SIN_AYUDAS": "\n  Başka yardım hakkı kalmadı!  \n  Yarın tekrar gelin!",
    "loc:AVISO_BOCADILLOS": "\n Konuşma balonları açık! \n  \n İyi eğlenceler!",
    "loc:AVISO_SANGRE": "\n Kan modu açık! \n  \n Bunu siz istediniz...",
    "loc:AVISO_UNIDAD_UNICA": "\n Bu birimden aynı anda iki tane olamaz.",
    "loc:AVISO_SUFICIENTE_COMIDA": "\n Yeterli yemeğiniz yok! \n Çiftlik, değirmen ve ahırlardan yemek alın.",
    "loc:AVISO_SUFICIENTE_MADERA": "\n Yeterli odununuz yok! \n Daha fazla ağaç kesin.",
    "loc:AVISO_SUFICIENTE_PIEDRA": "\n Yeterli taşınız yok! \n Daha fazla taş damarı çıkarın.",
    "loc:AVISO_NAVEGAR_SIN_TROPAS": "\n Yelken açacak hiç askeriniz yok!",
    "loc:AVISO_TORRE_ZEPPELIN": "\n Zeplin inşa edip mürettebatla doldurmak için bir Zeplin Kulesi'ne ihtiyacınız var!",
    "loc:AVISO_VOLAR_SIN_TROPAS": "\n Uçacak hiç askeriniz yok!",
    "loc:AVISO_MERCADO_AGOTADO": "\n Pazar kaynakları tükendi. Daha fazla takas için 24 saat sonra gelin!",
    "loc:AVISO_JUGADOR_NO_ENCONTRADO": "\n Oyuncu bulunamadı",
    "loc:AVISO_SERVICIO_NO_DISPONIBLE": "\n Hizmet kullanılamadı",
    "loc:AVISO_DEMASIADOS_POSTS": "\n  \n Bugün yeterince gönderi gönderdiniz",
    "loc:AVISO_BARCO_SIN_MUELLE": "\n Tekneyle karaya çıkamazsınız. \n Daha büyük gemi inşa edip ordunuzu taşımak için bir liman yapın!",
    "loc:AVISO_QUEST_BLOQUEADA": "\n Bu görevin kilidini henüz açmadınız!",
    "loc:AVISO_QUEST_GASTADA": "\n Her ada yalnızca 4 saatte bir oynanabilir",
    "loc:INFO_ESPIAR": "Artık dünya gezgini üzerinden düşmanlarınızı gözetleyebilirsiniz. \n ",
    "loc:POPUP_COMPRAR_ASALTO_SIN_ACCIONES": "Daha fazla #0# hakkınız yok, \n ",
    "loc:POPUP_COMPRAR_ASALTO_RECARGA": "#0# sonra 3 tane daha alacaksınız \n  \n ",
    "loc:POPUP_RAZA_NIVEL_TROLL": "\n Troll Irkını açmak için #0# seviyesine ulaşmalısınız.",
    "loc:TOURNAMENT_LOSE": "\n  \n Maalesef turnuvayı kaybettiniz! \n Pes etmeyin ve tekrar deneyin, harika ödüller sizi bekliyor!",
    "loc:TOURNAMENT_WIN": "\n  \n Tebrikler! Turnuvayı kazandınız! \n Ödülünüzü deponuzda arayın!",
    "loc:TOURNAMENT_YOU_CAN_FIGHT_WITH_20_UNITS": "\n En fazla 20 birim seçebilirsiniz. \n Çıkmak istediğinize emin misiniz?",
    "loc:TOURNAMENT_YOU_CAN_NOT_ENTER_WITHOUT_UNITS": "\n Hiç biriminiz olmadan turnuvaya giremezsiniz. \n Takımınızı seçin.",
    "loc:TOURNAMENT_YOU_TEAM_HAS_NOT_MAXIUM_UNITS": "\n  \n İzin verilen maksimum birim sayısını henüz seçmediniz. \n  \n Şimdi turnuvaya girmek istediğinize emin misiniz?",
    "loc:TOURNAMENT_HELP_TEXT": "\n  \n - Bu oyun modunu oynarken hiçbir biriminizi KAYBETMEZSİNİZ! \n  \n - 3 oyuncuya karşı oynayın ve turnuvayı kazanın! \n  \n - Tüm oyuncular tüm maçları oynadığında veya 24 saat geçtiğinde turnuva biter. \n  \n - Bir turnuvayı kazanırsanız harika ödüller alırsınız! \n  \n - Şu anda bu birimler turnuva modunda kullanılamaz: #0#",
    "loc:TOURNAMENT_LEAVE_CONFIRM_TEXT": "\n  \n Turnuvadan çıkmak istediğinize emin misiniz? \n  \n Oynanan tüm savaşları kaybedeceksiniz...",
    "loc:TOURNAMENT_WEEKLY_INFO_TEXT": "\n Yapay zekâ oyuncularını yenin ve Dünya Çapında İlk 10'a girin!! \n  \n Ne kadar çok puan alırsanız o kadar iyi. Beraberlik durumunda daha az oynama süresi olan oyuncunun üstte olacağını unutmayın!",
    "loc:TOURNAMENT_WIN_REWARD_SOON": "\n  \n Tebrikler! Turnuvayı kazandınız! \n Ödülünüz yakında deponuzda görünecek!",
    "loc:LIMIT_HELP": "- Limit, tüm saldırıların en güçlüsüdür. \n - Limit saldırısını yalnızca Süvari Ejderhalarında bulabilirsiniz. \n - 3 tür Limit vardır: Hücum, Işın Saldırısı ve İyileştirme. Her süvari ejderha bunlardan birini kullanır. \n - Düşmanları öldürerek çubuğu doldurun ve Limit'i etkinleştirin. \n - Etkinleştirdikten sonra saldırıyı serbest bırakmak için çubuk düğmesine tıklayın. \n - Farklı süvari ejderhalarla saldırarak kendi Limit stratejinizi oluşturun. \n ",
    "loc:POPUP_SURVIVAL_MODE_TEXT": "- Merkezdeki Yadigârı düşman saldırılarından koruyun! \n  \n - Mümkün olduğunca uzun dayanın ve bir birim kazanın! \n  \n - Ordunuz en güçlü 30 biriminizden oluşacak!! \n  \n - İpucu: 8 yönden gelen düşmanların doğmasını durdurmak için önce Patronları yenin! \n  \n - Bu oyun modunu oynarken hiçbir biriminizi kaybetmezsiniz!! :) \n  \n - Süreyi geçip bir birim kazanırsanız, almak için deponuzu kontrol edin! \n  \n - En iyi sürenizi geçin, fotoğraf çekin ve forumlarımıza gönderin! \n  \n ",
    "loc:UNIT_WAREHOUSE_HELP_TEXT": "- Birimlerinizi depoda güvende tutun! \n  \n - Yer eksikliği yüzünden birimlerinizi feda etmenize gerek yok! \n  \n - Haritanızdaki bir birime tıklayın ve depoya koymak için depoya tıklayın. \n  \n  - Bir birim portresine tıklayarak onu tekrar haritanıza koyun. \n  \n  - 200 yuvaya kadar daha fazla yer satın alabilirsiniz!! \n  \n ",
    "loc:POPUP_BAHAMUT_SUPREME_TEMPLE_HELP_TEXT": "-ŞİMDİYE KADAR EN MUHTEŞEM EJDERHAYI ALIN!! \n  \n - Yüce Bahamut Ejderhasını serbest bırakmak için tüm adımları tamamlayın. \n  \n - Her adım 48 saat sürer. \n  \n -Her adımı istediğiniz sırayla tamamlayın. \n  \n ",
    "loc:TEAM_SELECTION_WINDOW_REQUIREMENTS_MSG": "Bu göreve girmek için aşağıdaki kategorilerden en az #0# birime sahip olmalısınız: \n  \n ",
}

with open(YOL, encoding="utf-8") as f:
    veri = json.load(f)
veri.setdefault("ceviriler", {}).update(CEVIRILER)
with open(YOL, "w", encoding="utf-8") as f:
    json.dump(veri, f, ensure_ascii=False, indent=1)
print(len(CEVIRILER), "elle çeviri eklendi")
