from listingjet.models.audit_log import AuditLog
from listingjet.models.outbox import Outbox
from listingjet.models.user import User


def _indexed_columns(model) -> set[str]:
    cols = set()
    for idx in model.__table__.indexes:
        cols.update(c.name for c in idx.columns)
    return cols


def test_tenant_id_is_indexed_on_hot_tables():
    for model in (User, Outbox, AuditLog):
        assert "tenant_id" in _indexed_columns(model), model.__tablename__
