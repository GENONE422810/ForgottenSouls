"""Эмпат — исполнитель личностей.

Принцип: каждый персонаж получает СВОЙ изолированный вызов.

Почему не один вызов на всю очередь, как было раньше:
  1. Модель, получив пять личностей разом, усредняет их — персонажи
     начинают звучать одинаково.
  2. Тайные желания и слепые пятна одного утекают в реплику другого:
     в одном контексте нет приватности.
  3. Стабильный префикс у каждого свой, и только при раздельных вызовах
     он кешируется. Один общий вызов пересобирает всё каждый ход.
  4. Строгий формат ответа и его парсинг перестают быть нужны.

Персонажи всё равно реагируют друг на друга: они говорят по очереди,
и каждый следующий видит в логе сцены реплики, сказанные до него
в этом же круге.

Изоляция состава: в запрос попадают только те, кто передан в этот вызов.
Ничего не накапливается между ходами — история живёт в Scene.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from AI.resolver import SYSTEM_PROMPT
from AI.scene import MapPerson, Scene
from Person import Interlocutor
from Person.prompt import outward_impression


class Completer(Protocol):
    """Всё, что нужно эмпату от модели. Клиент подставляется снаружи —
    это позволяет прогонять сцены на заглушке, не тратя запросы."""
    def complete(self, system: list[str], messages: list[dict]) -> str: ...


@dataclass(slots=True)
class Reply:
    name: str
    text: str


class Empath:
    def __init__(self, llm: "Completer") -> None:
        self.llm = llm

    # ------------------------------------------------------------------
    def play(
        self,
        scene: Scene,
        player_text: str | None = None,
        only: list[str] | None = None,
        intents: dict[str, str] | None = None,
        remember: bool = True,
    ) -> list[Reply]:
        """Прогнать круг реплик.

        only    — имена тех, кто отвечает в этом круге. None = весь состав
                  сцены. Кто не в списке — не обрабатывается и в промпт
                  других попадает только как присутствующий.
        intents — {имя: намерение от симуляции}. Кому намерение не задано,
                  тот говорит свободно.
        """
        if player_text:
            scene.say(scene.player_name, player_text, is_player=True)

        speakers = self._select(scene, only)
        intents = intents or {}
        out: list[Reply] = []

        for m in speakers:
            text = self._one(scene, m, intents.get(m.name))
            scene.say(m.name, text)
            out.append(Reply(m.name, text))
            if remember:
                self._write_memory(scene, m, player_text)
        return out

    # ------------------------------------------------------------------
    def _select(self, scene: Scene, only: list[str] | None) -> list[MapPerson]:
        if only is None:
            return list(scene.cast)
        wanted = set(only)
        chosen = [m for m in scene.cast if m.name in wanted]
        missing = wanted - {m.name for m in chosen}
        if missing:
            raise KeyError(f"нет в составе сцены: {sorted(missing)}")
        return chosen

    # ------------------------------------------------------------------
    def _one(self, scene: Scene, m: MapPerson, intent: str | None) -> str:
        p = m.person
        # Собеседник — игрок, если он говорил последним; иначе тот, кто говорил.
        last = scene.log[-1] if scene.log else None
        who = None
        if last and last.speaker != m.name:
            other = scene.find(last.speaker)
            who = Interlocutor(last.speaker, female=other.female if other else False)

        pr = p.system_prompt(who, scene=self._setting(scene, m))

        volatile = [pr.volatile]
        others = self._others_block(scene, m)
        if others:
            volatile.append(others)
        if intent:
            volatile.append(SYSTEM_PROMPT.intent_frame.format(intent=intent))

        system = [
            SYSTEM_PROMPT.empath_frame + "\n\n" + pr.stable,   # стабильный, кешируемый
            "\n\n".join(volatile),                             # летучий
        ]
        return self.llm.complete(system, self._messages(scene, m))

    # ------------------------------------------------------------------
    def _setting(self, scene: Scene, m: MapPerson) -> str:
        bits = [x for x in (m.place or scene.place, scene.situation) if x]
        return ", ".join(bits)

    def _others_block(self, scene: Scene, me: MapPerson) -> str:
        """Публичная сводка о присутствующих. Только то, что видно снаружи."""
        rows = []
        for o in scene.cast:
            if o.name is me.name or o.name == me.name:
                continue
            att = me.person.state.attitude(o.name)
            feel = _attitude_word(att)
            rows.append(f"- {o.name} ({o.kind}): {outward_impression(o.person)}. {feel}")
        if not rows:
            return ""
        return ("Кто ещё здесь (видишь только внешнее, мыслей их не знаешь):\n"
                + "\n".join(rows))

    def _messages(self, scene: Scene, me: MapPerson, depth: int = 12) -> list[dict]:
        """Лог сцены как диалог: свои реплики — assistant, чужие — user."""
        msgs: list[dict] = []
        for line in scene.tail(depth):
            if line.speaker == me.name:
                msgs.append({"role": "assistant", "content": line.text})
            else:
                msgs.append({"role": "user", "content": f"{line.speaker}: {line.text}"})
        if not msgs or msgs[-1]["role"] == "assistant":
            msgs.append({"role": "user", "content": "(пауза; твой ход)"})
        return msgs

    # ------------------------------------------------------------------
    def _write_memory(self, scene: Scene, m: MapPerson, player_text: str | None) -> None:
        """Эпизод пишется в память самого персонажа, не в общий лог модели."""
        if not player_text:
            return
        valence = m.person.state.mood.pleasure * 0.5
        m.person.state.remember(
            what=f"разговор: «{player_text[:60]}»",
            who=scene.player_name,
            valence=valence,
            weight=0.4 + abs(valence) * 0.6,
        )


def _attitude_word(a: float) -> str:
    if a <= -0.6:
        return "Ты его не выносишь."
    if a <= -0.2:
        return "Ты ему не доверяешь."
    if a < 0.2:
        return "Ты к нему равнодушен."
    if a < 0.6:
        return "Ты к нему расположен."
    return "Ты ему предан."
