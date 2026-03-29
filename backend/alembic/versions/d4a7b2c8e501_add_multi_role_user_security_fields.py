"""add multi-role user security fields

Adds columns to the users table to support:
- Multi-organisation membership (organization_id FK)
- Account lockout (is_locked, failed_login_attempts, locked_until)
- Forced password change on first login (must_change_password)
- Audit trail fields (last_login_ip)
- Password reset flow (password_reset_token, password_reset_expires)

Revision ID: d4a7b2c8e501
Revises: c3f5e8a1d902
Create Date: 2026-03-29

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd4a7b2c8e501'
down_revision = 'c3f5e8a1d902'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use batch mode for SQLite compatibility (env.py handles render_as_batch)
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(
            sa.Column('organization_id', sa.Integer(),
                      sa.ForeignKey('organizations.id'),
                      nullable=True)
        )
        batch_op.add_column(
            sa.Column('is_locked', sa.Boolean(),
                      nullable=False, server_default=sa.text('false'))
        )
        batch_op.add_column(
            sa.Column('failed_login_attempts', sa.Integer(),
                      nullable=False, server_default=sa.text('0'))
        )
        batch_op.add_column(
            sa.Column('locked_until', sa.DateTime(timezone=True),
                      nullable=True)
        )
        batch_op.add_column(
            sa.Column('must_change_password', sa.Boolean(),
                      nullable=False, server_default=sa.text('false'))
        )
        batch_op.add_column(
            sa.Column('last_login_ip', sa.String(45),
                      nullable=True)
        )
        batch_op.add_column(
            sa.Column('password_reset_token', sa.String(255),
                      nullable=True)
        )
        batch_op.add_column(
            sa.Column('password_reset_expires', sa.DateTime(timezone=True),
                      nullable=True)
        )
        batch_op.create_index('ix_users_organization_id', ['organization_id'])


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_index('ix_users_organization_id')
        batch_op.drop_column('password_reset_expires')
        batch_op.drop_column('password_reset_token')
        batch_op.drop_column('last_login_ip')
        batch_op.drop_column('must_change_password')
        batch_op.drop_column('locked_until')
        batch_op.drop_column('failed_login_attempts')
        batch_op.drop_column('is_locked')
        batch_op.drop_column('organization_id')
