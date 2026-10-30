# 1.4.07 config hattı: bizim yamalarımız

Bu dosya `araclar/config_hatti.py` ile üretilir; elle düzenlenmez.

- C₁₄₀₇: taban + upstream `54df29e` `config/patch` (0-language_en, 1-mega_patch, 2-unit_patch) + `goals.json`.

| Yama | İşlem | aynı | kapsanıyor | farklı | yeni | yolu yok | Hüküm | Farklı alanlar (işlem sayısı) |
|---|---|---|---|---|---|---|---|---|
| `dragon_boss_fix` | 1 | 0 | 1 | 0 | 0 | 0 | **gider** | — |
| `graveyard` | 3 | 0 | 0 | 3 | 0 | 0 | **çatışır** | `id` 2, `amount` 1, `price` 1, `text` 1 |
| `kompu` | 28 | 1 | 0 | 27 | 0 | 0 | **çatışır** | `id` 25, `text` 22 |
| `level_up_tips` | 14 | 0 | 0 | 14 | 0 | 0 | **çatışır** | `id` 13, `text` 13, `<değer>` 1 |
| `mission_goals` | 1 | 0 | 0 | 1 | 0 | 0 | **çatışır** | — |
| `missions_0_1` | 2 | 0 | 0 | 1 | 1 | 0 | **çatışır** | `description` 1, `reward` 1, `title` 1 |
| `new_daily_bonus` | 1 | 0 | 0 | 1 | 0 | 0 | **çatışır** | — |
| `soulmixer_temp` | 2 | 1 | 0 | 1 | 0 | 0 | **çatışır** | `cost` 1, `cost_type` 1, `height` 1, `unit_capacity` 1, `width` 1, `xp` 1 |
| `unit_collections` | 100 | 0 | 0 | 1 | 99 | 0 | **çatışır** | `100` 1, `101` 1, `102` 1, `103` 1, `104` 1, `105` 1, `106` 1, `107` 1 … (+91 alan) |
| `unit_patch` | 250 | 0 | 191 | 59 | 0 | 0 | **çatışır** | `tamed_id` 59 |
| `viral_icons` | 1 | 0 | 0 | 1 | 0 | 0 | **çatışır** | — |
| `viral_offers` | 1 | 0 | 0 | 1 | 0 | 0 | **çatışır** | `<değer>` 1 |
| `yeni_icerik` | 8 | 0 | 0 | 0 | 8 | 0 | **kalır** | — |

## Bütün listeyi koyan işlemlerde öğe sayımı

| Yama | Yol | aynı | kapsanıyor | farklı | yeni |
|---|---|---|---|---|---|
| `kompu` | `/kompu_offers` | 0 | 0 | 0 | 1 |
| `kompu` | `/globals/KOMPU_WIZZARD_COSTS` | 0 | 0 | 0 | 3 |
| `mission_goals` | `/goals` | 0 | 0 | 0 | 2 |
| `new_daily_bonus` | `/daily_bonus` | 0 | 0 | 1 | 0 |
| `viral_icons` | `/viral_icons` | 0 | 0 | 0 | 11 |

## Dokunulan config adları istemcide geçiyor mu (◐)

| Yama | Ad | 0926 | 1.4.07 |
|---|---|---|---|
| `dragon_boss_fix` | `items` | ✔ | ✔ |
| `graveyard` | `GRAVEYARD_POTIONS` | ✔ | ✔ |
| `graveyard` | `globals` | ✔ | ✔ |
| `graveyard` | `localization_strings` | ✔ | ✔ |
| `kompu` | `KOMPU_MIN_LEVEL` | ✔ | ✔ |
| `kompu` | `KOMPU_WIZZARD_COSTS` | ✔ | ✔ |
| `kompu` | `globals` | ✔ | ✔ |
| `kompu` | `kompu_offers` | ✔ | ✔ |
| `kompu` | `localization_strings` | ✔ | ✔ |
| `level_up_tips` | `level_up_tips` | — | ✔ | **canlanır**
| `level_up_tips` | `localization_strings` | ✔ | ✔ |
| `mission_goals` | `goals` | — | ✔ | **canlanır**
| `missions_0_1` | `missions` | ✔ | — |
| `new_daily_bonus` | `daily_bonus` | ✔ | ✔ |
| `soulmixer_temp` | `items` | ✔ | ✔ |
| `unit_collections` | `localization_strings` | ✔ | ✔ |
| `unit_collections` | `units_collections_categories` | ✔ | ✔ |
| `unit_patch` | `DRAGONS` | ✔ | ✔ |
| `unit_patch` | `globals` | ✔ | ✔ |
| `unit_patch` | `items` | ✔ | ✔ |
| `viral_icons` | `viral_icons` | — | ✔ | **canlanır**
| `viral_offers` | `viral_offers` | — | ✔ | **canlanır**
| `yeni_icerik` | `items` | ✔ | ✔ |
| `yeni_icerik` | `offer_packs` | ✔ | ✔ |
