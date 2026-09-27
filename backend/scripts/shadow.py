"""Put accounts "in the shadow" (hidden from the site with everything they made, but kept in the database) or bring them back.

    python -m scripts.shadow hide lev_orlovsky kostya_theory maria_viola
    python -m scripts.shadow show lev_orlovsky
    python -m scripts.shadow list
"""
import argparse

from sqlalchemy import select

from allegro_common.db import SessionLocal
from allegro_common.models import User


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=["hide", "show", "list"])
    parser.add_argument("usernames", nargs="*")
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.action == "list":
            for user in db.scalars(select(User).order_by(User.username)):
                print(f"{'в тени ' if user.is_hidden else 'виден  '} {user.username:24} {user.display_name}")
            return
        if not args.usernames:
            parser.error("укажите имена пользователей")
        for username in args.usernames:
            user = db.scalar(select(User).where(User.username == username.lower()))
            if not user:
                print(f"нет такого пользователя: {username}")
                continue
            user.is_hidden = args.action == "hide"
            print(f"{username}: {'в тени' if user.is_hidden else 'виден'}")
        db.commit()


if __name__ == "__main__":
    main()
