"""Обёртки в работе."""
from World.demo import W
from World.store import Store
from World.view import Gouverment, Person, Region


def main():
    s = Store(W)

    r = Region(s, "reg.7")
    print(r)
    print("  биом:        ", r.biome)
    print("  население:   ", r.population)
    print("  государство: ", r.gouverment.name)
    print("  правитель:   ", r.gouverment.ruler.name, " <- две ссылки подряд")
    print("  вера:        ", r.dominant_faith().name, f"({r.faith('ideo.1')})")
    print("  войска:      ", [d.name for d in r.divisions], " <- из индекса")

    g = Gouverment(s, "gov.1")
    print("\n", g)
    print("  регионы:     ", [x.name for x in g.regions],
          "\n                (в записи gov.1 списка регионов нет)")
    print("  живая сила:  ", g.manpower, " <- army -> divisions -> manpower")

    p = Person(s, "per.1")
    print("\n", p)
    print("  идеология:   ", p.ideology.name)
    print("  правит:      ", [x.name for x in p.rules])

    print("\n--- обёртка не копия, а вид на запись ---")
    before = r.population
    for _ in range(10):
        r.tick()
    print(f"  население {before} -> {r.population}")
    print("  в хранилище:", s.rec["reg.7"]["population"], " <- то же число")
    print("  другая обёртка того же региона:", Region(s, "reg.7").population)

    print("\n--- to_dict не нужен ---")
    print("  запись уже является хранимой формой:")
    print("  ", {k: v for k, v in s.rec["reg.7"].items() if k != "faiths"})


if __name__ == "__main__":
    main()
