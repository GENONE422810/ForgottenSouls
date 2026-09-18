"""Рендер снимка личности в системный промпт для обработчика-эмпата.

Два принципа:
1. Никаких голых чисел. LLM плохо отыгрывает по статблоку и хорошо —
   по прозе во втором лице. Числа переводим в словесные градации.
2. Промпт режется на stable / volatile. Stable одинакова всю игру
   (её кеширует провайдер), volatile пересобирается каждый тик.
"""
from __future__ import annotations

from dataclasses import dataclass

from .traits import CHARACTER_AXES


@dataclass(slots=True)
class PersonaPrompt:
    stable: str      # личность: не меняется -> кешируемый префикс
    volatile: str    # состояние сцены: меняется каждый вызов

    def as_text(self) -> str:
        return f"{self.stable}\n\n{self.volatile}"

    def as_messages(self) -> list[dict]:
        """Готово для API с кешированием стабильного префикса."""
        return [
            {"type": "text", "text": self.stable,
             "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": self.volatile},
        ]


# --- вербализация -----------------------------------------------------------
def _band(v: float, labels: tuple[str, ...], lo: float = -1.0, hi: float = 1.0) -> str:
    """Число -> словесная градация."""
    span = (hi - lo) or 1.0
    idx = int((v - lo) / span * len(labels))
    return labels[max(0, min(len(labels) - 1, idx))]


_DEGREE = ("совсем не", "не особо", "довольно", "очень")


def _axis_phrase(name: str, value: float) -> str | None:
    """Ось характера -> фраза. Слабые оси выкидываем, они шум."""
    if abs(value) < 0.25:
        return None
    pos, neg = CHARACTER_AXES[name]
    pole = pos if value > 0 else neg
    mag = abs(value)
    prefix = "" if mag < 0.55 else ("скорее " if mag < 0.75 else "подчёркнуто ")
    return f"{prefix}{pole}".strip()


def _speech_lines(s) -> list[str]:
    out = []
    out.append("Темп речи: " + _band(s.tempo, (
        "медленный, с паузами, слова подбираешь",
        "ровный, неспешный",
        "живой",
        "быстрый, глотаешь окончания, перебиваешь"), 0.0, 1.0))
    out.append("Длина реплик: " + _band(s.verbosity, (
        "одно-два слова, часто просто кивок",
        "коротко, по делу",
        "нормальная живая речь",
        "многословно, уходишь в отступления"), 0.0, 1.0))
    out.append("Манера: " + _band(s.directness, (
        "говоришь намёками, прямого ответа избегаешь",
        "смягчаешь, заходишь издалека",
        "говоришь прямо",
        "рубишь в лоб, без предисловий"), 0.0, 1.0))
    out.append("Тон: " + _band(s.warmth, (
        "холодный, отстранённый",
        "сдержанный",
        "доброжелательный",
        "тёплый, участливый"), 0.0, 1.0))
    out.append("Регистр: " + _band(s.formality, (
        "просторечие, как на улице",
        "обычная разговорная речь",
        "вежливо, соблюдаешь приличия",
        "церемонно, с титулами и оборотами"), 0.0, 1.0))
    # грубость гасится регистром: церемонный человек не сквернословит
    effective = s.profanity * (1.0 - s.formality)
    if effective > 0.25:
        out.append("Грубых слов не стесняешься.")
    return out


def _reply_length_rule(verbosity: float) -> str:
    return _band(verbosity, (
        "Реплика — несколько слов. Часто достаточно жеста вместо ответа.",
        "Реплика — одна короткая фраза. Лишнего не говоришь.",
        "Реплика — одна-две фразы. Живые люди не говорят абзацами.",
        "Ты говоришь охотно и с отступлениями, но всё равно не длиннее "
        "четырёх-пяти фраз за раз."), 0.0, 1.0)


# --- сборка -----------------------------------------------------------------
def render(snap, scene: str = "") -> PersonaPrompt:
    return PersonaPrompt(stable=_stable(snap), volatile=_volatile(snap, scene))


def _stable(s) -> str:
    p: list[str] = []
    p.append(
        f"Ты отыгрываешь персонажа по имени {s.name}"
        + (f", {s.age} лет" if s.age else "")
        + (f", {s.role}" if s.role else "")
        + ". Ты не ассистент и не рассказчик. Ты — этот человек."
    )
    if s.background:
        p.append(f"Откуда ты взялся: {s.background}")

    p.append(
        f"\n# Как устроена твоя нервная система\n"
        f"Ты {s.temperament_label}. "
        + _band(s.temperament.reactivity, (
            "Задеть тебя трудно, ты почти не заводишься.",
            "На резкое ты реагируешь, но без бури.",
            "Реагируешь остро, сразу видно.",
            "Вспыхиваешь мгновенно и сильно."), 0.0, 1.0)
        + " "
        + _band(s.temperament.inertia, (
            "Отпускает тебя почти сразу — минуту назад орал, сейчас смеёшься.",
            "Успокаиваешься довольно быстро.",
            "Отходишь медленно, обида тлеет.",
            "Задетое держится в тебе часами и днями."), 0.0, 1.0)
        + " "
        + _band(s.temperament.energy, (
            "Сил мало, устаёшь от людей и шума.",
            "Выносливость средняя.",
            "Энергии много.",
            "Энергии через край, но тратишь её залпом."), 0.0, 1.0)
    )

    traits = [ph for n, v in s.character.items() if (ph := _axis_phrase(n, v))]
    if traits:
        p.append("\n# Характер\nТы " + ", ".join(traits) + ".")

    open_d = [d for d in s.desires if not d.secret]
    secret_d = [d for d in s.desires if d.secret]
    if open_d:
        p.append("\n# Чего ты хочешь\n" + "\n".join(
            f"- {d.text}" + (" (это для тебя главное)" if d.weight > 0.75 else "")
            for d in sorted(open_d, key=lambda x: -x.weight)))
    if secret_d:
        p.append("\n# Чего ты хочешь, но вслух не скажешь\n" + "\n".join(
            f"- {d.text}" for d in secret_d)
            + "\nЭто правит твоими поступками, но прямо ты об этом не говоришь. "
              "Если разговор подходит близко — уводишь в сторону.")

    if s.fears:
        p.append("\n# Чего ты боишься\n" + "\n".join(f"- {f}" for f in s.fears)
                 + "\nСтрах сильнее желания: если задето это — ты реагируешь до того, "
                   "как успел подумать.")

    if s.habits:
        verbal = [h for h in s.habits if h.verbal]
        body = [h for h in s.habits if not h.verbal]
        lines = []
        if body:
            lines += [f"- Когда {h.trigger} — {h.action}." for h in body]
        if verbal:
            lines += [f"- В речи: {h.action} ({h.trigger})." for h in verbal]
        p.append("\n# Привычки\n" + "\n".join(lines)
                 + "\nПривычка срабатывает сама, раньше рассудка. Вставляй их в "
                   "описания действий, не объясняя.")

    best = s.abilities.best(3)
    if best:
        p.append("\n# Что ты умеешь\n" + ", ".join(
            f"{k} ({_band(v, ('кое-как', 'сносно', 'хорошо', 'мастерски'), 0.0, 1.0)})"
            for k, v in best)
            + "\nО том, в чём ты силён, говоришь уверенно. В остальном не берёшься судить.")

    sc = s.self_concept
    if sc.identity or sc.denied:
        block = ["\n# Каким ты себя видишь"]
        if sc.identity:
            block += [f"- {i}" for i in sc.identity]
        block.append(_band(sc.self_esteem, (
            "В глубине ты считаешь себя ничтожеством.",
            "Ты собой не слишком доволен.",
            "Ты о себе неплохого мнения.",
            "Ты уверен, что стоишь куда больше, чем тебе дают."), -1.0, 1.0))
        if sc.denied:
            block.append("Чего ты в себе НЕ признаёшь: "
                         + "; ".join(sc.denied)
                         + ". Прямое указание на это ты отрицаешь — злостью, "
                           "шуткой или сменой темы. Это твоё слепое пятно, "
                           "и оно должно быть заметно со стороны.")
        p.append("\n".join(block))

    p.append("\n# Как ты говоришь\n" + "\n".join(_speech_lines(s.speech)))

    p.append(
        "\n# Правила отыгрыша\n"
        "- Ты знаешь только то, что знает твой персонаж. Ни слова о механике игры.\n"
        "- Ты не обязан помогать собеседнику. Помогаешь, только если это отвечает "
        "твоим желаниям или отношению к нему.\n"
        f"- {_reply_length_rule(s.speech.verbosity)}\n"
        "- Тебе дадут НАМЕРЕНИЕ, выбранное симуляцией. Твоя задача — озвучить "
        "именно его, своим голосом. Менять намерение нельзя."
    )
    return "\n".join(p)


def _volatile(s, scene: str = "") -> str:
    st = s.state
    p: list[str] = ["# Прямо сейчас"]

    p.append("Состояние: " + _band(st.mood.pleasure, (
        "тебе тяжело и мерзко", "ты не в духе", "ты в порядке", "тебе хорошо"))
        + ", " + _band(st.mood.arousal, (
        "вял и заторможен", "спокоен", "на взводе", "взвинчен до предела"))
        + ", " + _band(st.mood.dominance, (
        "чувствуешь себя загнанным", "чувствуешь себя неуверенно",
        "держишься уверенно", "чувствуешь себя хозяином положения")) + ".")

    if st.stamina < 0.35:
        p.append("Ты вымотан. На длинный разговор тебя не хватит, "
                 "отвечаешь короче и раздражительнее обычного.")

    top = [(n, v) for n, v in s.urgency.items() if v > 0.2][:2]
    if top:
        NEED_RU = {
            "safety": "тебе нужно почувствовать себя в безопасности",
            "belonging": "тебе не хватает близких людей",
            "status": "тебе нужно, чтобы тебя признали",
            "control": "тебе невыносимо, что ситуация не в твоих руках",
            "order": "тебя изводит бардак вокруг",
            "autonomy": "тебе душно от чужой воли",
            "novelty": "тебя тошнит от однообразия",
            "meaning": "тебе нужно понять, ради чего всё это",
            "altruism": "тебе нужно быть кому-то полезным",
            "pleasure": "тебе давно не было хорошо",
            "mastery": "у тебя руки чешутся сделать что-то стоящее",
        }
        p.append("Что тебя гложет: " + "; ".join(NEED_RU[n] for n, _ in top) + ".")

    if s.interlocutor:
        him, he = ("её", "ей") if s.interlocutor_female else ("его", "ему")
        p.append(f"\nПеред тобой: {s.interlocutor}. " + _band(s.attitude, (
            f"Ты {him} не выносишь.", f"Ты {he} не доверяешь.",
            f"Ты к {'ней' if s.interlocutor_female else 'нему'} расположен.",
            f"Ты {he} предан.")))
        if s.shared_memory:
            p.append(f"Что всплывает в памяти о {'ней' if s.interlocutor_female else 'нём'}:")
            for e in s.shared_memory:
                mark = "тяжело" if e.valence < -0.3 else ("тепло" if e.valence > 0.3 else "ровно")
                p.append(f"- {e.what} (вспоминается {mark})")

    if scene:
        p.append(f"\nОбстановка: {scene}")
    return "\n".join(p)


def outward_impression(person) -> str:
    """Как персонаж выглядит СО СТОРОНЫ.

    Другие не читают его мыслей: им видна только та часть состояния,
    которую он не сумел спрятать. Насколько сумел — решает темперамент:
    флегматика не прочитаешь, холерик весь наружу.
    """
    t = person.temperament
    m = person.state.mood
    show = max(0.15, min(1.0, t.reactivity * (1.0 - t.inertia * 0.25)))
    p, a = m.pleasure * show, m.arousal * show

    face = _band(p, ("лицо мрачное", "вид недовольный",
                     "выражение обычное", "выглядит довольным"))
    body = _band(a, ("движения вялые", "держится спокойно",
                     "заметно напряжён", "не находит себе места"))
    out = f"{face}, {body}"
    if person.state.stamina < 0.35:
        out += ", вид усталый"
    return out
