"""plan versions itinerary

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-23 17:17:58.248131
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0004'
down_revision: str | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('plan_versions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('trip_id', sa.Uuid(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('parent_version', sa.Integer(), nullable=True),
    sa.Column('created_by', sa.String(length=16), nullable=False),
    sa.Column('planner', sa.String(length=40), nullable=True),
    sa.Column('reason', sa.Text(), server_default='', nullable=False),
    sa.Column('explanation', sa.Text(), server_default='', nullable=False),
    sa.Column('warnings', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
    sa.Column('diff', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("created_by IN ('planner', 'user', 'system')", name=op.f('ck_plan_versions_created_by_valid')),
    sa.CheckConstraint('parent_version IS NULL OR parent_version < version', name=op.f('ck_plan_versions_parent_before')),
    sa.CheckConstraint('version >= 1', name=op.f('ck_plan_versions_version_positive')),
    sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], name=op.f('fk_plan_versions_trip_id_trips'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_plan_versions')),
    sa.UniqueConstraint('trip_id', 'version', name=op.f('uq_plan_versions_trip_id_version'))
    )
    op.create_index(op.f('ix_plan_versions_trip_id'), 'plan_versions', ['trip_id'], unique=False)
    op.create_table('itinerary_days',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('plan_version_id', sa.Uuid(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('stop_seq', sa.SmallInteger(), nullable=False),
    sa.Column('timezone', sa.String(length=64), nullable=False),
    sa.Column('capacity_minutes', sa.Integer(), server_default='0', nullable=False),
    sa.Column('notes', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
    sa.ForeignKeyConstraint(['plan_version_id'], ['plan_versions.id'], name=op.f('fk_itinerary_days_plan_version_id_plan_versions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_itinerary_days')),
    sa.UniqueConstraint('plan_version_id', 'date', name=op.f('uq_itinerary_days_plan_version_id_date'))
    )
    op.create_table('itinerary_items',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('day_id', sa.Uuid(), nullable=False),
    sa.Column('item_key', sa.Uuid(), nullable=False),
    sa.Column('position', sa.SmallInteger(), nullable=False),
    sa.Column('kind', sa.String(length=16), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('place_id', sa.String(length=300), nullable=True),
    sa.Column('booking_id', sa.Uuid(), nullable=True),
    sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('locked', sa.Boolean(), nullable=False),
    sa.Column('weather_sensitive', sa.Boolean(), nullable=False),
    sa.Column('source', sa.String(length=16), nullable=False),
    sa.Column('why', sa.Text(), server_default='', nullable=False),
    sa.CheckConstraint("kind <> 'place' OR place_id IS NOT NULL", name=op.f('ck_itinerary_items_place_has_id')),
    sa.CheckConstraint("kind IN ('place', 'booking', 'transfer', 'meal', 'custom', 'free')", name=op.f('ck_itinerary_items_kind_valid')),
    sa.CheckConstraint("source IN ('planner', 'user', 'booking')", name=op.f('ck_itinerary_items_source_valid')),
    sa.CheckConstraint('ends_at >= starts_at', name=op.f('ck_itinerary_items_times_ordered')),
    sa.ForeignKeyConstraint(['day_id'], ['itinerary_days.id'], name=op.f('fk_itinerary_items_day_id_itinerary_days'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_itinerary_items')),
    sa.UniqueConstraint('day_id', 'item_key', name=op.f('uq_itinerary_items_day_id_item_key'))
    )
    op.create_index(op.f('ix_itinerary_items_day_id'), 'itinerary_items', ['day_id'], unique=False)
    op.create_index(op.f('ix_itinerary_items_item_key'), 'itinerary_items', ['item_key'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_itinerary_items_item_key'), table_name='itinerary_items')
    op.drop_index(op.f('ix_itinerary_items_day_id'), table_name='itinerary_items')
    op.drop_table('itinerary_items')
    op.drop_table('itinerary_days')
    op.drop_index(op.f('ix_plan_versions_trip_id'), table_name='plan_versions')
    op.drop_table('plan_versions')
