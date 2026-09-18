"""Демонстрация пайплайна: инициализация -> сборка -> системный промпт."""
from __future__ import annotations

from . import Abilities, Desire, Habit, Interlocutor, Person, SelfConcept


def make_guard() -> Person:
    return Person(
        name="Ведор Крайн",
        age=44,
        role="десятник городской стражи",
        background=(
            "Двадцать лет в страже. Пережил осаду, в которой погиб его отряд, "
            "и с тех пор командует теми, кого не хочет знать по именам."
        ),
        archetype={"Ruler": 0.6, "Caregiver": 0.4},
        temperament={"Choleric": 0.7, "Melancholic": 0.3},
        desires=[
            Desire("Чтобы в квартале был порядок и никто больше не погиб на твоём посту",
                   need="order", weight=0.9, horizon="life"),
            Desire("Дослужиться до капитана, пока не списали по возрасту",
                   need="status", weight=0.6, horizon="short"),
            Desire("Чтобы кто-нибудь наконец сказал, что тогда ты сделал всё, что мог",
                   need="belonging", weight=0.8, horizon="life", secret=True),
        ],
        habits=[
            Habit("нервничает", "трёт большим пальцем зазубрину на рукояти меча", 0.7),
            Habit("не хочет отвечать", "смотрит поверх плеча собеседника", 0.5),
            Habit("раздражён", "называет собеседника «парень», кем бы тот ни был",
                  0.6, verbal=True),
        ],
        abilities=Abilities({"меч": 0.8, "дознание": 0.6, "грамота": 0.25}),
        self_concept=SelfConcept(
            self_esteem=-0.3,
            identity=["Ты солдат, а не палач", "Ты отвечаешь за своих людей"],
            denied=["что ты тогда струсил и увёл отряд слишком поздно"],
        ),
    )


def main() -> None:
    g = make_guard()
    print(repr(g), "\n")

    # разогнать состояние: устал, задет, ситуация вышла из-под контроля
    g.state.needs.update({"order": 0.8, "status": 0.5, "belonging": 0.7})
    g.state.apply(g.temperament, dp=-0.6, da=+0.7, dd=-0.4, cost=0.5)
    g.state.attitudes["Аэн"] = -0.5
    g.state.remember("она провела чужаков через твой пост ночью", "Аэн", -0.8, 1.0)

    pr = g.system_prompt(interlocutor=Interlocutor("Аэн", female=True), scene="караулка, третий час ночи, дождь")
    print("=" * 70)
    print("STABLE (кешируемый префикс)")
    print("=" * 70)
    print(pr.stable)
    print()
    print("=" * 70)
    print("VOLATILE (пересобирается каждый тик)")
    print("=" * 70)
    print(pr.volatile)

    print("\n" + "=" * 70)
    print("ВЫБОР ДЕЙСТВИЯ (решает симуляция, не LLM)")
    print("=" * 70)
    options = {
        "арестовать её":      dict(satisfies={"order": 1.0, "control": 0.7}, risk=0.3),
        "выслушать":          dict(satisfies={"belonging": 0.6, "meaning": 0.4}, risk=0.0),
        "взять взятку":       dict(satisfies={"status": 0.3, "pleasure": 0.5}, risk=0.9),
        "позвать капитана":   dict(satisfies={"safety": 0.6, "order": 0.5}, risk=0.1),
    }
    for name, kw in sorted(options.items(), key=lambda kv: -g.score(**kv[1])):
        print(f"  {g.score(**kw):+.3f}  {name}")


if __name__ == "__main__":
    main()
