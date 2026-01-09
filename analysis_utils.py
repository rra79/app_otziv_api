from collections import Counter

NEGATIVE = {
    "баг": "Баги",
    "ошиб": "Ошибки",
    "вылет": "Краши",
    "не работает": "Не работает",
    "медлен": "Производительность",
    "лага": "Производительность",
    "реклама": "Реклама",
    "подпис": "Подписка",
}

POSITIVE = {
    "удоб": "Удобство",
    "отлич": "Качество",
    "класс": "Качество",
    "полез": "Польза",
    "быстро": "Скорость",
}

def extract_problems_and_pluses(texts):
    problems = Counter()
    pluses = Counter()

    for t in texts:
        low = t.lower()
        for k, v in NEGATIVE.items():
            if k in low:
                problems[v] += 1
        for k, v in POSITIVE.items():
            if k in low:
                pluses[v] += 1

    return problems, pluses
