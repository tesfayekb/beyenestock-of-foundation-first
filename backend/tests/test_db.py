import db


class BrokenTable:
    def upsert(self, *args, **kwargs):
        raise RuntimeError("supabase unreachable")

    def insert(self, *args, **kwargs):
        raise RuntimeError("supabase unreachable")


class BrokenClient:
    def table(self, _name):
        return BrokenTable()


def test_write_health_status_returns_false_on_exception(monkeypatch):
    monkeypatch.setattr(db, "get_client", lambda: BrokenClient())
    assert db.write_health_status("svc", "healthy") is False


def test_write_audit_log_returns_false_on_exception(monkeypatch):
    monkeypatch.setattr(db, "get_client", lambda: BrokenClient())
    assert db.write_audit_log("test.action") is False
