"""add token_version, refresh_token_jti, audit_logs

Adds security columns to support:
  H2  — token_version: invalidates access tokens after password change
  L1  — refresh_token_jti: refresh token rotation to detect reuse
  L2  — audit_logs table: tamper-evident record of security-relevant events

Revision ID: f6e9d1c4b802
Revises: d4a7b2c8e501
Create Date: 2026-04-01

"""
from alembic import op
import sqlalchemy as sa

revision = 'f6e9d1c4b802'
down_revision = 'd4a7b2c8e501'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users table: security columns ────────────────────────────────────────
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(
            sa.Column(
                'token_version',
                sa.Integer(),
                nullable=False,
                server_default=sa.text('0'),
            )
        )
        batch_op.add_column(
            sa.Column('refresh_token_jti', sa.String(36), nullable=True)
        )

    # ── audit_logs table ──────────────────────────────────────────────────────
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            'timestamp',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('resource', sa.String(255), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('detail', sa.Text(), nullable=True),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_event_type', 'audit_logs', ['event_type'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])


def downgrade() -> None:
    op.drop_index('ix_audit_logs_timestamp', table_name='audit_logs')
    op.drop_index('ix_audit_logs_event_type', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user_id', table_name='audit_logs')
    op.drop_table('audit_logs')

    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('refresh_token_jti')
        batch_op.drop_column('token_version')
