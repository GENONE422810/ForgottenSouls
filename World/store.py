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

# Где в записи лежат ссылки. Путь может уходить вглубь и ветвиться:
#   "world"                  — поле верхнего уровня
#   "soul.domains"           — поле внутри вложенного объекта
#   "instances.*.of"         — одноимённое поле у каждого элемента словаря
# Это единственное место, где знание о ссылках записано: обход, индекс
# и проверка целостности читают отсюда.
REF_FIELDS: dict[str, tuple[str, ...]] = {
    "meta":         ("player",),
    "plane":        (),
    "world":        ("plane",),
    "region":       ("world", "gouverment"),
    "gouverment":   ("world", "ruler", "heir"),
    "army":         ("gouverment",),
    "division":     ("army", "pos"),
    "ideology":     ("world", "god"),
    "person":       ("world", "region", "ideology", "family", "battle",
                     "soul.domains", "soul.skills", "soul.spells",
                     "soul.constellations",
                     "personality.state.episodes.*.who"),
    "mob":          ("world", "region", "battle"),
    "combatant":    ("skills",),
    "tile":         (),
    "domain":       (),
    "path":         ("domain", "branches"),
    "skill":        (),
    "spell":        ("owner", "domain"),
    "constellation": (),
    "event":        ("who", "refs", "where.plane", "where.world", "where.region"),
    "battle":       ("region", "instances.*.of", "instances.*.actor"),
}

# Пути до словарей, где ИД является ключом: ребро с данными.
REF_MAPS: dict[str, tuple[str, ...]] = {
    "region": ("population.faiths",),
    "person": ("personality.state.attitudes", "soul.progress"),
}


def _walk(node, parts: tuple[str, ...]):
    """Пройти по пути внутри записи. `*` разворачивает список или словарь."""
    if node is None:
        return
    if not parts:
        yield node
        return
    head, rest = parts[0], parts[1:]
    if head == "*":
        items = node.values() if isinstance(node, dict) else node
        if isinstance(items, (list, tuple, type({}.values()))):
            for it in items:
                yield from _walk(it, rest)
        return
    if isinstance(node, dict):
        yield from _walk(node.get(head), rest)
    elif isinstance(node, list):
        for it in node:
            yield from _walk(it, parts)


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
        kind = r.get("type", "")
        out: list[str] = []
        for path in REF_FIELDS.get(kind, ()):
            for v in _walk(r, tuple(path.split("."))):
                if isinstance(v, str):
                    out.append(v)
                elif isinstance(v, list):
                    out.extend(x for x in v if isinstance(x, str))
        for path in REF_MAPS.get(kind, ()):
            for v in _walk(r, tuple(path.split("."))):
                if isinstance(v, dict):
                    out.extend(k for k in v if isinstance(k, str))
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
