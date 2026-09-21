"""Обёртки над записями хранилища.

Обёртка НЕ владеет данными. Она держит только хранилище и строку id,
а поля читает из записи в момент обращения:

    region = Region(store, "reg.7")     # нужна только строка
    region.name                         # -> store.rec["reg.7"]["name"]
    region.gouverment.name              # ссылка разрешается здесь и сейчас

Сравни с конструктором, который владеет данными:

    Region(id, name, biome, population, territory, government)
                                                   ^^^^^^^^^^
    чтобы создать регион, нужен готовый объект государства,
    а тому нужны его регионы — и загрузка превращается в задачу
    о порядке построения графа с циклами

Здесь этой задачи нет: ссылка остаётся строкой, пока к ней не обратятся.
`to_dict` тоже не нужен — словарь в хранилище УЖЕ является хранимой формой.

Обёртки необязательны. `store.rec["reg.7"]["name"]` работает и без них.
Обёртку стоит заводить, только когда у сущности появляется поведение —
метод, который что-то считает или меняет. Пока поведения нет, хватит словаря.
"""
from __future__ import annotations


class Node:
    """Общая часть: доступ к своей записи и разрешение ссылок."""

    def __init__(self, store, rid: str) -> None:
        self.store = store
        self.id = rid

    @property
    def rec(self) -> dict:
        """Живая запись. Не копия: изменения видны сразу."""
        return self.store.rec[self.id]

    @property
    def name(self) -> str:
        return self.rec.get("name", self.id)

    def ref(self, field: str, cls=None):
        """Разрешить ссылку из поля. None, если поля нет."""
        rid = self.rec.get(field)
        if not rid:
            return None
        return (cls or Node)(self.store, rid)

    def incoming(self, kind: str, cls=None) -> list:
        """Кто ссылается на меня и имеет нужный тип. Работает на индексе."""
        return [(cls or Node)(self.store, i)
                for i in self.store.linked_to(self.id)
                if self.store.rec[i].get("type") == kind]

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.id} {self.name!r}>"


class Region(Node):
    @property
    def biome(self) -> str:
        return self.rec.get("biome", "")

    @property
    def population(self) -> int:
        return self.rec.get("population", 0)

    @property
    def gouverment(self):
        return self.ref("gouverment", Gouverment)

    @property
    def divisions(self) -> list:
        """Войска, стоящие здесь. Ссылку хранят дивизии, не регион."""
        return self.incoming("division", Division)

    @property
    def events(self) -> list:
        return self.incoming("event", Node)

    def faith(self, ideology_id: str) -> float:
        return self.rec.get("faiths", {}).get(ideology_id, 0.0)

    def dominant_faith(self):
        f = self.rec.get("faiths", {})
        if not f:
            return None
        return Node(self.store, max(f, key=f.get))

    # --- поведение: ради него обёртка и существует ---
    def tick(self, dt: float = 1.0) -> None:
        """Шаг симуляции. Пишет прямо в запись хранилища."""
        food = self.rec.get("resources", {}).get("food", 0)
        capacity = 1000 + food * 10
        growth = 0.01 * dt * (1 - self.population / max(capacity, 1))
        self.rec["population"] = max(0, round(self.population * (1 + growth)))


class Gouverment(Node):
    @property
    def ruler(self):
        return self.ref("глава", Person)

    @property
    def army(self):
        return self.ref("army", Node)

    @property
    def regions(self) -> list:
        """Списка регионов в записи НЕТ — он берётся из обратного индекса."""
        return self.incoming("region", Region)

    @property
    def manpower(self) -> int:
        army = self.army
        if not army:
            return 0
        return sum(d.rec.get("manpower", 0) for d in army.incoming("division", Division))


class Division(Node):
    @property
    def pos(self):
        return self.ref("pos", Region)


class Person(Node):
    @property
    def ideology(self):
        return self.ref("ideology", Node)

    @property
    def world(self):
        return self.ref("current_world", Node)

    @property
    def rules(self):
        """Государства, где этот человек — глава. Тоже через индекс."""
        return [g for g in self.incoming("gouverment", Gouverment)
                if g.rec.get("глава") == self.id]
