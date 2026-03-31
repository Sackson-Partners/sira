"""Add shipments table (required by assignments and checkpoints foreign keys)

Revision ID: a9f3c2e8b501
Revises: 04440dcecb17
Create Date: 2026-03-31 00:00:00.000000

Note: The Shipment model has optional FKs to corridors, vessels, and ports
which are not yet in the migration chain.  Those columns are created as plain
integers here; the FK constraints will be added when those tables are
introduced in a later migration.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a9f3c2e8b501'
down_revision = '04440dcecb17'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'shipments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('shipment_ref', sa.String(50), nullable=False),
        # corridor_id / vessel_id / port FKs deferred — those tables not yet migrated
        sa.Column('corridor_id', sa.Integer(), nullable=True),
        sa.Column('vessel_id', sa.Integer(), nullable=True),
        sa.Column('cargo_type', sa.String(100), nullable=False),
        sa.Column('cargo_grade', sa.String(100), nullable=True),
        sa.Column('volume_tonnes', sa.Float(), nullable=True),
        sa.Column('bill_of_lading', sa.String(100), nullable=True),
        sa.Column('origin', sa.String(255), nullable=False),
        sa.Column('destination', sa.String(255), nullable=False),
        sa.Column('origin_port_id', sa.Integer(), nullable=True),
        sa.Column('destination_port_id', sa.Integer(), nullable=True),
        sa.Column('laycan_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('laycan_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(50), nullable=True, server_default='planned'),
        sa.Column('current_leg', sa.String(100), nullable=True),
        sa.Column('current_mode', sa.String(50), nullable=True),
        sa.Column('eta_destination', sa.DateTime(timezone=True), nullable=True),
        sa.Column('eta_confidence', sa.Float(), nullable=True),
        sa.Column('eta_updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('demurrage_risk_score', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('demurrage_exposure_usd', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('demurrage_rate_usd', sa.Float(), nullable=True),
        sa.Column('demurrage_days', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('loading_started', sa.DateTime(timezone=True), nullable=True),
        sa.Column('loading_completed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('departed_origin', sa.DateTime(timezone=True), nullable=True),
        sa.Column('arrived_destination', sa.DateTime(timezone=True), nullable=True),
        sa.Column('discharge_started', sa.DateTime(timezone=True), nullable=True),
        sa.Column('discharge_completed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('shipper', sa.String(255), nullable=True),
        sa.Column('receiver', sa.String(255), nullable=True),
        sa.Column('freight_forwarder', sa.String(255), nullable=True),
        sa.Column('insurance_ref', sa.String(100), nullable=True),
        sa.Column('custody_seal_id', sa.String(100), nullable=True),
        sa.Column('custody_status', sa.String(50), nullable=True, server_default='intact'),
        sa.Column('freight_cost', sa.Float(), nullable=True),
        sa.Column('insurance_cost', sa.Float(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('shipment_ref'),
    )
    op.create_index('ix_shipments_id', 'shipments', ['id'])
    op.create_index('ix_shipments_shipment_ref', 'shipments', ['shipment_ref'])
    op.create_index('ix_shipments_status', 'shipments', ['status'])


def downgrade() -> None:
    op.drop_index('ix_shipments_status', 'shipments')
    op.drop_index('ix_shipments_shipment_ref', 'shipments')
    op.drop_index('ix_shipments_id', 'shipments')
    op.drop_table('shipments')
