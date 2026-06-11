#!/usr/bin/env python3

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

MD_PATH = Path(__file__).parent / "Brezhnev_L_I_Rabochie_i_dnevnikovye_zapisi_V_3_kh_tomakh_tom_2_2016.md"
SKIP_UNTIL = "### 1 апреля"
DIARY_YEARS = range(1965, 1983)

LI_RE = re.compile(
    r"л\.?\s*и\.?|брежнев|jl\.?\s*и\.?|ji\.?\s*и\.?|j1\.?\s*и\.?"
    r"|j\.?\s*и\.?|\.:jи|jl\.\s*1|л\.\s*1|лji\.?|л\.i\.?"
    r"|л\.\\s*1|л\.\s*1|jj\.?\s*и|\.rJ\.?\s*и|лJI\.?|лJ1\.?",
    re.I,
)

TRAVEL_VERBS = (
    r"отбыл|выехал|вылетел|прибыл|прилетел|вернулся|возвратился|находился|находится|"
    r"уехал|направился|отправился|приехал|приезжал|выезжал|выезжает|"
    r"следовал|прибыли|отбыли|отправился"
)
TRAVEL_VERB_RE = re.compile(TRAVEL_VERBS, re.I)

HOME = {
    "москва", "москву", "москве", "москвы", "москвой", "домой", "родину",
    "внуково", "внуково-2", "внуково-11", "шереметьево", "шереметьева",
    "кремль", "кремле", "цк", "бкд", "кдс", "кабинет", "кабинете",
    "поликлинику", "поликлинике", "цкб", "больницу", "больнице", "спецбольнице",
    "аэродром", "аэропорт", "аэроnорт", "вокзал", "вокзала",
    "лужники", "конезавод", "дачу", "даче", "квартиру", "квартире",
    "работе", "работу", "приемной", "заседании", "переговорах", "сессии",
    "отдых", "отпуск", "отпуска",
    "район", "учений", "ручей", "ланское", "ланском",
    "шитко-ланск", "шитпо-ланск", "барвиху",
    "поликлинику на ул", "поликлинику на у л", "nоликлинику",
    "лен горы", "ленинских горах", "особняк",
}

LOCAL_DEST_RE = re.compile(
    r"(?:в|на|из)\s+(?:г\.?\s*)?(?:"
    r"москв|кремл|красн(?:ую|ой)?\s+площад|площад|"
    r"внуков|шереметьев|работ|поликлин|больниц|"
    r"цк\b|бкд|кабинет|аэродром|аэро"
    r")",
    re.I,
)


def is_daily_commute_line(line: str) -> bool:
    low = normalize_line(line).lower()
    if re.search(r"(?:уехал|выехал|отбыл|приехал|прибыл)\s+домой\b", low):
        return True
    if re.search(r"прибыл\s+на\s+работ", low):
        return True
    if re.search(r"на\s+переговор(?:ах|ы)\b", low) and not re.search(
        r"(?:отбыл|вылетел)\s+(?:[^.]{0,80}?\s+)?(?:в|на)\s+(?:"
        r"г\.?\s*)?(?:инди|франц|польш|чех|болгар|венгр|фрг|куб|"
        r"республик[aeu]\s+куб|монголи|финлянд)",
        low,
    ):
        return True
    if re.search(r"больниц|обследован|поликлин", low) and not re.search(
        r"(?:отбыл|вылетел)\s+(?:[^.]{0,60}?\s+)?(?:в|на)\s+(?:"
        r"г\.?\s*)?(?:инди|франц|польш|чех|болгар|венгр|фрг|куб|"
        r"республик[aeu]\s+куб|монголи|финлянд)",
        low,
    ):
        return True
    return False


def _has_unresolved_travel_destination(line: str) -> bool:
    if extract_raw_destination(line):
        return True
    low = normalize_line(line).lower()
    if re.search(r"командировк", low):
        return True
    if re.search(
        r"(?:отбыл|вылетел|направился)\s+(?:[^.]{0,90}?\s+)?(?:в|на)\s+"
        r"(?:г\.?\s*)?[«\"']?[\w«»\-]{3,}",
        low,
    ):
        tail = re.search(
            r"(?:отбыл|вылетел|направился)\s+(?:[^.]{0,90}?\s+)?(?:в|на)\s+"
            r"(?:г\.?\s*)?[«\"']?([\w«»\-]{3,})",
            low,
            re.I,
        )
        if tail:
            raw = tail.group(1)
            if clean_token(raw) not in HOME and _valid_unrec_token(raw):
                return True
    return False


def is_local_movement_line(line: str) -> bool:
    if is_daily_commute_line(line):
        return True
    if not TRAVEL_VERB_RE.search(line):
        return False
    low = normalize_line(line).lower()
    if not LOCAL_DEST_RE.search(low):
        return False
    if _country_from_travel_line(line):
        return False
    if extract_destinations(line):
        return False
    if re.search(
        r"(?:отбыл|вылетел|выехал|уехал|направился)\s+(?:[^.]{0,80}?\s+)?(?:в|на)\s+(?:"
        r"г\.?\s*)?(?:зареч|завид|ялт|барвих|сочи|крым)",
        low,
    ):
        return False
    return True


PLACES: dict[str, tuple[str, str]] = {
    "варшава": ("Польша", "Варшава"), "варшаву": ("Польша", "Варшава"), "варшаве": ("Польша", "Варшава"),
    "бухарест": ("Румыния", "Бухарест"), "бухаресте": ("Румыния", "Бухарест"), "бухареста": ("Румыния", "Бухарест"),
    "софия": ("Болгария", "София"), "софию": ("Болгария", "София"), "софии": ("Болгария", "София"),
    "будапешт": ("Венгрия", "Будапешт"), "будапеште": ("Венгрия", "Будапешт"),
    "берлин": ("ГДР", "Берлин"), "берлине": ("ГДР", "Берлин"), "берлина": ("ГДР", "Берлин"),
    "прага": ("Чехословакия", "Прага"), "праге": ("Чехословакия", "Прага"),
    "праги": ("Чехословакия", "Прага"), "прагу": ("Чехословакия", "Прага"),
    "карловы вары": ("Чехословакия", "Карловы Вары"), "карловых вар": ("Чехословакия", "Карловы Вары"),
    "белград": ("Югославия", "Белград"), "белграда": ("Югославия", "Белград"), "белграде": ("Югославия", "Белград"),
    "загреб": ("Югославия", "Загреб"), "любляна": ("Югославия", "Любляна"),
    "хельсинки": ("Финляндия", "Хельсинки"),
    "париж": ("Франция", "Париж"), "париже": ("Франция", "Париж"),
    "лондон": ("Великобритания", "Лондон"), "лондоне": ("Великобритания", "Лондон"),
    "вашингтон": ("США", "Вашингтон"), "нью-йорк": ("США", "Нью-Йорк"),
    "оттава": ("Канада", "Оттава"),
    "пекин": ("Китай", "Пекин"), "пекине": ("Китай", "Пекин"),
    "токио": ("Япония", "Токио"),
    "дели": ("Индия", "Дели"),
    "гавана": ("Куба", "Гавана"), "гаване": ("Куба", "Гавана"), "гаавана": ("Куба", "Гавана"),
    "ульан-батор": ("Монголия", "Улан-Батор"), "улан-батор": ("Монголия", "Улан-Батор"),
    "бонн": ("ФРГ", "Бонн"), "бонне": ("ФРГ", "Бонн"),
    "франкфурт": ("ФРГ", "Франкфурт"),
    "вена": ("Австрия", "Вена"), "вене": ("Австрия", "Вена"),
    "рим": ("Италия", "Рим"), "риме": ("Италия", "Рим"),
    "мадрид": ("Испания", "Мадрид"),
    "лиссабон": ("Португалия", "Лиссабон"),
    "стокгольм": ("Швеция", "Стокгольм"),
    "осло": ("Норвегия", "Осло"),
    "брюссель": ("Бельгия", "Брюссель"),
    "амстердам": ("Нидерланды", "Амстердам"),
    "афины": ("Греция", "Афины"),
    "анкара": ("Турция", "Анкара"),
    "тегеран": ("Иран", "Тегеран"), "тегеране": ("Иран", "Тегеран"),
    "кабул": ("Афганистан", "Кабул"),
    "дамаск": ("Сирия", "Дамаск"),
    "багдад": ("Ирак", "Багдад"),
    "каир": ("Египет", "Каир"), "каире": ("Египет", "Каир"),
    "алжир": ("Алжир", "Алжир"),
    "триполи": ("Ливия", "Триполи"),
    "ханой": ("Вьетнам", "Ханой"), "ханое": ("Вьетнам", "Ханой"),
    "пхеньян": ("КНДР", "Пхеньян"),
    "исламабад": ("Пакистан", "Исламабад"),
    "дубай": ("ОАЭ", "Дубай"),
    "беловежская пуща": ("Польша", "Беловежская пуща"),
    "беловежской пуще": ("Польша", "Беловежская пуща"),
    "братислава": ("Чехословакия", "Братислава"), "братиславе": ("Чехословакия", "Братислава"),
    "братиславу": ("Чехословакия", "Братислава"),
    "дрезден": ("ГДР", "Дрезден"), "дрездене": ("ГДР", "Дрезден"),
    "кокчетав": ("СССР", "Кокчетав"), "кокчетаве": ("СССР", "Кокчетав"),
    "заречье": ("СССР", "Заречье"), "заречья": ("СССР", "Заречье"), "заречью": ("СССР", "Заречье"),
    "будаnешт": ("Венгрия", "Будапешт"), "будаnеште": ("Венгрия", "Будапешт"),
    "будаnешта": ("Венгрия", "Будапешт"), "будаnеш": ("Венгрия", "Будапешт"),
    "республику кuba": ("Куба", "Куба"), "республике кuba": ("Куба", "Куба"),
    "республику куба": ("Куба", "Куба"), "республике куба": ("Куба", "Куба"),
    "польшу": ("Польша", "Польша"), "польше": ("Польша", "Польша"), "польша": ("Польша", "Польша"),
    "пнр": ("Польша", "Польша"),
    "чехословакию": ("Чехословакия", "Чехословакия"),
    "чехословакии": ("Чехословакия", "Чехословакия"),
    "чехасловакию": ("Чехословакия", "Чехословакия"),
    "чехасловакии": ("Чехословакия", "Чехословакия"),
    "чсср": ("Чехословакия", "Чехословакия"),
    "венгрию": ("Венгрия", "Венгрия"), "венгрии": ("Венгрия", "Венгрия"), "внр": ("Венгрия", "Венгрия"),
    "гдр": ("ГДР", "ГДР"), "фрг": ("ФРГ", "ФРГ"),
    "румынию": ("Румыния", "Румыния"), "румынии": ("Румыния", "Румыния"),
    "болгарию": ("Болгария", "Болгария"), "болгарии": ("Болгария", "Болгария"), "нрб": ("Болгария", "Болгария"),
    "югославию": ("Югославия", "Югославия"), "югославии": ("Югославия", "Югославия"),
    "кубу": ("Куба", "Куба"), "кубе": ("Куба", "Куба"), "куба": ("Куба", "Куба"),
    "республике куба": ("Куба", "Куба"), "республику куба": ("Куба", "Куба"), "на кубе": ("Куба", "Куба"),
    "монголию": ("Монголия", "Монголия"), "монголии": ("Монголия", "Монголия"), "мнр": ("Монголия", "Монголия"),
    "монгольской народной республике": ("Монголия", "Монголия"),
    "монгольской народной республики": ("Монголия", "Монголия"),
    "польской народной республике": ("Польша", "Польша"),
    "польской народной рсснуб": ("Польша", "Польша"),
    "индию": ("Индия", "Индия"), "индии": ("Индия", "Индия"),
    "финляндию": ("Финляндия", "Финляндия"), "финляндии": ("Финляндия", "Финляндия"),
    "францию": ("Франция", "Франция"), "сша": ("США", "США"),
    "иран": ("Иран", "Иран"), "иране": ("Иран", "Иран"), "дрв": ("Вьетнам", "Вьетнам"),
    "узбекистане": ("СССР", "Узбекистан"), "узбекистан": ("СССР", "Узбекистан"),
    "казахстане": ("СССР", "Казахстан"), "казахстан": ("СССР", "Казахстан"),
    "молдавии": ("СССР", "Молдавия"), "молдавия": ("СССР", "Молдавия"),
    "грузии": ("СССР", "Грузия"), "украине": ("СССР", "Украина"),
    "белоруссии": ("СССР", "Белоруссия"),
    "азербайджане": ("СССР", "Азербайджан"), "армении": ("СССР", "Армения"),
    "ленинград": ("СССР", "Ленинград"), "ленинграде": ("СССР", "Ленинград"),
    "киев": ("СССР", "Киев"), "киеве": ("СССР", "Киев"),
    "минск": ("СССР", "Минск"), "минске": ("СССР", "Минск"),
    "ташкент": ("СССР", "Ташкент"), "ташкента": ("СССР", "Ташкент"), "ташкенте": ("СССР", "Ташкент"),
    "алма-ата": ("СССР", "Алма-Ата"), "алма-ату": ("СССР", "Алма-Ата"), "алма-ате": ("СССР", "Алма-Ата"),
    "баку": ("СССР", "Баку"), "тбилиси": ("СССР", "Тбилиси"),
    "ереван": ("СССР", "Ереван"), "ереване": ("СССР", "Ереван"),
    "кишинев": ("СССР", "Кишинёв"), "кишинёв": ("СССР", "Кишинёв"),
    "волгоград": ("СССР", "Волгоград"), "волгограде": ("СССР", "Волгоград"),
    "свердловск": ("СССР", "Свердловск"), "новосибирск": ("СССР", "Новосибирск"),
    "иркутск": ("СССР", "Иркутск"), "иркутске": ("СССР", "Иркутск"),
    "краснодар": ("СССР", "Краснодар"), "владивосток": ("СССР", "Владивосток"),
    "хабаровск": ("СССР", "Хабаровск"), "мурманск": ("СССР", "Мурманск"),
    "архангельск": ("СССР", "Архангельск"),
    "горький": ("СССР", "Горький"), "горьком": ("СССР", "Горький"),
    "самарканд": ("СССР", "Самарканд"), "фрунзе": ("СССР", "Фрунзе"),
    "душанбе": ("СССР", "Душанбе"), "ашхабад": ("СССР", "Ашхабад"),
    "рига": ("СССР", "Рига"), "риге": ("СССР", "Рига"),
    "таллин": ("СССР", "Таллин"), "вильнюс": ("СССР", "Вильнюс"),
    "запорожье": ("СССР", "Запорожье"), "днепропетровск": ("СССР", "Днепропетровск"),
    "харьков": ("СССР", "Харьков"), "одесса": ("СССР", "Одесса"), "одессе": ("СССР", "Одесса"),
    "новгород": ("СССР", "Новгород"), "смоленск": ("СССР", "Смоленск"),
    "воронеж": ("СССР", "Воронеж"),
    "ростов": ("СССР", "Ростов"), "ростове": ("СССР", "Ростов"),
    "ставрополь": ("СССР", "Ставрополь"), "красноярск": ("СССР", "Красноярск"),
    "омск": ("СССР", "Омск"), "челябинск": ("СССР", "Челябинск"),
    "пермь": ("СССР", "Пермь"), "уфа": ("СССР", "Уфа"),
    "казань": ("СССР", "Казань"), "саратов": ("СССР", "Саратов"),
    "якутск": ("СССР", "Якутск"), "брест": ("СССР", "Брест"),
    "завидово": ("СССР", "Завидово"), "завндово": ("СССР", "Завидово"),
    "ялта": ("СССР", "Ялта"), "ялте": ("СССР", "Ялта"),
    "крым": ("СССР", "Крым"), "крыму": ("СССР", "Крым"),
    "симферополь": ("СССР", "Симферополь"), "сочи": ("СССР", "Сочи"),
    "пицунда": ("СССР", "Пицунда"), "гагра": ("СССР", "Гагра"),
    "феодосию": ("СССР", "Феодосия"), "феодосии": ("СССР", "Феодосия"),
    "кисловодск": ("СССР", "Кисловодск"), "кисловодске": ("СССР", "Кисловодск"),
    "барвиха": ("СССР", "Барвиха"), "барвихе": ("СССР", "Барвиха"),
    "яjпе": ("СССР", "Ялта"), "яjjте": ("СССР", "Ялта"), "яjlте": ("СССР", "Ялта"),
    "яюе": ("СССР", "Ялта"), "ялтe": ("СССР", "Ялта"),
    "кисjjоводске": ("СССР", "Кисловодск"), "кисjюводске": ("СССР", "Кисловодск"),
    "кисловодске": ("СССР", "Кисловодск"),
    "тула": ("СССР", "Тула"), "тулу": ("СССР", "Тула"), "туле": ("СССР", "Тула"),
    "новороссийск": ("СССР", "Новороссийск"), "новороссийске": ("СССР", "Новороссийск"),
    "донецк": ("СССР", "Донецк"), "донецке": ("СССР", "Донецк"),
    "байконур": ("СССР", "Байконур"), "байконуре": ("СССР", "Байконур"),
    "байkонур": ("СССР", "Байконур"), "байkонуре": ("СССР", "Байконур"),
    "владивосток": ("СССР", "Владивосток"), "владивостоке": ("СССР", "Владивосток"),
    "молдавию": ("СССР", "Молдавия"),
    "будапешта": ("Венгрия", "Будапешт"),
    "зашщово": ("СССР", "Завидово"), "завилово": ("СССР", "Завидово"),
    "заречье-б": ("СССР", "Заречье"), "заречье-б в": ("СССР", "Заречье"),
}

REST_CITY_OCR: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^яlt[aeуe]?$|^я[lji1\.]{2,4}$", re.I), "Ялта"),
    (re.compile(r"^соч", re.I), "Сочи"),
    (re.compile(r"^крым", re.I), "Крым"),
    (re.compile(r"^кислов", re.I), "Кисловодск"),
    (re.compile(r"^барвих", re.I), "Барвиха"),
    (re.compile(r"^зареч", re.I), "Заречье"),
    (re.compile(r"^завид|^завил|^за[щш]", re.I), "Завидово"),
    (re.compile(r"^симфер", re.I), "Симферополь"),
    (re.compile(r"^пицунд", re.I), "Пицунда"),
    (re.compile(r"^гагр", re.I), "Гагра"),
    (re.compile(r"^феодос", re.I), "Феодосия"),
    (re.compile(r"^астрах", re.I), "Астрахань"),
]

LINE_REST_OCR: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(?:^|[\s«\"'])яlt[aeуe]?(?:[\s\-,\.»\"']|$)", re.I), "Ялта"),
    (re.compile(r"(?:^|[\s«\"'])я[lji1\.]{2,4}(?:[\s\-,\.»\"']|$)", re.I), "Ялта"),
    (re.compile(r"зар[еэсc%][чььяю]?", re.I), "Заречье"),
    (re.compile(r"завид[оа]?(?:во)?|завил[оа]?во|за[щш][iи]?ово|зашщово", re.I), "Завидово"),
]

_PLACE_KEYS_BY_LEN = sorted(
    (k for k in PLACES if len(k) >= 4),
    key=len,
    reverse=True,
)

DEPARTURE_RE = re.compile(
    r"(?:отбыл|выехал|вылетел|уехал|направился|прибыл|прилетел|приехал|следовал|готовился|прибыли)",
    re.I,
)

COMMAND_END_RE = re.compile(
    r"(?:вернул(?:ся|ась)|возвратился).*?(?:из\s+)?командиров",
    re.I,
)

COUNTRY_KEYS = {
    key: country
    for key, (country, city) in PLACES.items()
    if country != "СССР" and city == country
}
COUNTRY_KEYS.update({
    "чехасловакию": "Чехословакия",
    "чехасловакии": "Чехословакия",
    "югославию": "Югославия",
    "срр": "Румыния",
})

UNREC_JUNK = (
    "кремл", "аэроп", "аэро", "бкд", "кдс", "лужник", "посольств", "дач",
    "мероприят", "командиров", "обследов", "больниц", "гостиниц", "кабинет",
    "заседан", "переговор", "документ", "работ", "домой", "час", "ночи",
    "полноч", "внуков", "шереметьев", "цк", "приемн", "поликлин", "санатор",
    "министерств", "дворец", "стадион", "концерт", "хокке", "парад",
    "место", "встреч", "торжеств", "сесси", "резиден", "провод", "прием",
    "обед", "завтрак", "конферен", "парад", "поезд", "пути", "съезд",
)

COUNTRY_LINE_PATTERNS = [
    (r"\bв\s+(?:г\.?\s*)?болгари\w*\b", "Болгария"),
    (r"\bв\s+(?:г\.?\s*)?(?:республик\w+\s+)?куб[аеу]\b", "Куба"),
    (r"\bв\s+(?:г\.?\s*)?югослав\w*\b", "Югославия"),
    (r"\bв\s+(?:г\.?\s*)?польш\w*\b", "Польша"),
    (r"\bв\s+(?:г\.?\s*)?румын\w*\b", "Румыния"),
    (r"\bв\s+(?:г\.?\s*)?венгри\w*\b", "Венгрия"),
    (r"\bв\s+(?:г\.?\s*)?чех\w*\b", "Чехословакия"),
    (r"\bв\s+(?:г\.?\s*)?франц\w*\b", "Франция"),
    (r"\bв\s+(?:г\.?\s*)?монголи\w*\b", "Монголия"),
    (r"\bв\s+(?:г\.?\s*)?инди\w*\b", "Индия"),
    (r"\bв\s+(?:г\.?\s*)?финлянд\w*\b", "Финляндия"),
    (r"\bв\s+(?:г\.?\s*)?иран\w*\b", "Иран"),
    (r"венгерск\w+\s+народн\w+\s+республ", "Венгрия"),
    (r"венгерск\w+\s+н/\s*народ", "Венгрия"),
    (r"\bв\s+(?:г\.?\s*)?молдав\w*\b", "СССР"),
]

DATE_HDR = re.compile(r"^###\s+(.+)$", re.MULTILINE)
YEAR_HDR = re.compile(r"^##\s+(\d{4})\s*$", re.MULTILINE)

_V = TRAVEL_VERBS
DEST_PATTERNS = [
    re.compile(
        r"(?:" + _V + r")"
        r"(?:\s+[^.]{0,120}?)?\s+в\s+"
        r"(?:г\.?\s*|гор\.?\s*|столиц[уе]\s+)?"
        r"([\w«»\-]+(?:\s+[\w«»\-]+){0,3})",
        re.I,
    ),
    re.compile(
        r"(?:" + _V + r")"
        r"(?:\s+[^.]{0,120}?)?\s+на\s+"
        r"(?!празднован|торжеств)"
        r"(?:г\.?\s*|гор\.?\s*)?"
        r"([\w«»\-]+(?:\s+[\w«»\-]+){0,3})",
        re.I,
    ),
    re.compile(
        r"(?:с\s+)?(?:официальным|неофициальным|дружеским)\s+визитом\s+(?:в\s+)?"
        r"(?:г\.?\s*)?([\w«»\-]+(?:\s+[\w«»\-]+){0,3})",
        re.I,
    ),
    re.compile(
        r"находил(?:ся|ась)\s+(?:с\s+визитом\s+)?(?:в|на)\s+"
        r"(?:г\.?\s*|гор\.?\s*)?([\w«»\-]+(?:\s+[\w«»\-]+){0,3})",
        re.I,
    ),
    re.compile(
        r"находил(?:ся|ась|ится)\s+на\s+отдыхе\s+в\s+"
        r"(?:г\.?\s*|гор\.?\s*|r\.?\s*)?([\w«»\-]+(?:\s+[\w«»\-]+){0,2})",
        re.I,
    ),
    re.compile(
        r"на\s+отдыхе\s+в\s+(?:г\.?\s*|гор\.?\s*|r\.?\s*)?([\w«»\-]+(?:\s+[\w«»\-]+){0,2})",
        re.I,
    ),
    re.compile(r"на\s+отдыхе\s*\(\s*([\w«»\-]+)", re.I),
    re.compile(r"находился\s+на\s+отдыхе\s*\(\s*([\w«»\-]+)", re.I),
    re.compile(
        r"в\s+командировке\s*\(\s*в\s+"
        r"(?:г\.?\s*)?([\w«»\-]+(?:\s+[\w«»\-]+){0,2})\s*\)",
        re.I,
    ),
    re.compile(
        r"готовился\s+к\s+поездке\s+в\s+"
        r"(?:г\.?\s*)?([\w«»\-]+)",
        re.I,
    ),
    re.compile(
        r"следовал\s+(?:в|на)\s+"
        r"(?:г\.?\s*)?([\w«»\-]+(?:\s+[\w«»\-]+){0,2})",
        re.I,
    ),
    re.compile(
        r"(?:делегаци\w+|л\.?\s*и\.?|сопровожда\w+).{0,80}?(?:прибыли|прибыл[ia]?)\s+(?:в|н)\s+"
        r"(?:г\.?\s*)?([\w«»\-]+)",
        re.I,
    ),
    re.compile(
        r"во\s+главе\s+[^.]{0,80}?(?:отбыл|выехал|вылетел|направился)\s+"
        r"(?:[^.]{0,40}?\s+)?(?:в|на)\s+"
        r"(?:г\.?\s*)?([\w«»\-]+(?:\s+[\w«»\-]+){0,3})",
        re.I,
    ),
    re.compile(
        r"(?:уехал|выехал|отбыл|вылетел)\s+"
        r"(?:в\s+)?командировк[уе]\s+(?:в\s+)?"
        r"(?:г\.?\s*)?([\w«»\-]+)",
        re.I,
    ),
    re.compile(r"(?:прибыл|вылетел|отбыл|выехал)[^.]{0,80}?г\.\s*([\w«»\-]+)", re.I),
    re.compile(r"находил(?:ся|ась|ится)\s+в\s+г\.?\s*([\w«»\-]+)", re.I),
    re.compile(r"республик[aeu]\s+([\w«»\-]+)", re.I),
    re.compile(r"командировк[ae][^.]{0,50}?г\.?\s*([\w«»\-]+)", re.I),
    re.compile(r"(?:^|[.\s;])в\s+([\w«»\"'\-]+)\s+на\s+отдыхе", re.I),
    re.compile(
        r"находил(?:ся|ась|ится)\s+в\s+([\w«»\"'\-]+)\s*-?\s*на\s+отдыхе",
        re.I,
    ),
    re.compile(r"на\s+пути\s+(?:в|из)\s+(?:г\.?\s*)?([\w«»\-]+)", re.I),
    re.compile(r"г\.?\s*([\w«»\-]+)\s*\(\s*[\w«»\-]+\s*\)", re.I),
    re.compile(
        r"(?:^|[.\s])[^.]{0,40}?\(\s*[^)]*?\s+в\s+(?:г\.?\s*)?([\w«»\-]+)\s*\)",
        re.I,
    ),
    re.compile(
        r"(?:вернул(?:ся|ась)|возвратился|выехал|отбыл|приехал|прибыл)"
        r"(?:\s+[^.]{0,100}?)?\s+из\s+"
        r"(?:г\.?\s*)?[«\"']?([\w«»\"'\-]+)",
        re.I,
    ),
    re.compile(
        r"(?:вернул(?:ся|ась)|возвратился|прибыл|приехал)"
        r"(?:\s+[^.]{0,100}?)?\s+(?:на\s+дач[уе]\s+)?в\s+"
        r"[«\"']?([\w«»\"'\-]+)",
        re.I,
    ),
]

RETURN_HOME_RE = re.compile(
    r"(?:вернул(?:ся|ась)|возвратился|прибыл|отбыл|выехал|приехал)"
    r".{0,80}?(?:в|на)\s+(?:г\.?\s*)?(?:москв|домой|родину|внуково|шереметьев)",
    re.I,
)


@dataclass
class Trip:
    year: str
    date: str
    country: str | None
    city: str | None
    line: str
    category: str
    event: str


def csv_field(value: str | None) -> str:
    if value is None:
        return "None"
    return f'"{value.replace(chr(34), chr(39))}"'


def clean_token(raw: str) -> str:
    s = raw.lower().strip(" .,;:!?»«\"'()[]~•")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"^(?:г\.?|гор\.?|r\.?)\s*", "", s)
    s = re.split(r"[,;\-–—(\[]", s)[0].strip()
    return s


def lookup(raw: str) -> tuple[str, str | None, str] | None:
    s = clean_token(raw)
    if not s or s in HOME:
        return None
    if re.match(r"^[гр]$", s):
        return None
    for n in (3, 2, 1):
        parts = s.split()
        if len(parts) >= n:
            key = " ".join(parts[:n])
            if key in PLACES:
                return _cat(*PLACES[key])
    for key, val in PLACES.items():
        if len(s) >= 4 and (s.startswith(key) or key.startswith(s)):
            return _cat(*val)
    for pat, city in REST_CITY_OCR:
        if pat.search(s):
            return _cat("СССР", city)
    return None


def resolve_place(raw: str) -> tuple[str, str | None, str] | None:
    words = raw.split()
    for n in range(len(words), 0, -1):
        res = lookup(" ".join(words[:n]))
        if res:
            return res
    return None


def _cat(country: str, city: str) -> tuple[str, str | None, str]:
    if country != "СССР" and city == country:
        city = None
    if country == "СССР":
        return country, city, "ussr"
    return country, city, "foreign"


def trip_key(country: str, city: str | None) -> str:
    if country != "СССР":
        return country
    return f"{country}|{city}"


def normalize_line(line: str) -> str:
    line = re.sub(r"находил(?:ся|ась|ится)(?=в[а-яё])", r"\g<0> ", line, flags=re.I)
    line = re.sub(r"(?<=[.\s])в(?=[ЯяЮю])", "в ", line)
    line = re.sub(r"(\d)([Яя])", r"\1 \2", line)
    return line


def _is_escort_or_local(line: str) -> bool:
    low = line.lower()
    if re.search(
        r"провожал|проводы|на\s+провод|правожал|правожать|"
        r"для\s+встречи|траурн|"
        r"[pn][оo0]сольств|посольств|"
        r"екатерининск|свердловск(?:ий|ого)\s+зал|"
        r"колонный\s+зал|"
        r"прибыл\s+на\s+работу|"
        r"переговор.*делегац|делегац.*переговор|"
        r"правож.*делег|провож.*делег|делег.*правож|"
        r"совпосл",
        low,
    ):
        if re.search(
            r"(?:отбыл|вылетел)\s+(?:[^.]{0,80}?\s+)?(?:в|на)\s+(?:"
            r"г\.?\s*)?(?:инди|франц|польш|чех|болгар|венгр|фрг|куб|"
            r"республик[aeu]\s+куб|монголи|финлянд)",
            low,
        ):
            return False
        return True
    if re.search(r"приемную\s+звонили|(?:^|[\s,.])звонили\b", low):
        return True
    if re.search(r"\(посол\s+в|\(послом\s+в|,\s*посол\s+в|\(посоl\s+в|совпосл\s+в", low):
        return True
    if re.search(
        r"выехал\s+(?:во?\s+)?(?:внуков|шереметьев|аэро)[^.]{0,60}(?:"
        r"встреч|провож|провод|правож)",
        low,
    ):
        return True
    if re.search(r"принял\s+(?:т\.|тов)", low) and re.search(r"(?:сов)?посол\s+в", low):
        return True
    if re.search(r"выехал\s+в\s+поликлин|приехал\s+в\s+больниц", low):
        return True
    return False


def _place_about_other_person(line: str, key: str) -> bool:
    low = line.lower()
    if len(key) < 4:
        return False
    if not re.search(rf"\([^)]*\.{0,80}{re.escape(key[:5])}", low):
        return False
    before = low.split("(", 1)[0]
    return not re.search(r"л\.?\s*и\.|брежнев", before, re.I)


def _is_spurious_match(line: str, country: str, city: str | None) -> bool:
    if _is_escort_or_local(line):
        return True
    low = line.lower()
    if city and re.search(rf"\(посол\s+в\s+[^)]*{re.escape(country[:4].lower())}", low):
        return True
    if city == "Каир" and re.search(r"кремл", low) and not re.search(r"каир", low):
        return True
    if city == "Тула" and re.search(r"\(тула\)", low) and not re.search(r"находил(?:ся|ась|ится)\s+в\s+г\.?\s*тул", low):
        return True
    if city == "Новороссийск" and _place_about_other_person(line, "новор"):
        return True
    if city == "Ялта" and re.search(r"переяслав", low):
        return True
    if city:
        for key, (_, ci) in PLACES.items():
            if ci == city and _place_about_other_person(line, key):
                return True
    return False


def _apply_country_line_patterns(
    found: dict[str, tuple[str, str | None, str, str]],
    line: str,
) -> None:
    if not TRAVEL_VERB_RE.search(line) or is_non_trip_line(line):
        return
    for pat, country in COUNTRY_LINE_PATTERNS:
        if not re.search(rf"(?:{TRAVEL_VERBS}).{{0,120}}?{pat}", line, re.I):
            continue
        city: str | None = None
        cat = "foreign" if country != "СССР" else "ussr"
        if country == "СССР" and re.search(r"молдав", line, re.I):
            city = "Молдавия"
        if not _is_spurious_match(line, country, city):
            _add_destination(found, country, city, cat, line)
        break


def _key_in_line(key: str, low: str) -> bool:
    idx = 0
    while True:
        pos = low.find(key, idx)
        if pos < 0:
            return False
        before_ok = pos == 0 or not low[pos - 1].isalpha()
        after = pos + len(key)
        after_ok = after >= len(low) or not low[after].isalpha()
        if before_ok and after_ok:
            return True
        idx = pos + 1


def scan_line_for_places(line: str, limit: int = 3) -> list[tuple[str, str | None, str]]:
    low = normalize_line(line).lower()
    found: list[tuple[int, int, str, str | None, str]] = []

    for key in _PLACE_KEYS_BY_LEN:
        if not _key_in_line(key, low):
            continue
        country, city, cat = _cat(*PLACES[key])
        if _is_spurious_match(line, country, city):
            continue
        specificity = 2 if city else 1
        found.append((specificity, len(key), country, city, cat))

    for pat, city in LINE_REST_OCR:
        if pat.search(low):
            country, city, cat = _cat("СССР", city)
            if not _is_spurious_match(line, country, city):
                found.append((2, 8, country, city, cat))

    found.sort(key=lambda x: (-x[0], -x[1]))
    seen: set[str] = set()
    results: list[tuple[str, str | None, str]] = []
    for _, _, country, city, cat in found:
        dedup = f"{country}|{city}"
        if dedup in seen:
            continue
        seen.add(dedup)
        results.append((country, city, cat))
        if len(results) >= limit:
            break
    return results


def _has_travel_context(line: str) -> bool:
    return bool(
        TRAVEL_VERB_RE.search(line)
        or re.search(r"командиров|на\s+отдыхе|на\s+пути|на\s+даче|был\s+у\s+себя", line, re.I)
    )


def _is_dacha_commute(line: str) -> bool:
    low = line.lower()
    return bool(re.search(
        r"(?:выехал|отбыл|уехал|вылетел)"
        r".{0,80}?из\s+"
        r"(?:зареч|завид)"
        r".{0,80}?"
        r"(?:в|во|на)\s+(?:"
        r"москв|кремл|площад|красн|внуково|шерем|бкд|кдс|"
        r"работ|поликлин|больниц|аэро"
        r")",
        low,
    ))


def _scan_fallback(line: str, found: dict) -> list[tuple[str, str | None, str]]:
    if found and not any(v[1] is None for v in found.values()):
        return []
    if not (
        _has_travel_context(line)
        or re.search(r"республик[aeu]|на\s+даче|был\s+у\s+себя", line, re.I)
    ):
        return []
    if is_non_trip_line(line):
        return []
    hits = scan_line_for_places(line, limit=1)
    if not hits:
        return []
    country, city, cat = hits[0]
    if _is_spurious_match(line, country, city):
        return []
    if found:
        country, city, _cat = hits[0]
        if city and f"{country}|None" in found:
            return hits
        return []
    if hits[0][1] is None and re.search(r"переговор|площад", line, re.I):
        return []
    return hits


def is_non_trip_line(line: str) -> bool:
    return _is_escort_or_local(line)


def _travel_event(line: str) -> str:
    return "departure" if DEPARTURE_RE.search(line) else "stay"


def _dacha_departure_only(line: str, city: str | None, raw: str | None = None) -> bool:
    if city not in ("Заречье", "Завидово"):
        return False
    low = normalize_line(line).lower()
    stem = "зареч" if city == "Заречье" else "завид"
    tok = clean_token(raw) if raw else ""
    pos = low.find(tok[: min(len(tok), 6)]) if tok else low.find(stem)
    if pos < 0:
        pos = low.find(stem)
    if pos < 0:
        return False
    before = low[max(0, pos - 20):pos]
    if re.search(r"на\s+дач[уе]\s+в\s+[«\"']?\s*$", before):
        return False
    if re.search(r"\bв\s+(?:г\.?\s*)?[«\"']?\s*$", before):
        return False
    return bool(re.search(r"из\s+[«\"']?\s*$", before))


def _add_destination(
    found: dict[str, tuple[str, str | None, str, str]],
    country: str,
    city: str | None,
    cat: str,
    line: str,
    evt: str | None = None,
    raw: str | None = None,
) -> None:
    if _dacha_departure_only(line, city, raw):
        return
    if _is_spurious_match(line, country, city):
        return
    for key, (c, ci, ca, ev) in list(found.items()):
        if c == country and ci is None and city:
            del found[key]
    dedup = f"{country}|{city}"
    if dedup not in found:
        found[dedup] = (country, city, cat, evt or _travel_event(line))


def is_brezhnev_line(line: str, li_context: bool) -> bool:
    if LI_RE.search(line):
        return True
    if li_context and TRAVEL_VERB_RE.search(line):
        return True
    return False


def extract_destinations(line: str) -> list[tuple[str, str | None, str, str]]:
    if is_non_trip_line(line):
        return []

    line = normalize_line(line)
    found: dict[str, tuple[str, str | None, str, str]] = {}

    for pat in DEST_PATTERNS:
        for m in pat.finditer(line):
            res = resolve_place(m.group(1))
            if not res:
                continue
            if (
                _is_dacha_commute(line)
                and res[0] == "СССР"
                and res[1] in ("Заречье", "Завидово")
            ):
                continue
            _add_destination(found, res[0], res[1], res[2], line, raw=m.group(1))

    _apply_country_line_patterns(found, line)

    scan_hits = _scan_fallback(line, found)

    if not found and scan_hits:
        country, city, cat = scan_hits[0]
        if not (
            _is_dacha_commute(line)
            and country == "СССР"
            and city in ("Заречье", "Завидово")
        ):
            _add_destination(found, country, city, cat, line)
    else:
        for country, city, cat in scan_hits:
            if city and f"{country}|None" in found:
                _add_destination(found, country, city, cat, line)

    if not found and _has_travel_context(line):
        for raw in _collect_unrec_raws(line):
            res = resolve_place(raw)
            if res:
                _add_destination(found, res[0], res[1], res[2], line, raw=raw)
                break

    return list(found.values())


def parse_entries(text: str):
    start = text.find(SKIP_UNTIL)
    if start == -1:
        start = 0
    pre = text[:start]
    year_m = [m for m in YEAR_HDR.finditer(pre) if int(m.group(1)) in DIARY_YEARS]
    initial_year = year_m[-1].group(1) if year_m else ""
    text = text[start:]

    year, date = initial_year, ""
    li_context = False

    for line in text.splitlines():
        ls = line.strip()
        ym = YEAR_HDR.match(ls)
        if ym:
            y = int(ym.group(1))
            if y in DIARY_YEARS:
                year = ym.group(1)
            continue
        dm = DATE_HDR.match(ls)
        if dm:
            date = dm.group(1)
            li_context = False
            continue
        if not ls or ls.startswith("<!--") or ls.startswith("#"):
            continue
        if not year:
            continue
        if LI_RE.search(ls):
            li_context = True
        yield year, date, ls, li_context


def segment_trips(entries) -> list[Trip]:
    trips: list[Trip] = []
    current_key: str | None = None
    for year, date, line, li_context in entries:
        if not is_brezhnev_line(line, li_context):
            continue
        if is_local_movement_line(line):
            continue

        dests = extract_destinations(line)
        for country, city, cat, evt in dests:
            key = trip_key(country, city)
            if key != current_key:
                trips.append(Trip(year, date, country, city, line[:160], cat, evt))
                current_key = key

        if RETURN_HOME_RE.search(line) or COMMAND_END_RE.search(line):
            current_key = None
        elif re.search(
            r"(?:выехал|отбыл|уехал|вылетел).{0,60}?из\s+[«\"']?(?:зареч|завид)",
            line,
            re.I,
        ):
            current_key = None
        elif re.search(r"(?:вернулся|возвратился|прибыл)\s+из\s+", line, re.I):
            if not re.search(r"прибыл\s+в\s+(?:г\.?\s*)?\w", line, re.I):
                current_key = None

    return trips


UNREC_DEST_RE = re.compile(
    r"(?:" + TRAVEL_VERBS + r")"
    r"(?:\s+[^.]{0,100}?)?\s+(?:в|на)\s+"
    r"(?:г\.?\s*)?([\w«»\-]+(?:\s+[\w«»\-]+){0,2})",
    re.I,
)

UNREC_REST_RE = re.compile(
    r"на\s+отдыхе\s*(?:\(\s*([\w«»\-]+)|в\s+([\w«»\-]+))",
    re.I,
)


def _match_country_key(token: str) -> str | None:
    s = clean_token(token)
    if not s:
        return None
    words = s.split()
    for n in range(len(words), 0, -1):
        key = " ".join(words[:n])
        if key in COUNTRY_KEYS:
            return COUNTRY_KEYS[key]
    for key, country in COUNTRY_KEYS.items():
        if len(s) >= 4 and (s.startswith(key) or key.startswith(s)):
            return country
    return None


def _valid_unrec_token(token: str) -> bool:
    first = clean_token(token.split()[0])
    if not first or first in HOME or len(first) < 4:
        return False
    if re.match(r"^[\dоoil1\W]+$", first):
        return False
    if any(first.startswith(j) for j in UNREC_JUNK):
        return False
    return True


def _country_from_travel_line(line: str) -> str | None:
    if not TRAVEL_VERB_RE.search(line):
        return None
    if re.search(r"посольств|делегац", line, re.I):
        return None
    for key, country in sorted(COUNTRY_KEYS.items(), key=lambda x: -len(x[0])):
        pat = rf"(?:{TRAVEL_VERBS}).{{0,120}}?\s+в\s+(?:г\.?\s*)?{re.escape(key)}\b"
        if re.search(pat, line, re.I):
            return country
    for pat, country in COUNTRY_LINE_PATTERNS:
        if re.search(rf"(?:{TRAVEL_VERBS}).{{0,120}}?{pat}", line, re.I):
            return country
    return None


def _collect_unrec_raws(line: str) -> list[str]:
    raws: list[str] = []
    for m in UNREC_DEST_RE.finditer(line):
        raw = m.group(1).strip()
        if _valid_unrec_token(raw):
            raws.append(raw)
    m = UNREC_REST_RE.search(line)
    if m:
        raw = (m.group(1) or m.group(2) or "").strip()
        if _valid_unrec_token(raw):
            raws.append(raw)
    return raws


def extract_raw_destination(line: str) -> str | None:
    raws = _collect_unrec_raws(line)
    for raw in raws:
        if _match_country_key(raw):
            return raw
    return raws[0] if raws else None


def is_unrecognized_travel(line: str, li_context: bool) -> bool:
    if not is_brezhnev_line(line, li_context):
        return False
    if is_non_trip_line(line):
        return False
    if is_local_movement_line(line):
        return False
    if is_daily_commute_line(line):
        return False
    if extract_destinations(line):
        return False
    if not (
        TRAVEL_VERB_RE.search(line)
        or re.search(r"командиров|на\s+отдыхе", line, re.I)
    ):
        return False
    return _has_unresolved_travel_destination(line)


def collect_unrecognized(entries) -> list[Trip]:
    trips: list[Trip] = []
    seen: set[tuple[str, str, str]] = set()

    for year, date, line, li_context in entries:
        if not is_unrecognized_travel(line, li_context):
            continue
        key = (year, date, line[:120])
        if key in seen:
            continue
        seen.add(key)

        evt = "unknown"
        if re.search(
            r"(?:отбыл|выехал|вылетел|уехал|направился|прибыл|прилетел|приехал|следовал)",
            line,
            re.I,
        ):
            evt = "departure"

        trips.append(Trip(
            year=year,
            date=date,
            country=None,
            city=None,
            line=line[:160],
            category="нераспознанно",
            event=evt,
        ))
    return trips


def main():
    text = MD_PATH.read_text(encoding="utf-8")
    entries = list(parse_entries(text))
    recognized = segment_trips(entries)
    unrecognized = collect_unrecognized(entries)
    trips = recognized + unrecognized

    by_country: Counter = Counter()
    by_city: Counter = Counter()
    by_year: Counter = Counter()
    by_cat: Counter = Counter()

    for t in recognized:
        by_country[t.country] += 1
        if t.city:
            by_city[t.city] += 1
        by_year[t.year] += 1
        by_cat[t.category] += 1

    print("Поездки Брежнева (1965–1982)")
    print(f"Распознанных: {len(recognized)} (зарубеж {by_cat.get('foreign', 0)}, СССР {by_cat.get('ussr', 0)})")
    print(f"Нераспознанных: {len(unrecognized)}")

    print("\n── Зарубеж — по странам ──")
    for country, cnt in by_country.most_common():
        if any(t.country == country and t.category == "foreign" for t in recognized):
            print(f"  {cnt:3d}  {country}")

    print("\n── Зарубеж — по городам (топ-20) ──")
    fcity: Counter = Counter()
    for t in recognized:
        if t.category == "foreign" and t.city:
            fcity[f"{t.city} ({t.country})"] += 1
        elif t.category == "foreign":
            fcity[f"[страна] ({t.country})"] += 1
    for place, cnt in fcity.most_common(20):
        print(f"  {cnt:3d}  {place}")

    print("\n── СССР — топ-20 городов ──")
    for city, cnt in [(c, n) for c, n in by_city.most_common() if any(t.city == c and t.category == "ussr" for t in recognized)][:20]:
        print(f"  {cnt:3d}  {city}")

    print("\n── По годам (распознанные) ──")
    for year in sorted(by_year):
        f = sum(1 for t in recognized if t.year == year and t.category == "foreign")
        u = sum(1 for t in recognized if t.year == year and t.category == "ussr")
        print(f"  {year}: {by_year[year]:3d}  (заруб.{f} / СССР {u})")

    csv = MD_PATH.parent / "trips_segments.csv"
    with open(csv, "w", encoding="utf-8") as f:
        f.write("year,date,category,country,city,event,line\n")
        for t in trips:
            f.write(
                f"{csv_field(t.year)},{csv_field(t.date)},{csv_field(t.category)},"
                f"{csv_field(t.country)},{csv_field(t.city)},"
                f"{csv_field(t.event)},{csv_field(t.line)}\n"
            )
    print(f"\nCSV: {csv} — всего {len(trips)} ({len(recognized)} распозн. + {len(unrecognized)} нераспозн.)")


if __name__ == "__main__":
    main()
