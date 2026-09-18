"""Темперамент как физика реакции, а не как ярлык.

Классические 4 типа — это не категории, а углы пространства.
Храним 4 коэффициента, ярлык выводим обратно для UI и промпта.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class Temperament:
    reactivity: float = 0.5   # амплитуда отклика на стимул
    inertia: float = 0.5      # насколько долго держится состояние (0 — отходит мгновенно)
    energy: float = 0.5       # запас сил, скорость истощения
    tone: float = 0.0         # базовый эмоциональный фон, -1..1

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


PRESETS: dict[str, Temperament] = {
    # вспыхивает ярко, отходит мгновенно, много сил, фон положительный
    "Sanguine":    Temperament(reactivity=0.60, inertia=0.20, energy=0.80, tone=+0.40),
    # вспыхивает сильно и держит, сил много но тратит залпом
    "Choleric":    Temperament(reactivity=0.90, inertia=0.70, energy=0.90, tone=-0.10),
    # раскачать трудно, остановить тоже трудно, ровный фон
    "Phlegmatic":  Temperament(reactivity=0.20, inertia=0.80, energy=0.55, tone=+0.00),
    # задевает всё, держится долго, сил мало
    "Melancholic": Temperament(reactivity=0.80, inertia=0.80, energy=0.30, tone=-0.40),
}

_FIELDS = ("reactivity", "inertia", "energy", "tone")


def mix(weights: dict[str, float]) -> Temperament:
    """Смешать пресеты: {"Choleric": 0.7, "Melancholic": 0.3}."""
    total = sum(weights.values()) or 1.0
    acc = {f: 0.0 for f in _FIELDS}
    for name, w in weights.items():
        base = PRESETS[name]
        for f in _FIELDS:
            acc[f] += getattr(base, f) * (w / total)
    return Temperament(**acc)


def label(t: Temperament) -> str:
    """Ближайший классический тип — только для отображения."""
    def dist(p: Temperament) -> float:
        return sum((getattr(t, f) - getattr(p, f)) ** 2 for f in _FIELDS)
    return min(PRESETS, key=lambda k: dist(PRESETS[k]))


RU = {
    "Sanguine": "сангвиник",
    "Choleric": "холерик",
    "Phlegmatic": "флегматик",
    "Melancholic": "меланхолик",
}
