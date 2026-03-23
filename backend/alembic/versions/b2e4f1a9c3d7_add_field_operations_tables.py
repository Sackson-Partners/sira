"""Add field operations tables: organizations, vehicles, drivers, routes, assignments, checkpoints, sync_logs, audit_logs

Revision ID: b2e4f1a9c3d7
Revises: 04440dcecb17
Create Date: 2026-03-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'b2e4f1a9c3d7'
down_revision = '04440dcecb17'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ----------------------------------------------------------------
    # organizations
    # ----------------------------------------------------------------
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('type', sa.String(50), nullable=False, server_default='logistics'),
        sa.Column('country_code', sa.String(2), nullable=False, server_default='GH'),
        sa.Column('timezone', sa.String(50), nullable=False, server_default='Africa/Accra'),
        sa.Column('plan', sa.String(20), nullable=False, server_default='starter'),
        sa.Column('settings', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )
    op.create_index('ix_organizations_id', 'organizations', ['id'])
    op.create_index('ix_organizations_slug', 'organizations', ['slug'])

    # ----------------------------------------------------------------
    # vehicles
    # ----------------------------------------------------------------
    op.create_table(
        'vehicles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('plate_number', sa.String(50), nullable=False),
        sa.Column('vehicle_type', sa.String(30), nullable=False, server_default='truck'),
        sa.Column('make', sa.String(100), nullable=True),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('capacity_tons', sa.Float(), nullable=True),
        sa.Column('iot_device_id', sa.String(100), nullable=True),
        sa.Column('iot_device_type', sa.String(30), nullable=True),
        sa.Column('last_known_lat', sa.Float(), nullable=True),
        sa.Column('last_known_lng', sa.Float(), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='available'),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('iot_device_id'),
    )
    op.create_index('ix_vehicles_id', 'vehicles', ['id'])
    op.create_index('ix_vehicles_organization_id', 'vehicles', ['organization_id'])
    op.create_index('ix_vehicles_iot_device_id', 'vehicles', ['iot_device_id'])

    # ----------------------------------------------------------------
    # drivers
    # ----------------------------------------------------------------
    op.create_table(
        'drivers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('license_number', sa.String(100), nullable=False),
        sa.Column('license_class', sa.String(20), nullable=True),
        sa.Column('license_expiry', sa.Date(), nullable=True),
        sa.Column('current_vehicle_id', sa.Integer(), nullable=True),
        sa.Column('performance_score', sa.Float(), nullable=False, server_default='100.0'),
        sa.Column('total_trips', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_km', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['current_vehicle_id'], ['vehicles.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index('ix_drivers_id', 'drivers', ['id'])
    op.create_index('ix_drivers_user_id', 'drivers', ['user_id'])
    op.create_index('ix_drivers_organization_id', 'drivers', ['organization_id'])

    # ----------------------------------------------------------------
    # routes
    # ----------------------------------------------------------------
    op.create_table(
        'routes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('origin', sa.String(255), nullable=False),
        sa.Column('origin_lat', sa.Float(), nullable=False),
        sa.Column('origin_lng', sa.Float(), nullable=False),
        sa.Column('destination', sa.String(255), nullable=False),
        sa.Column('destination_lat', sa.Float(), nullable=False),
        sa.Column('destination_lng', sa.Float(), nullable=False),
        sa.Column('waypoints', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('distance_km', sa.Float(), nullable=True),
        sa.Column('estimated_hours', sa.Float(), nullable=True),
        sa.Column('risk_profile', sa.String(20), nullable=False, server_default='low'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_routes_id', 'routes', ['id'])
    op.create_index('ix_routes_organization_id', 'routes', ['organization_id'])

    # ----------------------------------------------------------------
    # assignments
    # ----------------------------------------------------------------
    op.create_table(
        'assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('shipment_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('vehicle_id', sa.Integer(), nullable=False),
        sa.Column('assigned_by', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='pending'),
        sa.Column('driver_accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['shipment_id'], ['shipments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['driver_id'], ['users.id']),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id']),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_assignments_id', 'assignments', ['id'])
    op.create_index('ix_assignments_shipment_id', 'assignments', ['shipment_id'])
    op.create_index('ix_assignments_driver_id', 'assignments', ['driver_id'])
    op.create_index('ix_assignments_vehicle_id', 'assignments', ['vehicle_id'])

    # ----------------------------------------------------------------
    # checkpoints
    # ----------------------------------------------------------------
    op.create_table(
        'checkpoints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('shipment_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('checkpoint_type', sa.String(50), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('accuracy_meters', sa.Float(), nullable=True),
        sa.Column('altitude_m', sa.Float(), nullable=True),
        sa.Column('location_name', sa.String(255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('verified_by', sa.Integer(), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('offline_queued', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('device_id', sa.String(100), nullable=True),
        sa.Column('client_event_id', sa.String(100), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['shipment_id'], ['shipments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('client_event_id'),
    )
    op.create_index('ix_checkpoints_id', 'checkpoints', ['id'])
    op.create_index('ix_checkpoints_shipment_id', 'checkpoints', ['shipment_id'])
    op.create_index('ix_checkpoints_organization_id', 'checkpoints', ['organization_id'])
    op.create_index('ix_checkpoints_user_id', 'checkpoints', ['user_id'])

    # ----------------------------------------------------------------
    # sync_logs
    # ----------------------------------------------------------------
    op.create_table(
        'sync_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.String(100), nullable=False),
        sa.Column('sync_type', sa.String(20), nullable=False, server_default='batch'),
        sa.Column('events_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('conflicts_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('response', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sync_logs_id', 'sync_logs', ['id'])
    op.create_index('ix_sync_logs_user_id', 'sync_logs', ['user_id'])
    op.create_index('ix_sync_logs_device_id', 'sync_logs', ['device_id'])
    op.create_index('ix_sync_logs_organization_id', 'sync_logs', ['organization_id'])

    # ----------------------------------------------------------------
    # audit_logs
    # ----------------------------------------------------------------
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('old_value', sa.JSON(), nullable=True),
        sa.Column('new_value', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(512), nullable=True),
        sa.Column('device_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'])
    op.create_index('ix_audit_logs_organization_id', 'audit_logs', ['organization_id'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])

    # ----------------------------------------------------------------
    # Seed: default organization (id=1) for single-tenant compat
    # ----------------------------------------------------------------
    op.execute("""
        INSERT INTO organizations (id, name, slug, type, country_code, timezone, plan, settings, is_active)
        VALUES (1, 'Default Organization', 'default', 'logistics', 'GH', 'Africa/Accra', 'enterprise', '{}', true)
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('sync_logs')
    op.drop_table('checkpoints')
    op.drop_table('assignments')
    op.drop_table('routes')
    op.drop_table('drivers')
    op.drop_table('vehicles')
    op.drop_table('organizations')
