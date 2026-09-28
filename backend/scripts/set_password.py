"""Set a new password for an account. The password is typed in, not passed as an argument
(so it doesn't stay in the shell history).

    python -m scripts.set_password allegro_cantabile
"""
import argparse
import getpass

from sqlalchemy import select

import allegro.models  # noqa: F401  (all tables, for relationships)
from allegro.core.db import SessionLocal
from allegro.core.security import hash_password
from allegro.modules.accounts.models import User

MIN_LENGTH = 12


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("username")
    args = parser.parse_args()

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == args.username.lower()))
        if not user:
            raise SystemExit(f"Нет пользователя {args.username}")
        password = getpass.getpass("Новый пароль: ")
        if len(password) < MIN_LENGTH:
            raise SystemExit(f"Слишком короткий: нужно не меньше {MIN_LENGTH} символов")
        if password in ("allegro-demo",) or password.lower() == user.username:
            raise SystemExit("Этот пароль известен посторонним — выберите другой")
        if getpass.getpass("Ещё раз: ") != password:
            raise SystemExit("Пароли не совпадают")
        user.password_hash = hash_password(password)
        db.commit()
        print(f"Пароль для {user.username} изменён")


if __name__ == "__main__":
    main()
