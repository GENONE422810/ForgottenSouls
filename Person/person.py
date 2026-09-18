"""Person — контейнер личности и точка сборки.

Пайплайн: __init__ -> assemble() -> build_system_prompt()

В Person лежат ИНГРЕДИЕНТЫ. Готовый промпт здесь не хранится:
он протухает при любом изменении настроения, нужды или отношения.
Хранится кеш с флагом грязи — см. system_prompt().
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from . import archetypes as arch
from . import temperament as tmp
from .prompt import PersonaPrompt, render
from .state import MentalState
from .temperament import Temperament
from .traits import Abilities, Character, Desire, Habit, SelfConcept


@dataclass(slots=True)
class Interlocutor:
    """Кто перед персонажем. Нужен минимум — имя и род, для согласования."""
    name: str
    female: bool = False

    @staticmethod
    def of(x) -> "Interlocutor | None":
        if x is None:
            return None
        return x if isinstance(x, Interlocutor) else Interlocutor(str(x))


@dataclass(slots=True)
class SpeechStyle:
    """Как звучит речь. Выводится, не задаётся руками."""
    tempo: float = 0.5        # 0 — тянет паузы, 1 — тараторит
    verbosity: float = 0.5    # 0 — цедит по слову, 1 — растекается
    directness: float = 0.5   # 0 — намёками, 1 — в лоб
    warmth: float = 0.5       # 0 — ледяной, 1 — участливый
    formality: float = 0.5    # 0 — площадная речь, 1 — церемонный
    profanity: float = 0.0    # склонность к грубости


@dataclass(slots=True)
class PersonaSnapshot:
    """Плоский срез всех подсистем на конкретный тик.

    Именно это отдаётся в билдер промпта и в утилитарный ИИ.
    Ничего не вычисляет — только собранные данные.
    """
    name: str
    age: int
    role: str
    background: str
    temperament: Temperament
    temperament_label: str
    archetype_mix: dict[str, float]
    archetype_dominant: str
    drives: dict[str, float]
    fears: list[str]
    character: dict[str, float]
    desires: list[Desire]
    habits: list[Habit]
    abilities: Abilities
    self_concept: SelfConcept
    speech: SpeechStyle
    state: MentalState
    urgency: dict[str, float]          # need -> weight * дефицит, отсортировано
    interlocutor: str | None = None
    interlocutor_female: bool = False
    attitude: float = 0.0
    shared_memory: list = field(default_factory=list)


class Person:
    def __init__(
        self,
        name: str = "Безымянный",
        age: int = 30,
        role: str = "",
        background: str = "",
        archetype: dict[str, float] | str | None = None,
        temperament: dict[str, float] | str | Temperament | None = None,
        character: Character | None = None,
        desires: list[Desire] | None = None,
        habits: list[Habit] | None = None,
        abilities: Abilities | None = None,
        self_concept: SelfConcept | None = None,
    ) -> None:
        self.name = name
        self.age = age
        self.role = role
        self.background = background

        # --- архетип: строка -> чистая смесь ---
        if archetype is None:
            archetype = {"Everyman": 1.0}
        elif isinstance(archetype, str):
            archetype = {archetype: 1.0}
        unknown = set(archetype) - set(arch.WEIGHTS)
        if unknown:
            raise ValueError(f"неизвестный архетип: {sorted(unknown)}")
        self.archetype_mix: dict[str, float] = dict(archetype)

        # --- темперамент ---
        if temperament is None:
            temperament = {"Phlegmatic": 1.0}
        if isinstance(temperament, str):
            temperament = {temperament: 1.0}
        if isinstance(temperament, dict):
            unknown = set(temperament) - set(tmp.PRESETS)
            if unknown:
                raise ValueError(f"неизвестный темперамент: {sorted(unknown)}")
            temperament = tmp.mix(temperament)
        self.temperament: Temperament = temperament

        # --- остальное: либо задано, либо выведено ---
        self.character = character or Character.derive(self.temperament, self.archetype_mix)
        self.desires: list[Desire] = desires or []
        self.habits: list[Habit] = habits or []
        self.abilities = abilities or Abilities()
        self.self_concept = self_concept or SelfConcept(role=role)

        self.state = MentalState()
        self.drives = arch.drives_from(self.archetype_mix)

        self._cache: dict[tuple, PersonaPrompt] = {}
        self._dirty = True

    # ------------------------------------------------------------------
    # ШАГ 2: сборка данных из подсистем
    # ------------------------------------------------------------------
    def assemble(self, interlocutor=None) -> PersonaSnapshot:
        who = Interlocutor.of(interlocutor)
        ch = self.character
        t = self.temperament

        speech = SpeechStyle(
            tempo=_c01(0.5 + (t.energy - 0.5) * 0.8 + (t.reactivity - 0.5) * 0.4
                       - (t.inertia - 0.5) * 0.4),
            verbosity=_c01(0.5 + ch.get("warmth") * 0.3 + (t.energy - 0.5) * 0.5
                           + self.drives.get("belonging", 0) * 0.2),
            directness=_c01(0.5 + ch.get("honesty") * 0.4 + ch.get("pride") * 0.2
                            + self.drives.get("control", 0) * 0.3),
            warmth=_c01(0.5 + ch.get("warmth") * 0.5 + t.tone * 0.3),
            formality=_c01(0.5 + ch.get("deference") * 0.4
                           + self.drives.get("order", 0) * 0.3
                           - self.drives.get("autonomy", 0) * 0.3),
            profanity=_c01(0.2 - ch.get("deference") * 0.4 + t.reactivity * 0.3
                           + self.drives.get("autonomy", 0) * 0.2),
        )

        # какие потребности горят прямо сейчас: важность * дефицит
        urgency = {
            n: self.drives.get(n, 0.0) * self.state.needs.get(n, 0.0)
            for n in arch.NEEDS
        }
        urgency = dict(sorted(urgency.items(), key=lambda kv: -kv[1]))

        return PersonaSnapshot(
            name=self.name,
            age=self.age,
            role=self.role or self.self_concept.role,
            background=self.background,
            temperament=t,
            temperament_label=tmp.RU[tmp.label(t)],
            archetype_mix=self.archetype_mix,
            archetype_dominant=arch.RU[arch.dominant(self.archetype_mix)],
            drives=self.drives,
            fears=arch.fears_of(self.archetype_mix),
            character=dict(ch.axes),
            desires=list(self.desires),
            habits=list(self.habits),
            abilities=self.abilities,
            self_concept=self.self_concept,
            speech=speech,
            state=self.state,
            urgency=urgency,
            interlocutor=who.name if who else None,
            interlocutor_female=who.female if who else False,
            attitude=self.state.attitude(who.name) if who else 0.0,
            shared_memory=self.state.recent(3, who=who.name) if who else [],
        )

    # ------------------------------------------------------------------
    # ШАГ 3: системный промпт
    # ------------------------------------------------------------------
    def system_prompt(self, interlocutor=None, scene: str = "",
                      private: bool = True) -> PersonaPrompt:
        """Промпт для обработчика-эмпата.

        Возвращает две части: stable (кешируется провайдером, одинакова
        всегда) и volatile (состояние на этот тик, меняется каждый раз).
        """
        who = Interlocutor.of(interlocutor)
        key = (who.name if who else None, private)
        if self._dirty or key not in self._cache:
            self._cache[key] = render(self.assemble(who), scene, private)
            self._dirty = False
        else:
            # личность та же — пересобираем только летучую часть
            self._cache[key] = PersonaPrompt(
                stable=self._cache[key].stable,
                volatile=render(self.assemble(who), scene, private).volatile,
            )
        return self._cache[key]

    def touch(self) -> None:
        """Пометить личность изменившейся (выучил навык, сменил цель)."""
        self._dirty = True
        self.drives = arch.drives_from(self.archetype_mix)

    # ------------------------------------------------------------------
    # утилитарный выбор: решение принимает симуляция, не LLM
    # ------------------------------------------------------------------
    def score(self, satisfies: dict[str, float], requires: dict[str, float] | None = None,
              risk: float = 0.0) -> float:
        """Оценка действия. LLM потом только ОЗВУЧИВАЕТ выбранное намерение."""
        if requires:
            for skill, lvl in requires.items():
                if self.abilities.level(skill) < lvl:
                    return float("-inf")
        util = sum(self.drives.get(n, 0.0) * self.state.needs.get(n, 0.0) * v
                   for n, v in satisfies.items())
        # настроение смещает оценку: злой и уверенный лезет на рожон
        boldness = self.character.get("courage") + self.state.mood.dominance * 0.5
        util -= risk * (1.5 - boldness)
        util *= 0.5 + self.state.stamina * 0.5
        return util

    # ------------------------------------------------------------------
    # сохранение / загрузка
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        """Полный слепок: и личность, и память. Кладётся в сейв как есть."""
        return {
            "name": self.name, "age": self.age, "role": self.role,
            "background": self.background,
            "archetype_mix": dict(self.archetype_mix),
            "temperament": self.temperament.as_dict(),
            "character": dict(self.character.axes),
            "desires": [asdict(d) for d in self.desires],
            "habits": [asdict(h) for h in self.habits],
            "abilities": dict(self.abilities.skills),
            "self_concept": asdict(self.self_concept),
            "state": self.state.to_dict(),
        }

    @staticmethod
    def from_dict(d: dict) -> "Person":
        p = Person(
            name=d["name"], age=d.get("age", 30), role=d.get("role", ""),
            background=d.get("background", ""),
            archetype=d.get("archetype_mix"),
            temperament=Temperament(**d["temperament"]),
            character=Character(axes=dict(d.get("character", {}))),
            desires=[Desire(**x) for x in d.get("desires", [])],
            habits=[Habit(**x) for x in d.get("habits", [])],
            abilities=Abilities(skills=dict(d.get("abilities", {}))),
            self_concept=SelfConcept(**d["self_concept"]) if "self_concept" in d else None,
        )
        p.state = MentalState.from_dict(d.get("state", {}))
        return p

    def __repr__(self) -> str:
        return (f"<Person {self.name}: {tmp.RU[tmp.label(self.temperament)]}/"
                f"{arch.RU[arch.dominant(self.archetype_mix)]}>")


def _c01(v: float) -> float:
    return max(0.0, min(1.0, v))
