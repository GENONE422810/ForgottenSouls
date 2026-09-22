"""Характер, желания, привычки, способности, Я-концепция.

Всё числовое, всё сериализуемое. Текст появляется только в prompt.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import archetypes as arch
from .temperament import Temperament

# --- ХАРАКТЕР ---------------------------------------------------------------
# Классическая разбивка: отношение к миру, к людям, к труду, к себе.
# Значения -1..+1. Имя черты — полюс "+".
CHARACTER_AXES: dict[str, tuple[str, str]] = {
    # ось: (полюс "+", полюс "-"). Формулировки — во втором лице,
    # они подставляются после "Ты ...".
    "trust":       ("доверчив к миру", "подозрителен ко всему"),
    "warmth":      ("тёплый с людьми", "холодный и дистантный"),
    "honesty":     ("прямой и честный", "скрытный, говоришь обиняками"),
    "diligence":   ("въедлив в работе", "делаешь лишь бы отвязаться"),
    "discipline":  ("держишь слово и порядок", "живёшь как придётся"),
    "courage":     ("идёшь на риск", "избегаешь опасности"),
    "pride":       ("самолюбив", "легко признаёшь себя неправым"),
    "deference":   ("уважаешь чины и старших", "плевал на любые чины"),
}


@dataclass(slots=True)
class Character:
    axes: dict[str, float] = field(default_factory=dict)

    def get(self, name: str) -> float:
        return self.axes.get(name, 0.0)

    @staticmethod
    def derive(temp: Temperament, mixture: dict[str, float]) -> "Character":
        """Базовый характер выводим из темперамента и архетипа.

        Это черновик для массовой генерации NPC — ключевых персонажей
        правишь руками поверх.
        """
        d = arch.drives_from(mixture)
        g = lambda k: d.get(k, 0.0)
        axes = {
            "trust":      _clamp(temp.tone + g("belonging") * 0.4 - g("control") * 0.3),
            "warmth":     _clamp(temp.tone * 0.5 + g("belonging") * 0.5 + g("altruism") * 0.5),
            "honesty":    _clamp(g("meaning") * 0.4 + g("autonomy") * 0.3 - g("status") * 0.3),
            "diligence":  _clamp(g("mastery") * 0.7 + temp.inertia * 0.4 - temp.reactivity * 0.2),
            "discipline": _clamp(g("order") * 0.6 + temp.inertia * 0.5 - temp.reactivity * 0.3),
            "courage":    _clamp(temp.energy * 0.6 - g("safety") * 0.5 + g("status") * 0.3),
            "pride":      _clamp(g("status") * 0.6 + g("control") * 0.4 - g("belonging") * 0.3),
            "deference":  _clamp(g("order") * 0.6 - g("autonomy") * 0.7),
        }
        return Character(axes=axes)


def _clamp(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


# --- ЖЕЛАНИЯ ----------------------------------------------------------------
@dataclass(slots=True)
class Desire:
    """Конкретная цель, привязанная к базовой потребности.

    need   — какую потребность закрывает (см. archetypes.NEEDS)
    weight — насколько важно, 0..1
    horizon— 'now' | 'short' | 'life'
    secret — не произносится вслух, но правит поведением
    """
    text: str
    need: str
    weight: float = 0.5
    horizon: str = "short"
    secret: bool = False
    target: str | None = None   # id сущности, если желание адресное


# --- ПРИВЫЧКИ ---------------------------------------------------------------
@dataclass(slots=True)
class Habit:
    """Автоматизм: стимул -> действие, мимо взвешивания полезности.

    Привычка тем и ценна, что иногда перебивает рациональный выбор —
    это и создаёт впечатление живого человека.
    """
    trigger: str        # "когда нервничает"
    action: str         # "крутит кольцо на пальце"
    strength: float = 0.5
    verbal: bool = False    # речевая привычка (словечко, присказка)


# --- СПОСОБНОСТИ ------------------------------------------------------------
@dataclass(slots=True)
class Abilities:
    """Навыки. Гейтят доступные действия и уверенность в реплике."""
    skills: dict[str, float] = field(default_factory=dict)   # 0..1

    def level(self, name: str) -> float:
        return self.skills.get(name, 0.0)

    def best(self, n: int = 3) -> list[tuple[str, float]]:
        return sorted(self.skills.items(), key=lambda kv: -kv[1])[:n]


# --- Я-КОНЦЕПЦИЯ ------------------------------------------------------------
@dataclass(slots=True)
class SelfConcept:
    """Кем он себя считает — и что в себе не признаёт.

    `denied` — самое ценное для отыгрыша: слепые пятна дают
    противоречия между словами и поступками.
    """
    self_esteem: float = 0.0            # -1..1
    identity: list[str] = field(default_factory=list)   # "я солдат, а не убийца"
    denied: list[str] = field(default_factory=list)     # "что он трус"
    role: str = ""                                      # роль в обществе
