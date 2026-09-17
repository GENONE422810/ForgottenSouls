"""Динамическое состояние: настроение, нужды, силы, отношения, память.

Это то, чего не хватало исходной схеме. Без этого слоя NPC на 40-м часу
игры ведёт себя ровно как на первом.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import archetypes as arch
from .temperament import Temperament


@dataclass(slots=True)
class Mood:
    """PAD: удовольствие / возбуждение / доминирование. Всё -1..1."""
    pleasure: float = 0.0
    arousal: float = 0.0
    dominance: float = 0.0

    def nudge(self, dp: float, da: float, dd: float, gain: float) -> None:
        self.pleasure = _c(self.pleasure + dp * gain)
        self.arousal = _c(self.arousal + da * gain)
        self.dominance = _c(self.dominance + dd * gain)

    def decay_to(self, base: "Mood", rate: float) -> None:
        self.pleasure += (base.pleasure - self.pleasure) * rate
        self.arousal += (base.arousal - self.arousal) * rate
        self.dominance += (base.dominance - self.dominance) * rate


def _c(v: float) -> float:
    return max(-1.0, min(1.0, v))


@dataclass(slots=True)
class Episode:
    """Эпизод памяти с эмоциональной меткой."""
    what: str
    who: str | None
    valence: float      # -1..1, как он это пережил
    weight: float       # значимость, затухает со временем
    tick: int = 0


@dataclass(slots=True)
class MentalState:
    mood: Mood = field(default_factory=Mood)
    needs: dict[str, float] = field(default_factory=lambda: {n: 0.0 for n in arch.NEEDS})
    stamina: float = 1.0
    attitudes: dict[str, float] = field(default_factory=dict)   # entity_id -> -1..1
    episodes: list[Episode] = field(default_factory=list)

    # --- динамика ---
    def baseline(self, temp: Temperament, dominance_bias: float = 0.0) -> Mood:
        """Точка покоя, к которой темперамент тянет настроение."""
        return Mood(
            pleasure=temp.tone,
            arousal=(temp.energy - 0.5) * 0.6,
            dominance=dominance_bias,
        )

    def tick(self, temp: Temperament, dt: float = 1.0, dominance_bias: float = 0.0) -> None:
        """Возврат к базовой линии. Инерция = насколько медленно отпускает."""
        rate = min(1.0, (1.0 - temp.inertia) * dt)
        self.mood.decay_to(self.baseline(temp, dominance_bias), rate)
        self.stamina = min(1.0, self.stamina + 0.05 * temp.energy * dt)
        for k in self.needs:
            self.needs[k] = min(1.0, self.needs[k] + 0.01 * dt)
        for e in self.episodes:
            e.weight *= 0.995 ** dt
        self.episodes = [e for e in self.episodes if e.weight > 0.05]

    def apply(self, temp: Temperament, dp: float, da: float, dd: float,
              cost: float = 0.0) -> None:
        """Событие ударило по настроению. Сила удара = reactivity."""
        self.mood.nudge(dp, da, dd, gain=temp.reactivity)
        # холерик тратит силы залпом: чем выше reactivity, тем дороже вспышка
        self.stamina = max(0.0, self.stamina - cost * (0.5 + temp.reactivity))

    def remember(self, what: str, who: str | None, valence: float,
                 weight: float = 1.0, tick_no: int = 0) -> None:
        self.episodes.append(Episode(what, who, valence, weight, tick_no))

    def recent(self, n: int = 3, who: str | None = None) -> list[Episode]:
        pool = [e for e in self.episodes if who is None or e.who == who]
        return sorted(pool, key=lambda e: -(e.weight * abs(e.valence)))[:n]

    def attitude(self, who: str) -> float:
        return self.attitudes.get(who, 0.0)
