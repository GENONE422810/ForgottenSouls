"""Архетип — не текст, а вектор приоритетов над потребностями.

Хранится как смесь: {"Ruler": 0.7, "Caregiver": 0.3}.
Это даёт полутона, дрейф по ходу сюжета и обратный вывод ярлыка.
"""
from __future__ import annotations

# Базовые потребности-драйвы. Значение — вес в функции полезности.
# Отрицательный вес = отталкивание (Бунтарь активно не хочет порядка).
NEEDS = (
    "safety",     # безопасность, целостность
    "belonging",  # принадлежность, близость
    "status",     # признание, положение
    "control",    # власть над ситуацией
    "order",      # предсказуемость, правила
    "autonomy",   # свобода от чужой воли
    "novelty",    # новое, неизведанное
    "meaning",    # смысл, истина, понимание
    "altruism",   # польза другим
    "pleasure",   # удовольствие, красота
    "mastery",    # сделать хорошо, создать
)

WEIGHTS: dict[str, dict[str, float]] = {
    "Caregiver": {"altruism": 1.0, "belonging": 0.9, "safety": 0.5, "status": 0.1},
    "Ruler":     {"control": 1.0, "status": 0.9, "order": 0.8, "autonomy": 0.5},
    "Creator":   {"mastery": 1.0, "meaning": 0.6, "autonomy": 0.6, "novelty": 0.5},
    "Hero":      {"status": 0.8, "mastery": 0.8, "control": 0.6, "safety": -0.3},
    "Rebel":     {"autonomy": 1.0, "novelty": 0.6, "order": -0.7, "status": 0.3},
    "Magician":  {"meaning": 1.0, "control": 0.7, "novelty": 0.6, "mastery": 0.5},
    "Everyman":  {"belonging": 1.0, "safety": 0.6, "order": 0.4, "status": -0.2},
    "Lover":     {"pleasure": 1.0, "belonging": 0.9, "novelty": 0.3, "status": 0.3},
    "Jester":    {"pleasure": 0.9, "novelty": 0.8, "belonging": 0.5, "order": -0.4},
    "Innocent":  {"safety": 0.8, "order": 0.7, "belonging": 0.6, "novelty": -0.2},
    "Explorer":  {"novelty": 1.0, "autonomy": 0.9, "meaning": 0.5, "belonging": -0.2},
    "Sage":      {"meaning": 1.0, "mastery": 0.7, "autonomy": 0.5, "order": 0.4},
}

# Чего архетип боится — нужно эмпату, страх сильнее желания правит репликой.
FEARS: dict[str, str] = {
    "Caregiver": "оказаться ненужным; увидеть, что твоя забота никому не сдалась",
    "Ruler":     "потерять власть и смотреть, как всё скатывается в хаос",
    "Creator":   "оказаться посредственностью, повторяющей чужое",
    "Hero":      "показать слабость; не выдержать в решающий момент",
    "Rebel":     "стать бессильным и послушным, как все",
    "Magician":  "запустить то, что уже не сможешь остановить",
    "Everyman":  "быть отвергнутым, выделиться и остаться одному",
    "Lover":     "остаться одному и незамеченным",
    "Jester":    "скука; момент, когда от тебя перестают ждать шутки",
    "Innocent":  "сделать непоправимое и быть за это наказанным",
    "Explorer":  "застрять; осесть и пустить корни",
    "Sage":      "быть обманутым; принять ложь за истину",
}

RU: dict[str, str] = {
    "Caregiver": "Заботливый", "Ruler": "Правитель", "Creator": "Творец",
    "Hero": "Герой", "Rebel": "Бунтарь", "Magician": "Маг",
    "Everyman": "Свой", "Lover": "Любящий", "Jester": "Шут",
    "Innocent": "Простодушный", "Explorer": "Искатель", "Sage": "Мудрец",
}


def drives_from(mixture: dict[str, float]) -> dict[str, float]:
    """Смесь архетипов -> веса потребностей."""
    total = sum(mixture.values()) or 1.0
    acc = {n: 0.0 for n in NEEDS}
    for name, w in mixture.items():
        for need, val in WEIGHTS[name].items():
            acc[need] += val * (w / total)
    return acc


def dominant(mixture: dict[str, float]) -> str:
    return max(mixture, key=lambda k: mixture[k])


def fears_of(mixture: dict[str, float], threshold: float = 0.25) -> list[str]:
    return [FEARS[k] for k, w in sorted(mixture.items(), key=lambda kv: -kv[1])
            if w >= threshold]
