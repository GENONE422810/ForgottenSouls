"""Сцена: кто присутствует и что уже сказано.

История принадлежит сцене. Модель не хранит ничего между вызовами —
это и даёт изоляцию: в запрос попадают ровно те персонажи, которых
положили в эту сцену, и ничего сверх того.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from Person import Person


@dataclass(slots=True)
class MapPerson:
    """Персонаж, привязанный к месту и миру."""
    person: Person
    place: str = ""
    world: str = ""
    kind: str = "человек"        # 'бог' | 'человек' | 'другое'
    female: bool = False

    @property
    def name(self) -> str:
        return self.person.name


@dataclass(slots=True)
class Line:
    """Реплика в сцене."""
    speaker: str
    text: str
    is_player: bool = False


@dataclass(slots=True)
class Scene:
    scene_id: str = "default"
    place: str = ""
    situation: str = ""
    cast: list[MapPerson] = field(default_factory=list)
    log: list[Line] = field(default_factory=list)
    player_name: str = "Путник"

    # --- состав ---
    def add(self, m: MapPerson) -> "Scene":
        self.cast.append(m)
        return self

    def remove(self, name: str) -> None:
        self.cast = [m for m in self.cast if m.name != name]

    def clear_cast(self) -> None:
        self.cast.clear()

    def find(self, name: str) -> MapPerson | None:
        return next((m for m in self.cast if m.name == name), None)

    # --- реплики ---
    def say(self, speaker: str, text: str, is_player: bool = False) -> None:
        self.log.append(Line(speaker, text, is_player))

    def tail(self, n: int = 12) -> list[Line]:
        return self.log[-n:]

    # --- сохранение ---
    def to_dict(self) -> dict:
        return {
            "scene_id": self.scene_id,
            "place": self.place,
            "situation": self.situation,
            "player_name": self.player_name,
            "log": [{"speaker": l.speaker, "text": l.text, "is_player": l.is_player}
                    for l in self.log],
            "cast": [{"person": m.person.to_dict(), "place": m.place,
                      "world": m.world, "kind": m.kind, "female": m.female}
                     for m in self.cast],
        }

    @staticmethod
    def from_dict(d: dict) -> "Scene":
        s = Scene(
            scene_id=d.get("scene_id", "default"),
            place=d.get("place", ""),
            situation=d.get("situation", ""),
            player_name=d.get("player_name", "Путник"),
        )
        s.log = [Line(**l) for l in d.get("log", [])]
        s.cast = [MapPerson(person=Person.from_dict(c["person"]), place=c.get("place", ""),
                            world=c.get("world", ""), kind=c.get("kind", "человек"),
                            female=c.get("female", False))
                  for c in d.get("cast", [])]
        return s

    def save(self, directory: str = None) -> str:
        directory = directory or os.path.join(os.path.dirname(__file__), "memory")
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, f"scene_{self.scene_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent="\t")
        return path

    @staticmethod
    def load(scene_id: str, directory: str = None) -> "Scene":
        directory = directory or os.path.join(os.path.dirname(__file__), "memory")
        path = os.path.join(directory, f"scene_{scene_id}.json")
        with open(path, encoding="utf-8") as f:
            return Scene.from_dict(json.load(f))
