from repositories import UserRepository
from models import UserInfo


class UserService:
    def __init__(self, db: sessio):
        self.repo = repo

    def upsert_user(
        self,
        user_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ):
        user = UserInfo(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        self.repo.upsert(user)

    def get_stats(self, user_id: int):
        return self.repo.get_stats(user_id)
