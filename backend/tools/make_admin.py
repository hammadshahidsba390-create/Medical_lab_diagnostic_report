"""Give an existing user the administrator role.

Usage (from backend/):  python -m tools.make_admin someone@example.com
"""
import sys

from app.db.session import get_sessionmaker
from app.services.auth_service import promote_to_admin


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m tools.make_admin EMAIL")
    with get_sessionmaker()() as db:
        user = promote_to_admin(db, sys.argv[1])
        print(f"{user.email} is now an administrator.")


if __name__ == "__main__":
    main()
