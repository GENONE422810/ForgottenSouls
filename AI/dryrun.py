"""Прогон без обращения к модели.

Подставляет заглушку вместо LLM и печатает, что именно ушло бы каждому
персонажу. Нужен, чтобы проверять изоляцию состава и размер промпта,
не тратя запросы.
"""
from __future__ import annotations

from AI.Roles.empath import Empath, _MARK_RE
from AI.scene import MapPerson, Scene
from Person import Abilities, Desire, Habit, Person, SelfConcept
from Person.demo import make_guard


class StubLLM:
    """Ничего не шлёт. Складывает запросы и отдаёт болванку.

    drop — имена, которые заглушка нарочно «забывает» в пакетном ответе.
    Так проверяется, что потерянный персонаж дозапрашивается отдельно.
    """
    def __init__(self, drop: set[str] | None = None) -> None:
        self.calls: list[dict] = []
        self.drop = drop or set()

    def complete(self, system, messages, **kw) -> str:
        self.calls.append({"system": system, "messages": messages})
        names = _MARK_RE.findall(system[0])
        if not names:                      # сольный вызов
            return "(реплика заглушки)"
        out = []
        for n in names:
            if n in self.drop:
                continue
            out.append(f"<<<{n}>>>\n(реплика {n})")
        return "\n".join(out)


def make_thief() -> Person:
    return Person(
        name="Аэн",
        age=23,
        role="контрабандистка",
        background="Выросла в порту, водит людей мимо постов за долю.",
        archetype={"Rebel": 0.6, "Explorer": 0.4},
        temperament={"Sanguine": 0.7, "Choleric": 0.3},
        desires=[
            Desire("Уйти из города до рассвета", need="autonomy", weight=0.9, horizon="now"),
            Desire("Выкупить брата из долговой ямы", need="belonging",
                   weight=0.85, horizon="life", secret=True),
        ],
        habits=[Habit("врёт", "смотрит слишком прямо в глаза", 0.7)],
        abilities=Abilities({"воровство": 0.8, "болтовня": 0.7, "меч": 0.2}),
        self_concept=SelfConcept(self_esteem=0.3,
                                 identity=["Ты не воровка, ты проводница"],
                                 denied=["что брат о тебе и не вспомнит"]),
    )


def main() -> None:
    stub = StubLLM()
    empath = Empath(stub)

    scene = Scene(scene_id="dry", place="караулка", situation="ночь, дождь")
    guard, thief = make_guard(), make_thief()
    guard.state.attitudes["Аэн"] = -0.5
    guard.state.needs["order"] = 0.8
    guard.state.apply(guard.temperament, dp=-0.6, da=+0.7, dd=-0.4, cost=0.5)
    thief.state.attitudes["Ведор Крайн"] = -0.2

    scene.add(MapPerson(guard, kind="человек"))
    scene.add(MapPerson(thief, kind="человек", female=True))

    print("=" * 68)
    print("КРУГ 1 — отвечает только стража (only=[...])")
    print("=" * 68)
    empath.play(scene, player_text="Пропусти нас, начальник.",
                only=["Ведор Крайн"],
                intents={"Ведор Крайн": "отказать и потребовать подорожную"})
    _report(stub, scene)

    print()
    print("=" * 68)
    print("КРУГ 2 — отвечают оба, по очереди")
    print("=" * 68)
    stub.calls.clear()
    empath.play(scene, player_text="У нас нет бумаг.")
    _report(stub, scene)

    print()
    print("=" * 68)
    print("ПРОВЕРКИ ИЗОЛЯЦИИ")
    print("=" * 68)
    guard_call = stub.calls[0]
    thief_call = stub.calls[1]
    guard_text = "\n".join(guard_call["system"])
    thief_text = "\n".join(thief_call["system"])

    checks = [
        ("тайна воровки не попала в промпт стражи",
         "Выкупить брата" not in guard_text),
        ("слепое пятно воровки не попало в промпт стражи",
         "брат о тебе и не вспомнит" not in guard_text),
        ("тайна стражи не попала в промпт воровки",
         "сделал всё, что мог" not in thief_text),
        ("стража видит воровку только снаружи",
         "Аэн" in guard_text and "контрабандистка" not in guard_text),
        ("стабильный блок у каждого свой",
         guard_call["system"][0] != thief_call["system"][0]),
        ("состав не протёк из прошлого круга",
         guard_text.count("Ты отыгрываешь персонажа") == 1),
    ]
    for label, ok in checks:
        print(f"  [{'OK' if ok else 'ПРОВАЛ'}] {label}")

    print()
    print("Размер промпта (символов):")
    for c in stub.calls:
        name = c["system"][0].split("по имени ")[1].split(",")[0]
        print(f"  {name:16} stable={len(c['system'][0]):5}  "
              f"volatile={len(c['system'][1]):5}  реплик={len(c['messages'])}")
    crowd_check()


def crowd_check() -> None:
    """Пакетный режим на составе из 10 персонажей."""
    from Person import Temperament

    print()
    print("=" * 68)
    print("ПАКЕТНЫЙ РЕЖИМ: 10 персонажей")
    print("=" * 68)

    scene = Scene(scene_id="crowd", place="рыночная площадь", situation="полдень")
    scene.add(MapPerson(make_guard()))
    scene.add(MapPerson(make_thief(), female=True))
    arche = ["Everyman", "Jester", "Sage", "Innocent", "Lover",
             "Hero", "Explorer", "Creator"]
    temps = ["Sanguine", "Phlegmatic", "Melancholic", "Choleric"]
    for i, a in enumerate(arche):
        scene.add(MapPerson(Person(name=f"Горожанин-{i+1}", age=20 + i * 3,
                                   role="торговец",
                                   archetype=a, temperament=temps[i % 4])))
    names = [m.name for m in scene.cast]

    for size in (1, 4, 10):
        stub = StubLLM()
        Empath(stub).play(Scene.from_dict(scene.to_dict()),
                          player_text="Кто здесь главный?", batch_size=size)
        chars = sum(len(c["system"][0]) + len(c["system"][1]) for c in stub.calls)
        print(f"  batch_size={size:<3} вызовов={len(stub.calls):<3} "
              f"символов в промптах={chars}")

    # --- порядок и полнота ---
    stub = StubLLM()
    sc = Scene.from_dict(scene.to_dict())
    replies = Empath(stub).play(sc, player_text="Кто здесь главный?", batch_size=4)
    print(f"\n  реплик получено: {len(replies)} из {len(names)}")
    print(f"  порядок сохранён: {[r.name for r in replies] == names}")

    # --- потеря персонажа моделью ---
    stub = StubLLM(drop={"Горожанин-3", "Аэн"})
    sc = Scene.from_dict(scene.to_dict())
    replies = Empath(stub).play(sc, player_text="Кто здесь главный?", batch_size=4)
    got = {r.name for r in replies}
    solo = sum(1 for c in stub.calls if not _MARK_RE.findall(c["system"][0]))
    print(f"\n  модель потеряла двоих -> дозапросов: {solo}")
    print(f"  все всё равно ответили: {got == set(names)}")

    # --- приватность в пакете ---
    print()
    for policy in ("redact", "isolate", "off"):
        stub = StubLLM()
        sc = Scene.from_dict(scene.to_dict())
        Empath(stub).play(sc, player_text="?", batch_size=4, privacy=policy)
        blob = "\n".join(c["system"][0] for c in stub.calls
                          if _MARK_RE.findall(c["system"][0]))
        leak = "Выкупить брата" in blob or "струсил" in blob
        print(f"  privacy={policy:<8} вызовов={len(stub.calls):<3} "
              f"тайны в общем контексте: {'ДА' if leak else 'нет'}")


def _report(stub: StubLLM, scene: Scene) -> None:
    print(f"вызовов к модели: {len(stub.calls)}")
    for c in stub.calls:
        name = c["system"][0].split("по имени ")[1].split(",")[0]
        print(f"  -> {name}")
    print("лог сцены:")
    for line in scene.log:
        print(f"  {line.speaker}: {line.text}")


if __name__ == "__main__":
    main()
