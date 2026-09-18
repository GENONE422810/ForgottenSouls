"""Диалог с составом сцены."""
from AI.client import LLM
from AI.Roles.empath import Empath
from AI.scene import MapPerson, Scene
from Person.demo import make_guard


def build_scene() -> Scene:
    scene = Scene(
        scene_id="karaulka",
        place="караулка у южных ворот",
        situation="третий час ночи, дождь",
        player_name="Путник",
    )
    scene.add(MapPerson(make_guard(), kind="человек"))
    return scene


def main() -> None:
    empath = Empath(LLM())
    scene = build_scene()

    while True:
        try:
            said = input(">> ").strip()
        except (EOFError, KeyboardInterrupt):
            said = "X"
        if said in ("X", "x", "выход", ""):
            break
        for reply in empath.play(scene, player_text=said):
            print(f"{reply.name}: {reply.text}")

    scene.save()
    print("сцена сохранена")


if __name__ == "__main__":
    main()
