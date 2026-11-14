from sqlalchemy import select

from open_scholar.database.models import Notification, Opportunity, User
from open_scholar.database.repository import UserRepository
from open_scholar.database.session import init_db, make_engine, make_session_factory


def _session():
    engine = make_engine("sqlite:///:memory:")
    init_db(engine)
    return make_session_factory(engine)()


def test_user_isolation_and_profile_roundtrip():
    s = _session()
    repo = UserRepository(s)
    a = repo.get_or_create_by_telegram(1, "a")
    b = repo.get_or_create_by_telegram(2, "b")
    repo.save_profile(a, {"x": 1})
    s.commit()
    assert repo.get_or_create_by_telegram(1).id == a.id
    assert a.profile.data == {"x": 1} and b.profile is None


def test_delete_user_cascades():
    s = _session()
    repo = UserRepository(s)
    u = repo.get_or_create_by_telegram(5)
    opp = Opportunity(title="t", fingerprint="f")
    s.add(opp)
    s.flush()
    s.add(Notification(user_id=u.id, opportunity_id=opp.id))
    repo.save_profile(u, {})
    s.commit()
    repo.delete_user(u)
    s.commit()
    assert s.scalars(select(User)).all() == []
    assert s.scalars(select(Notification)).all() == []
    assert s.scalars(select(Opportunity)).all() != []  # shared data survives
