"""Demo content for the Allegro platform: three FICTIONAL authors, opuses with PDF scores, MusicXML (cursor follows
the recording note by note), recordings + page-sync markers, collections, articles, notes, workshop threads and
critiques with timecodes.

    python -m scripts.seed           (run from backend/, after `alembic upgrade head`)

Only the demo accounts below are replaced; real accounts and their works are never touched.
The demo authors are created "in the shadow" (hidden from the site) unless --visible is given;
toggle later with `python -m scripts.shadow show|hide <usernames>`.
Demo password: allegro-demo
"""
import random
import shutil
from datetime import timedelta

from sqlalchemy import delete, select

from allegro.core.db import SessionLocal
from allegro.core.security import hash_password
from allegro.core.slugs import unique_slug
from allegro.core.storage import storage
from allegro.models import (
    Collection, CollectionItem, Comment, Material, MeasureSyncMarker, Opus, Post, ScoreSyncMarker, User,
)
from allegro.modules.accounts.models import utcnow
from scripts.assets import compose, painting_svg, piece_musicxml, render_wav, score_pdf

PASSWORD = "allegro-demo"
# One demo member of each kind (all fictional)
DEMO_ROLES = {"lev_orlovsky": "composer", "kostya_theory": "theorist", "maria_viola": "performer"}


def put(key: str, data: bytes) -> str:
    return storage.save_bytes(f"seed/{key}", data)


USERS = [
    {
        "username": "lev_orlovsky", "display_name": "Лев Орловский", "pseudonym": None,
        "bio": "Вымышленный композитор для демонстрации: камерная и хоровая музыка, романтическая гармония.",
        "about_md": """## О демо-авторе

Этот кабинет создан для демонстрации возможностей альманаха: опусы с партитурами и записями, заметки, сборники.

## Сочинения

- **Фортепианное трио ре минор**, op. 1
- **Прелюдии**, op. 2
- **«Флориография»** — хоровой цикл о языке цветов""",
        "links": [], "palette": 0,
    },
    {
        "username": "kostya_theory", "display_name": "Константин Ремезов", "pseudonym": "Костя-теоретик",
        "bio": "Теоретик и аналитик. Пишу о форме, гармонии и о том, почему кода иногда не звучит.",
        "about_md": "## О себе\n\nПреподаю гармонию и анализ форм. Разбираю чужие партитуры с любовью и карандашом.",
        "links": [{"label": "Telegram", "url": "https://t.me/"}], "palette": 1,
    },
    {
        "username": "maria_viola", "display_name": "Мария Вельская", "pseudonym": None,
        "bio": "Альтистка и композитор. Камерная музыка, lamento и всё, что звучит в среднем регистре.",
        "about_md": "## О себе\n\nИграю в струнном квартете, пишу для альта — инструмента, которому всегда не хватает репертуара.",
        "links": [], "palette": 2,
    },
]

OPUSES = [
    {
        "author": "lev_orlovsky", "title": "Фортепианное трио ре минор", "subtitle": "op. 1, Ч. I: Allegro",
        "slug": "piano-trio-d-minor", "parts": ("Скрипка", "Фортепиано"), "genre": "trio", "key_signature": "ре минор",
        "year": 2026, "instruments": ["скрипка", "виолончель", "фортепиано"],
        "description_md": """Экспозиция строится на **терцовых соотношениях**: ре минор — фа мажор — ля минор вместо привычной доминанты.

> Главная партия — вздох lamento, нисходящий тетрахорд в басу.

Побочная партия (с 00:24) передаёт тему скрипке, фортепиано уходит в фигурацию. В разработке (00:48) тема дробится между виолончелью и левой рукой.""",
        "pdf": ("Piano Trio in D minor", "op. 1 - I. Allegro", "Allegro con brio", ["Vln.", "Vc.", "Pno."]),
        "pages": 4, "audio": ("d", True, 100, [0, 5, 2, 4, 0, 3, 4, 0], 40, ["violin", "strings"]),
        "score_access": "free", "plays": 214, "palette": 0,
    },
    {
        "author": "lev_orlovsky", "title": "Прелюдия ми минор", "subtitle": "op. 2 № 1", "slug": "prelude-e-minor", "parts": ("Фортепиано (п. р.)", "Фортепиано (л. р.)"),
        "genre": "solo", "key_signature": "ми минор", "year": 2025,
        "instruments": ["фортепиано"],
        "description_md": "Миниатюра на одном мотиве: секунда вниз и возвращение. Почти Шопен, но с тишиной вместо педали.",
        "pdf": ("Prelude in E minor", "op. 2 No. 1", "Largo", ["Pno.", ""]),
        "pages": 2, "audio": ("e", True, 72, [0, 3, 4, 0], 14, []), "score_access": "view_only", "plays": 98, "palette": 4,
    },
    {
        "author": "lev_orlovsky", "title": "Флориография. I. Фиалка", "subtitle": "op. 3 № 1", "slug": "floriography-violet", "parts": ("Сопрано", "Фортепиано"),
        "genre": "choir", "key_signature": "фа мажор", "year": 2026,
        "instruments": ["хор"],
        "description_md": "Первая пьеса цикла о языке цветов. Фиалка — скромность: хор поёт почти шёпотом, *pp* до самого конца.",
        "pdf": ("Floriography", "I. The Violet", "Andante semplice", ["S.", "A.", "T.", "B."]),
        "pages": 3, "audio": ("f", False, 66, [0, 3, 5, 4], 16, ["choir"]), "score_access": "free", "plays": 57, "palette": 3,
    },
    {
        "author": "lev_orlovsky", "title": "Флориография. II. Асфодель", "subtitle": "op. 3 № 2", "slug": "floriography-asphodel",
        "genre": "cantata", "key_signature": "ре минор", "year": 2026,
        "instruments": ["хор", "струнный оркестр"],
        "description_md": "Асфодель — цветок забвения. Записи пока нет: только партитура.",
        "pdf": ("Floriography", "II. The Asphodel", "Lento", ["S.", "A.", "T.", "B."]),
        "pages": 2, "audio": None, "score_access": "free", "plays": 0, "palette": 1,
    },
    {
        "author": "maria_viola", "title": "Вариации на тему lamento", "subtitle": "для альта и фортепиано", "slug": "lamento-variations", "parts": ("Альт", "Фортепиано"),
        "genre": "duo_sonata", "key_signature": "соль минор", "year": 2025,
        "instruments": ["альт", "фортепиано"],
        "description_md": "Пять вариаций на нисходящий тетрахорд. В третьей альт уходит в низкий регистр — проверяю, не тонет ли он.",
        "pdf": ("Variations on a Lamento", "for viola and piano", "Adagio", ["Vla.", "Pno."]),
        "pages": 3, "audio": ("g", True, 80, [0, 6, 5, 4], 24, ["violin"]), "score_access": "free", "plays": 131, "palette": 2,
    },
    {
        "author": "kostya_theory", "title": "Симфоническая поэма «Сумерки»", "subtitle": "для большого оркестра", "slug": "twilight-poem", "parts": ("Флейта", "Струнные"),
        "genre": "orchestral", "key_signature": "до минор", "year": 2024,
        "instruments": ["оркестр"],
        "description_md": "Попытка теоретика доказать, что он тоже умеет сочинять. Валторны — главные герои.",
        "pdf": ("Twilight", "Symphonic poem", "Maestoso", ["Fl.", "Hn.", "Vln.", "Vc."]),
        "pages": 4, "audio": ("c", True, 60, [0, 5, 3, 4], 22, ["horn", "strings"]), "score_access": "view_only", "plays": 76, "palette": 1,
    },
]

POSTS = [
    {
        "author": "kostya_theory", "kind": "article", "slug": "tertian-relations-exposition",
        "title": "Терцовые соотношения в романтической экспозиции",
        "excerpt": "Почему у Шуберта побочная партия так часто уходит не в доминанту, а на терцию вниз — и что это даёт форме.",
        "content_md": """Классическая экспозиция держится на тоническо-доминантовом противопоставлении. Романтики ослабляют его — и сразу теряют «пружину» формы. Чем они её заменяют?

## Терция вместо квинты

У Шуберта в первой части сонаты си-бемоль мажор побочная партия появляется в **соль-бемоль мажоре** — на большую терцию вниз. Модуляция звучит не как конфликт, а как смена освещения.

> Терцовое соотношение — это не драма, а свет, падающий под другим углом.

## Что это значит для фактуры

1. Общий звук двух тональностей держит связность — его можно оставить в басу.
2. Хроматический голос ведётся полутоном — отличная работа для средних голосов.
3. Доминанта никуда не исчезает: она переезжает в заключительную партию.

## Практический вывод

Если ваша экспозиция «проседает», проверьте, не пропал ли общий звук при переходе. Чаще всего проблема не в гармонии, а в том, что бас потерял опору.""",
        "palette": 1, "days": 3,
    },
    {
        "author": "lev_orlovsky", "kind": "article", "slug": "lamento-bass",
        "title": "Lamento bass: четыре века нисходящего тетрахорда",
        "excerpt": "От Монтеверди до Led Zeppelin — одна и та же формула скорби в басу.",
        "content_md": """Четыре ноты вниз по гамме — и слушатель уже знает, что будет печально.

## Истоки

В «Плаче нимфы» Монтеверди тетрахорд звучит как остинато: бас повторяет его снова и снова, пока голос над ним ищет выход.

## Как я использую его в трио

В первой части моего трио тетрахорд спрятан в левой руке фортепиано. Он не повторяется буквально — каждый раз одна из ступеней хроматизируется.""",
        "palette": 0, "days": 8,
    },
    {
        "author": "lev_orlovsky", "kind": "note", "slug": "nocturne-without-end",
        "title": "Ноктюрн, который не хотел заканчиваться",
        "excerpt": "Три недели я искал последний аккорд. Он нашёлся в черновике двухлетней давности.",
        "content_md": """Бывают пьесы, которые пишутся за вечер. Этот ноктюрн — не из них.

## Середина

Средний раздел переписывался **шесть раз**. В итоге я оставил почти пустую фактуру: бас, педаль и одинокий голос сверху.

- первая версия — хорал, слишком тяжело;
- третья — арпеджио, слишком «красиво»;
- шестая — тишина и один голос.

Ниже — фотографии черновиков.""",
        "palette": 3, "days": 12, "images": 3,
    },
    {
        "author": "lev_orlovsky", "kind": "note", "slug": "on-silence", "title": "О тишине в музыке",
        "excerpt": "Паузы — это не отсутствие звука, а его продолжение другими средствами.",
        "content_md": "Я всё чаще ловлю себя на том, что пишу меньше нот.\n\nПауза в конце фразы работает как запятая: она даёт слушателю время услышать то, что уже прозвучало.",
        "palette": 4, "days": 20,
    },
    {
        "author": "lev_orlovsky", "kind": "workshop", "slug": "trio-exposition-texture",
        "title": "Послушайте экспозицию моего трио — не проседает ли фактура?",
        "excerpt": "С 0:24 по 0:48 мне кажется, что фортепиано перекрывает виолончель.",
        "content_md": """Прошу свежих ушей. Меня беспокоит побочная партия: с **0:24** по **0:48** фортепиано ведёт фигурацию в среднем регистре, и виолончель, по-моему, тонет.

Вопросы:

1. Слышна ли линия виолончели на 0:30?
2. Не перегружен ли бас в конце экспозиции (0:44)?""",
        "opus": "piano-trio-d-minor", "days": 1,
    },
    {
        "author": "maria_viola", "kind": "workshop", "slug": "lamento-variation-three",
        "title": "Вариация III: альт тонет в фортепиано?",
        "excerpt": "Низкий регистр альта против плотных аккордов — нужен совет по балансу.",
        "content_md": "В третьей вариации (примерно с 0:40) альт опускается на струну до. Слышно ли его вообще?",
        "opus": "lamento-variations", "days": 2,
    },
]

COMMENTS = [
    # (target, author, timestamp, text, reply_to_index)
    (("opus", "piano-trio-d-minor"), "kostya_theory", 52, "Вот здесь, на 00:52, терцдецимаккорд перегружен в басу — попробуйте убрать квинту в левой руке.", None),
    (("opus", "piano-trio-d-minor"), "lev_orlovsky", None, "Спасибо! Уберу квинту и раздвину расположение. Послушайте ещё 01:14 — там та же беда?", 0),
    (("opus", "piano-trio-d-minor"), "maria_viola", 30, "Вход скрипки на 00:30 — чудесный. Но виолончель в этом месте дублирует бас фортепиано, и тембр теряется.", None),
    (("opus", "piano-trio-d-minor"), "kostya_theory", None, "Согласен с Марией. Поднимите виолончель на октаву — пусть поёт в теноровом регистре.", 2),
    (("post", "trio-exposition-texture"), "maria_viola", 40, "С 0:24 по 0:48 фактура держится, провал только около 0:40 — там фортепиано уходит в тот же регистр.", None),
    (("post", "tertian-relations-exposition"), "lev_orlovsky", None, "Отличный разбор. Проверил своё трио — общий звук при переходе действительно терялся.", None),
    (("opus", "lamento-variations"), "lev_orlovsky", 44, "На 00:44 альт слышен, но я бы облегчил правую руку — оставить только верхний голос.", None),
]

# Short channel-style posts (no title), newest first in the hall's «Блог»
CHANNEL = [
    ("lev_orlovsky", 0.2, "Дописал коду трио. Завтра — запись с живыми музыкантами, держите кулаки 🤞", 0),
    ("lev_orlovsky", 1.3, "Черновик второй части — пока только карандашом.", 1),
    ("lev_orlovsky", 4, "Лучший совет, который я получил по оркестровке: *сначала убери, потом добавь*.", None),
    ("maria_viola", 0.6, "Разыграла вариации с пианистом. Третья наконец-то звучит — альт больше не тонет.", None),
    ("kostya_theory", 2.2, "Новый разбор скоро. Тема — **неаполитанский секстаккорд** у Шуберта.", None),
]

MATERIALS = [
    ("lev_orlovsky", "book", "Учебник гармонии", "Классический курс: от трезвучий до модуляций. Мой экземпляр весь в пометках.", None, "notes"),
    ("lev_orlovsky", "book", "Трактат об оркестровке", "Настольная книга — перечитываю перед каждой партитурой.", "https://imslp.org/", None),
    ("lev_orlovsky", "link", "Партитуры на IMSLP", "Нотная библиотека: тысячи партитур в свободном доступе.", "https://imslp.org/", None),
    ("lev_orlovsky", "link", "MuseScore", "Бесплатный нотный редактор, в котором я набираю черновики.", "https://musescore.org/", None),
    ("lev_orlovsky", "file", "Партии трио для репетиции", "Скрипка, виолончель и фортепиано отдельными листами.", None, "parts"),
    ("kostya_theory", "link", "Словарь гармонических терминов", "Шпаргалка к разборам.", "https://en.wikipedia.org/wiki/Harmony", None),
]

COLLECTIONS = [
    ("lev_orlovsky", "Цикл «Флориография»", "floriography", 2026, "Хоровые миниатюры о языке цветов.", ["floriography-violet", "floriography-asphodel"]),
    ("lev_orlovsky", "Фортепианные прелюдии, op. 2", "preludes-op-2", 2025, "Короткие пьесы для фортепиано.", ["prelude-e-minor"]),
]


def seed(visible: bool = False) -> None:
    rng = random.Random(7)
    db = SessionLocal()
    try:
        usernames = [u["username"] for u in USERS]
        db.execute(delete(User).where(User.username.in_(usernames)))
        db.commit()
        if storage.is_local:
            shutil.rmtree(storage.root / "seed", ignore_errors=True)

        now = utcnow()
        users = {}
        for i, data in enumerate(USERS):
            avatar = put(f"avatars/{data['username']}.svg", painting_svg("", data["palette"], 40 + i, 600, 800, portrait=True))
            user = User(
                username=data["username"], role=DEMO_ROLES.get(data["username"], "composer"), password_hash=hash_password(PASSWORD),
                is_hidden=not visible,  # demo filler stays in the shadow unless asked for
                display_name=data["display_name"], pseudonym=data["pseudonym"], bio=data["bio"], about_md=data["about_md"],
                links=data["links"], avatar_url=avatar, created_at=now - timedelta(days=200 - i * 30),
            )
            db.add(user)
            users[user.username] = user
        db.flush()

        opuses = {}
        for i, data in enumerate(OPUSES):
            slug = data["slug"]
            title, movement, tempo, instruments = data["pdf"]
            instruments = [x for x in instruments if x] or ["Pno."]
            pdf_key = f"seed/scores/{slug}.pdf"
            storage.save_bytes(pdf_key, score_pdf(title, movement, tempo, instruments, data["pages"], seed=i))
            audio_type, audio_key, duration, markers, xml_key, measure_markers = "none", None, None, [], None, []
            if data["audio"]:
                key, minor, bpm, progression, bars, layers = data["audio"]
                piece = compose(key, minor, bpm, progression, bars, layers, seed=i)
                wav, duration = render_wav(piece)
                audio_key = f"seed/audio/{slug}.wav"
                storage.save_bytes(audio_key, wav)
                audio_type = "hosted_file"
                # The MusicXML is engraved from the very notes that were synthesized: the cursor matches exactly
                xml_key = f"seed/musicxml/{slug}.musicxml"
                author_name = next(u["display_name"] for u in USERS if u["username"] == data["author"])
                storage.save_bytes(xml_key, piece_musicxml(piece, data["title"], author_name, tempo, data["parts"]))
                if slug == "piano-trio-d-minor":
                    # Demonstrates measure markers (a live performance would need them for rubato)
                    measure_markers = [
                        MeasureSyncMarker(measure_number=m, timestamp_seconds=round((m - 1) * 4 * 60 / bpm, 2))
                        for m in (1, 9, 17, 25, 33)
                    ]
                # Pages turn on bar lines: split the music evenly between pages
                music = bars * 4 * 60 / bpm
                markers = [
                    ScoreSyncMarker(page_number=p + 1, timestamp_seconds=round(p * music / data["pages"], 2))
                    for p in range(data["pages"])
                ]
            opus = Opus(
                author_id=users[data["author"]].id, title=data["title"], subtitle=data["subtitle"],
                slug=unique_slug(db, Opus.slug, slug),
                genre=data["genre"], instruments=data["instruments"], key_signature=data["key_signature"],
                year=data["year"], description_md=data["description_md"],
                cover_url=put(f"covers/{slug}.svg", painting_svg(title, data["palette"], 10 + i)),
                audio_type=audio_type, audio_source=audio_key, audio_duration_seconds=duration,
                score_file_key=pdf_key, score_page_count=data["pages"], score_access=data["score_access"],
                musicxml_file_key=xml_key, measure_markers=measure_markers,
                play_count=data["plays"], created_at=now - timedelta(days=i * 4 + 1, hours=rng.randint(0, 20)),
                markers=markers,
            )
            db.add(opus)
            opuses[slug] = opus
        db.flush()

        posts = {}
        for i, data in enumerate(POSTS):
            attachments = []
            for n in range(data.get("images", 0)):
                url = put(f"posts/{data['slug']}-{n + 1}.svg", painting_svg(f"sketch {n + 1}", n + 2, 60 + n))
                attachments.append({"url": url, "name": f"черновик-{n + 1}.svg", "content_type": "image/svg+xml", "size": None})
            cover = None
            if "palette" in data:
                cover = put(f"posts/{data['slug']}-cover.svg", painting_svg(data["title"][:28], data["palette"], 80 + i))
            post = Post(
                author_id=users[data["author"]].id, kind=data["kind"], title=data["title"],
                slug=unique_slug(db, Post.slug, data["slug"]),
                excerpt=data["excerpt"], content_md=data["content_md"], cover_url=cover, attachments=attachments, tags=[],
                opus_id=opuses[data["opus"]].id if data.get("opus") else None,
                view_count=rng.randint(20, 400), created_at=now - timedelta(days=data["days"], hours=rng.randint(0, 20)),
            )
            db.add(post)
            posts[data["slug"]] = post
        db.flush()

        # Channel posts: a line or two, sometimes a photo of the manuscript
        for i, (author, days, text, image) in enumerate(CHANNEL):
            attachments = []
            if image is not None:
                url = put(f"channel/{author}-{i}.svg", painting_svg(f"draft {i + 1}", image + 3, 90 + i))
                attachments.append({"url": url, "name": f"черновик-{i + 1}.svg", "content_type": "image/svg+xml", "size": None})
            db.add(Post(
                author_id=users[author].id, kind="note", title="", content_md=text, attachments=attachments, tags=[],
                slug=unique_slug(db, Post.slug, f"{author}-zapis-{i + 1}"),
                view_count=rng.randint(10, 120), created_at=now - timedelta(days=days),
            ))
        db.flush()

        for i, (author, kind, title, description, url, file_kind) in enumerate(MATERIALS):
            file = None
            if file_kind == "notes":
                file = {"url": put(f"materials/{author}-{i}.pdf", score_pdf("Harmony", "notes", "", ["Pno."], 2, seed=90 + i)),
                        "name": "garmoniya-konspekt.pdf", "content_type": "application/pdf", "size": None}
            elif file_kind == "parts":
                file = {"url": put(f"materials/{author}-{i}.pdf", score_pdf("Piano Trio - parts", "Vln. / Vc. / Pno.", "Allegro con brio", ["Vln.", "Vc."], 3, seed=95)),
                        "name": "trio-partii.pdf", "content_type": "application/pdf", "size": None}
            db.add(Material(
                author_id=users[author].id, kind=kind, title=title, description=description, url=url, file=file,
                position=i, created_at=now - timedelta(days=10 - i),
            ))

        created = []
        for i, ((kind, slug), author, ts, text, reply_to) in enumerate(COMMENTS):
            target = {"opus_id": opuses[slug].id} if kind == "opus" else {"post_id": posts[slug].id}
            comment = Comment(
                author_id=users[author].id, timestamp_marker=ts, content_md=text,
                parent_id=created[reply_to].id if reply_to is not None else None,
                created_at=now - timedelta(hours=40 - i * 5), **target,
            )
            db.add(comment)
            db.flush()
            created.append(comment)

        for author, title, slug, year, description, items in COLLECTIONS:
            db.add(Collection(
                author_id=users[author].id, title=title, slug=slug, year=year, description=description,
                items=[CollectionItem(opus_id=opuses[s].id, position=n) for n, s in enumerate(items)],
            ))
        db.commit()
        print(f"Seeded {len(USERS)} authors, {len(OPUSES)} opuses, {len(POSTS)} posts, {len(COMMENTS)} comments.")
        print(f"Demo accounts: {', '.join(u['username'] for u in USERS)} / {PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Demo content (fictional authors), created in the shadow by default")
    parser.add_argument("--visible", action="store_true", help="show the demo authors on the site")
    seed(parser.parse_args().visible)
