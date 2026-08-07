"""
会话归档功能测试 — 模型字段 + 归档 curd 逻辑。

归档 curd 依赖真实数据库 Session，这里用 SQLite 内存库 + 真实 SQLModel 元数据验证，
避免依赖生产 PostgreSQL。
运行方式（在项目根目录）：
    python -m pytest tests/test_chat_archive.py -v
"""

import os
import sys

_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from apps.chat.models.chat_model import Chat, ArchiveChat  # noqa: E402
from apps.chat.curd.chat import archive_chat_with_user, list_chats  # noqa: E402


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Chat.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    s = Session()

    _make_user = lambda i: type("U", (), {"id": i, "oid": 1})()  # noqa: E731
    s.add(Chat(id=1, create_by=1, oid=1, brief="active-a", engine_type="chat"))
    s.add(Chat(id=2, create_by=1, oid=1, brief="active-b", engine_type="chat"))
    s.add(Chat(id=3, create_by=1, oid=1, brief="archived-c", engine_type="chat", is_archived=True))
    s.add(Chat(id=4, create_by=2, oid=1, brief="other-user", engine_type="chat"))
    s.commit()
    s._user = _make_user  # attach helper
    yield s
    s.close()


def make_user(id_):
    return type("U", (), {"id": id_, "oid": 1})()


def test_archive_chat_flag_default_false():
    assert Chat.__fields__["is_archived"].default is False
    assert ArchiveChat().is_archived is True


def test_list_chats_filters_archived(session):
    active = list_chats(session, make_user(1), archived=False)
    assert {c.brief for c in active} == {"active-a", "active-b"}

    archived = list_chats(session, make_user(1), archived=True)
    assert {c.brief for c in archived} == {"archived-c"}

    all_chats = list_chats(session, make_user(1), archived=None)
    assert len(all_chats) == 3


def test_list_chats_scoped_by_user(session):
    active = list_chats(session, make_user(2), archived=False)
    assert {c.brief for c in active} == {"other-user"}


def test_archive_then_unarchive(session):
    chat = next(c for c in list_chats(session, make_user(1), archived=False) if c.brief == "active-a")
    assert archive_chat_with_user(session, make_user(1), chat.id, True) is True
    assert archive_chat_with_user(session, make_user(1), chat.id, False) is False

    active = list_chats(session, make_user(1), archived=False)
    assert "active-a" in {c.brief for c in active}


def test_archive_raises_for_other_user(session):
    chat = next(c for c in list_chats(session, make_user(1), archived=False) if c.brief == "active-a")
    with pytest.raises(Exception, match="not Owned"):
        archive_chat_with_user(session, make_user(2), chat.id, True)