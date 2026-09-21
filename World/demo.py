"""Проверка хранилища на маленьком мире."""
from World.store import Store

W = {
  "plane.1":  {"type":"plane","name":"Первый пласт"},
  "world.1":  {"type":"world","name":"Ирм","plane":"plane.1","territoryis":"terr.1"},
  "terr.1":   {"type":"territoryis","world":"world.1","size":[100,100]},
  "reg.7":    {"type":"region","name":"Южные ворота","territoryis":"terr.1",
               "gouverment":"gov.1","biome":"степь","population":41000,
               "faiths":{"ideo.1":0.7,"ideo.2":0.2}},
  "reg.8":    {"type":"region","name":"Пустошь","territoryis":"terr.1",
               "gouverment":"gov.1","biome":"пустошь","population":900,"faiths":{}},
  "gov.1":    {"type":"gouverment","name":"Венец","world":"world.1",
               "глава":"per.1","army":"army.1"},
  "ideo.1":   {"type":"ideology","name":"Culto del Faro","world":"world.1","god":"per.2"},
  "ideo.2":   {"type":"ideology","name":"Молчащие","world":"world.1"},
  "army.1":   {"type":"army","name":"Первое войско"},
  "div.3":    {"type":"division","name":"Копейщики","army":"army.1","pos":"reg.7"},
  "per.1":    {"type":"person","name":"Ведор Крайн","current_world":"world.1",
               "ideology":"ideo.1","battle":"comb.1"},
  "per.2":    {"type":"person","name":"Аэн","current_world":"world.1","ideology":"ideo.2"},
  "comb.1":   {"type":"combatant","speed":4},
  "ev.12":    {"type":"event","name":"ночной досмотр","when":4120,
               "who":["per.1","per.2"],"where":"reg.7","importance":0.8,
               "refs":["gov.1"]},
}

def main():
    s = Store(W)
    print("записей:", len(s.rec), " битых ссылок:", s.dangling())

    print("\nregion reg.7")
    print("  ссылается на: ", s.refs_of("reg.7"))
    print("  ссылаются сюда:", s.linked_to("reg.7"))
    print("  (списка регионов у gov.1 нет — связь хранится только на регионе)")

    for d in (1, 2):
        g = s.gather("reg.7", d)
        names = sorted(s.rec[i].get("name", i) for i in g)
        print(f"\nконтекст от reg.7, глубина {d}: {len(g)} записей")
        print("  " + ", ".join(names))

    import os, tempfile
    p = os.path.join(tempfile.mkdtemp(), "world.json")
    s.save(p)
    s2 = Store.load(p)
    print("\nroundtrip:", s2.rec == s.rec,
          " индекс восстановлен:", s2.linked_to("reg.7") == s.linked_to("reg.7"))
    print("размер на диске:", os.path.getsize(p), "байт")

    # что ломается, если забыть про целостность
    s.rec["reg.7"]["gouverment"] = "gov.404"
    s.reindex()
    print("\nпосле битой ссылки:", s.dangling())

if __name__ == "__main__":
    main()
