"""Эмпат — исполнитель личностей.

Два режима, переключаются размером пакета.

batch_size=1 — отдельный вызов на персонажа. Максимальная верность:
    свой кешируемый префикс, полная приватность, ответ не надо парсить.
    Дорого при большом составе: N персонажей = N запросов.

batch_size>1 — несколько персонажей за один вызов, ответ размечен
    маркерами и разбирается парсером. Дёшево, но у режима две платы:
      * личности в одном контексте тянет к общему среднему, поэтому
        рамка промпта прямо требует контраста;
      * приватности в общем контексте нет — этим занимается политика
        `privacy` (см. ниже).
    Если модель пропустила кого-то в ответе, пропущенный переспрашивается
    отдельным вызовом, так что реплику получают все запрошенные.

Политика приватности в пакете:
    "redact"  — по умолчанию. Содержание тайных желаний и непризнаваемых
                черт заменяется поведенческой инструкцией: персонаж всё так
                же уходит от темы, но текст тайны в общий контекст не попадает.
    "isolate" — персонажи, у которых есть тайны, выносятся в собственные
                вызовы, остальные идут пакетом. Верность выше, запросов больше.
    "off"     — всё как есть, дешевле всего, тайны видны соседям по пакету.

Изоляция состава: обрабатываются только переданные персонажи. Между ходами
ничего не накапливается — история живёт в Scene, а не в клиенте.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

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
        batch_size: int = 1,
        privacy: str = "redact",
        remember: bool = True,
    ) -> list[Reply]:
        """Прогнать круг реплик.

        only       — имена тех, кто отвечает в этом круге. None = весь состав.
                     Кто не в списке, в промпт остальных попадает только как
                     присутствующий, и реплику не подаёт.
        intents    — {имя: намерение от симуляции}. Без намерения персонаж
                     говорит свободно.
        batch_size — сколько персонажей в одном вызове. 1 = по одному.
        privacy    — "redact" | "isolate" | "off", см. модуль.
        """
        if privacy not in ("redact", "isolate", "off"):
            raise ValueError(f"privacy: ожидалось redact|isolate|off, дано {privacy!r}")
        if player_text:
            scene.say(scene.player_name, player_text, is_player=True)

        speakers = self._select(scene, only)
        intents = intents or {}
        out: list[Reply] = []

        for group in self._group(speakers, batch_size, privacy):
            if len(group) == 1:
                m = group[0]
                said = {m.name: self._one(scene, m, intents.get(m.name))}
            else:
                said = self._many(scene, group, intents, privacy)
            # порядок фиксируем составом группы, а не порядком ответа модели
            for m in group:
                scene.say(m.name, said[m.name])
                out.append(Reply(m.name, said[m.name]))
                if remember:
                    self._write_memory(scene, m, player_text)
        return out

    # ------------------------------------------------------------------
    def _group(self, speakers: list[MapPerson], batch_size: int,
               privacy: str) -> list[list[MapPerson]]:
        """Разбить говорящих на вызовы."""
        if batch_size <= 1:
            return [[m] for m in speakers]

        solo: list[MapPerson] = []
        pack: list[MapPerson] = []
        for m in speakers:
            if privacy == "isolate" and _has_secrets(m.person):
                solo.append(m)
            else:
                pack.append(m)

        groups = [[m] for m in solo]
        groups += [pack[i:i + batch_size] for i in range(0, len(pack), batch_size)]
        # одиночка в пакетном режиме дешевле и точнее как обычный сольный вызов
        return [g for g in groups if g]

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
    def _many(self, scene: Scene, group: list[MapPerson],
              intents: dict[str, str], privacy: str) -> dict[str, str]:
        """Один вызов на группу. Возвращает {имя: реплика} для всей группы."""
        private = privacy == "off"
        marks = "\n".join(MARK.format(name=m.name) for m in group)

        personas: list[str] = []
        volatiles: list[str] = []
        for i, m in enumerate(group, 1):
            pr = m.person.system_prompt(None, scene=self._setting(scene, m),
                                        private=private)
            head = SYSTEM_PROMPT.batch_speaker_header.format(i=i, name=m.name)
            personas.append(f"{head}\n{pr.stable}")

            v = [f"{head}\n{pr.volatile}"]
            others = self._others_block(scene, m)
            if others:
                v.append(others)
            if intents.get(m.name):
                v.append(SYSTEM_PROMPT.intent_frame.format(intent=intents[m.name]))
            volatiles.append("\n\n".join(v))

        system = [
            # стабильный префикс: рамка + личности. При неизменном составе
            # повторяется дословно между ходами, поэтому кешируется.
            SYSTEM_PROMPT.batch_frame.format(marks=marks) + "\n\n"
            + "\n\n".join(personas),
            "## СОСТОЯНИЕ НА ЭТОТ ХОД\n\n" + "\n\n".join(volatiles),
        ]
        raw = self.llm.complete(system, [self._transcript(scene)])
        said = parse_marked(raw, [m.name for m in group])

        # Кого модель потеряла или выдала пустым — переспрашиваем отдельно.
        for m in group:
            if not said.get(m.name):
                said[m.name] = self._one(scene, m, intents.get(m.name))
        return said

    def _transcript(self, scene: Scene, depth: int = 12) -> dict:
        """Лог сцены одним сообщением: в пакете нет «своих» и «чужих» реплик."""
        lines = [f"{l.speaker}: {l.text}" for l in scene.tail(depth)]
        body = "\n".join(lines) if lines else "(сцена только началась)"
        return {"role": "user", "content": "Что уже сказано:\n" + body
                + "\n\nТеперь ответьте, каждый за себя."}

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


MARK = "<<<{name}>>>"
_MARK_RE = re.compile(r"<<<\s*(.+?)\s*>>>")


def parse_marked(raw: str, names: list[str]) -> dict[str, str]:
    """Разобрать размеченный ответ в {имя: реплика}.

    Маркеры, а не JSON: реплики — свободный текст с кавычками, переносами
    и скобками, на котором JSON рвётся постоянно. Здесь ломаться нечему.
    Неизвестные и повторные имена отбрасываются, регистр и пробелы прощаются.
    """
    by_lower = {n.lower(): n for n in names}
    out: dict[str, str] = {}
    parts = _MARK_RE.split(raw)
    # parts: [мусор до первого маркера, имя1, текст1, имя2, текст2, ...]
    for i in range(1, len(parts) - 1, 2):
        real = by_lower.get(parts[i].strip().lower())
        if real and real not in out:
            out[real] = parts[i + 1].strip()
    return out


def _has_secrets(person) -> bool:
    return any(d.secret for d in person.desires) or bool(person.self_concept.denied)
