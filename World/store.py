"""Хранилище мира: записи-словари, ссылки-строки, индекс связей.

Почему словари, а не классы с типизированным конструктором:

    Region(government=Government(...))   # чтобы создать регион, нужен объект
                                         # государства, а тому нужны регионы

Это задача о порядке построения графа с циклами, и на ней ломаются
загрузка и сейвы. Здесь запись — обычный dict, ссылка — строка id.
Порядка загрузки не существует, циклы безвредны, а json.load возвращает
готовое хранилище.

Поведение живёт в функциях над хранилищем, а не внутри записей.
"""
from __future__ import annotations

import json

# Какие поля каждого типа являются ссылками. Единственное место, где это
# знание записано: и обход, и валидация, и индекс читают отсюда.
REF_FIELDS: dict[str, tuple[str, ...]] = {
    "plane":     (),
    "world":     ("plane", "territoryis"),
    "territoryis": ("world",),
    "region":    ("territoryis", "gouverment"),
    "gouverment": ("world", "глава", "наследник", "army"),
    "ideology":  ("world", "god"),
    "army":      (),
    "division":  ("army", "pos"),
    "person":    ("current_world", "ideology", "battle"),
    "mob":       ("battle",),
    "combatant": (),
    "tile":      (),
    "domain":    (),
    "skill":     (),
    "event":     ("who", "refs", "where"),
}

# Поля-словари, где ключ — это id (ребро с данными: доля, вес, отношение).
REF_MAPS: dict[str, tuple[str, ...]] = {
    "region": ("faiths",),
    "person": ("attitudes",),
}


class Store:
    def __init__(self, records: dict[str, dict] | None = None) -> None:
        self.rec: dict[str, dict] = records or {}
        self.back: dict[str, set[str]] = {}
        self.reindex()

    # --- ссылки ---
    def refs_of(self, rid: str) -> list[str]:
        """Все id, на которые ссылается запись. Порядок стабильный."""
        r = self.rec.get(rid)
        if not r:
            return []
        out: list[str] = []
        for f in REF_FIELDS.get(r.get("type", ""), ()):
            v = r.get(f)
            if isinstance(v, str):
                out.append(v)
            elif isinstance(v, list):
                out.extend(x for x in v if isinstance(x, str))
        for f in REF_MAPS.get(r.get("type", ""), ()):
            v = r.get(f)
            if isinstance(v, dict):
                out.extend(v.keys())
        return out

    def reindex(self) -> None:
        """Обратный индекс: {id: кто на него ссылается}. Один проход."""
        self.back = {}
        for rid in self.rec:
            for target in self.refs_of(rid):
                self.back.setdefault(target, set()).add(rid)

    def linked_to(self, rid: str) -> list[str]:
        return sorted(self.back.get(rid, ()))

    # --- обход ---
    def gather(self, start: str, depth: int = 2) -> dict[str, int]:
        """Контекст вокруг записи. {id: на каком кольце найден}."""
        seen = {start: 0}
        frontier = [start]
        for k in range(1, depth + 1):
            nxt = []
            for rid in frontier:
                for nid in self.refs_of(rid) + self.linked_to(rid):
                    if nid not in seen and nid in self.rec:
                        seen[nid] = k
                        nxt.append(nid)
            frontier = nxt
        return seen

    def by_type(self, kind: str) -> list[str]:
        return [i for i, r in self.rec.items() if r.get("type") == kind]

    # --- целостность ---
    def dangling(self) -> list[tuple[str, str]]:
        """Ссылки в никуда. Гонять после каждой загрузки."""
        return [(rid, t) for rid in self.rec
                for t in self.refs_of(rid) if t not in self.rec]

    # --- диск ---
    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.rec, f, ensure_ascii=False, indent="\t")

    @staticmethod
    def load(path: str) -> "Store":
        with open(path, encoding="utf-8") as f:
            return Store(json.load(f))
