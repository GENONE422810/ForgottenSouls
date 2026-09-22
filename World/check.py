"""Проверка эталонного сейва: целостность, охват типов, обход."""
import json
import os

from World.store import REF_FIELDS, Store

PATH = os.path.join(os.path.dirname(__file__), "..", "Docs", "examples", "save.json")


def main() -> None:
    s = Store(json.load(open(PATH, encoding="utf-8")))
    kinds = {r.get("type") for r in s.rec.values()}

    print(f"записей: {len(s.rec)}, типов: {len(kinds)}")
    bad = s.dangling()
    print("битые ссылки:", bad or "нет")

    undeclared = sorted(k for k in kinds if k not in REF_FIELDS)
    print("типы без объявленных ref-полей:", undeclared or "нет")

    print("\nвложенные ссылки достаются:")
    for path, got in (
        ("soul.domains", "dom.1"),
        ("soul.progress (ключ)", "pth.1"),
        ("personality.state.attitudes (ключ)", "per.2"),
        ("personality.state.episodes.*.who", "per.2"),
    ):
        print(f"  {path:38} -> {'да' if got in s.refs_of('per.1') else 'НЕТ'}")

    print("\nbattle.instances.*.of и .actor:")
    print("  ", s.refs_of("btl.1"))

    print("\nобратный индекс:")
    for rid in ("reg.7", "per.1", "gov.1"):
        print(f"  на {rid:8} ссылаются: {s.linked_to(rid)}")

    assert not bad, "есть битые ссылки"
    assert not undeclared, "есть типы без ref-полей"
    print("\nвсё сошлось")


if __name__ == "__main__":
    main()
