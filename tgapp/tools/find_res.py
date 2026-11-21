import csv
import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent


def qualifying_rows(rows, column, score):
    thresholds = [(row, float(row[column])) for row in rows if row[column].strip()]
    if score > 270:
        thresholds.sort(key=lambda entry: entry[1], reverse=True)
    else:
        cutoff = round(score * 100 / 280.5)
        thresholds = [(row, threshold) for row, threshold in thresholds if threshold <= cutoff]
    return [row for row, _ in thresholds[:20]]


def format_rows(rows):
    return "".join(
        f"{index}. {row['UniverName'].replace('Va', 'va')}: {row['Name']}\n"
        for index, row in enumerate(rows, 1)
    )


def getResult(point, lang, typ, specs):
    if lang == "ru":
        with (DATA_DIR / "sLang.json").open(encoding="utf-8") as translations:
            specs = json.load(translations)[specs]
    first, second = specs.split("-", 1)
    with (DATA_DIR / "data.csv").open(encoding="utf-8", newline="") as file:
        rows = [
            row for row in csv.DictReader(file)
            if (row["Lang"], row["Type"], row["FirstSub"], row["SecondSub"])
            == (lang, typ, first, second)
        ]
    score = float(point)
    return tuple(format_rows(qualifying_rows(rows, column, score)) for column in ("PSchol", "PCont"))
