# Поездки Брежнева по записям секретариата (1965-1982)

Данные: **Записи секретарей Приемной Л. И. Брежнева. 1965-1982 гг.** (PDF издания -> MD -> `extract_trips.py` -> `trips_segments.csv` -> графики). Подробнее - [О_проекте.md](./О_проекте.md)

## Быстрый старт

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Пересобрать таблицу (нужен MD тома в корне проекта):

```bash
python extract_trips.py
```

Графики:

```bash
jupyter notebook notebooks/trips_analytics.ipynb
```

Ноутбук читает `trips_segments.csv`: сначала локальный файл в корне проекта, иначе [копию на Drive](https://drive.google.com/file/d/16NyoAdc-KGnpYZfBr-CLXO8wZweOYAY0/view?usp=sharing)

## Пайплайн

```
Brezhnev_…tom_2_2016.md  ->  extract_trips.py  ->  trips_segments.csv  ->  trips_analytics.ipynb
```

## Структура

```
extract_trips.py       парсер
load_trips.py          CSV для ноутбука
notebooks/             Plotly
Brezhnev_…2016.md      исходник (PDF->MD, обычно не в git)
trips_segments.csv     результат парсера
```

## Колонки `trips_segments.csv`

| Колонка | Смысл |
|---------|--------|
| `year` | год блока в MD |
| `date` | строка `### …` в дневнике |
| `category` | `ussr`, `foreign`, `нераспознанно` |
| `country` | страна, если разобрали |
| `city` | город или место |
| `event` | `departure`, `stay`, `unknown` |
| `line` | фрагмент исходной строки |

Распознанные - есть город, category не `нераспознанно`. Только страна - country есть, city пустой. Нераспознанные - category `нераспознанно`, country и city пустые
