"""Fix Evidence.metadata reserved name — no schema change needed

The SQLAlchemy model attribute was renamed from 'metadata' to
'evidence_metadata'.  The underlying DB column name was always 'metadata'
(now made explicit via Column("metadata", Text)), so this migration is a
no-op for the database schema.

We keep this migration in the chain so the revision history documents the
code-level change and prevents autogenerate from trying to rename the column
in future runs.

Revision ID: c3f5e8a1d902
Revises: b2e4f1a9c3d7
Create Date: 2026-03-23 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c3f5e8a1d902'
down_revision = 'b2e4f1a9c3d7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The 'evidences.metadata' column already exists in the database with
    # the correct name.  The only change was a Python-level rename of the
    # ORM attribute (metadata → evidence_metadata) with an explicit
    # column mapping: Column("metadata", Text).
    # No DDL alteration is required.
    pass


def downgrade() -> None:
    # Equally, no DDL change to reverse.
    pass
