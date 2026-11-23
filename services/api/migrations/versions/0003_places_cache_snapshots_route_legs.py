"""places cache snapshots route legs

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-23 16:39:01.624190
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Mirrors PlaceRow.__table_args__ (autogenerate does not detect CHECKs on existing tables).
PLACE_CHECKS = {
    'rating_range': 'rating IS NULL OR rating BETWEEN 0 AND 5',
    'price_level_range': 'price_level IS NULL OR price_level BETWEEN 1 AND 4',
    'visit_range': 'typical_visit_minutes BETWEEN 5 AND 600',
}


def upgrade() -> None:
    op.create_table('provider_snapshots',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('provider', sa.String(length=40), nullable=False),
    sa.Column('kind', sa.String(length=40), nullable=False),
    sa.Column('request_hash', sa.String(length=64), nullable=False),
    sa.Column('request', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('result_ids', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
    sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('expires_at > fetched_at', name=op.f('ck_provider_snapshots_ttl_positive')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_provider_snapshots')),
    sa.UniqueConstraint('provider', 'kind', 'request_hash', name=op.f('uq_provider_snapshots_provider_kind_request_hash'))
    )
    op.create_index(op.f('ix_provider_snapshots_expires_at'), 'provider_snapshots', ['expires_at'], unique=False)
    op.create_table('route_legs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('provider', sa.String(length=40), nullable=False),
    sa.Column('mode', sa.String(length=8), nullable=False),
    sa.Column('origin_id', sa.String(length=300), nullable=False),
    sa.Column('destination_id', sa.String(length=300), nullable=False),
    sa.Column('duration_s', sa.Integer(), nullable=False),
    sa.Column('distance_m', sa.Integer(), nullable=False),
    sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("mode IN ('walk', 'drive')", name=op.f('ck_route_legs_mode_valid')),
    sa.CheckConstraint('duration_s >= 0 AND distance_m >= 0', name=op.f('ck_route_legs_non_negative')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_route_legs')),
    sa.UniqueConstraint('provider', 'mode', 'origin_id', 'destination_id', name=op.f('uq_route_legs_provider_mode_origin_id_destination_id'))
    )
    op.add_column('places', sa.Column('city', sa.String(length=120), nullable=True))
    op.add_column('places', sa.Column('opening_hours', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('places', sa.Column('rating', sa.Float(), nullable=True))
    op.add_column('places', sa.Column('rating_count', sa.Integer(), nullable=True))
    op.add_column('places', sa.Column('price_level', sa.SmallInteger(), nullable=True))
    op.add_column('places', sa.Column('wheelchair_accessible', sa.Boolean(), nullable=True))
    op.add_column('places', sa.Column('timezone', sa.String(length=64), server_default='UTC', nullable=False))
    op.add_column('places', sa.Column('typical_visit_minutes', sa.SmallInteger(), server_default='60', nullable=False))
    op.add_column('places', sa.Column('fetched_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    for name, condition in PLACE_CHECKS.items():
        op.create_check_constraint(op.f(f'ck_places_{name}'), 'places', condition)


def downgrade() -> None:
    for name in PLACE_CHECKS:
        op.drop_constraint(op.f(f'ck_places_{name}'), 'places', type_='check')
    op.drop_column('places', 'fetched_at')
    op.drop_column('places', 'typical_visit_minutes')
    op.drop_column('places', 'timezone')
    op.drop_column('places', 'wheelchair_accessible')
    op.drop_column('places', 'price_level')
    op.drop_column('places', 'rating_count')
    op.drop_column('places', 'rating')
    op.drop_column('places', 'opening_hours')
    op.drop_column('places', 'city')
    op.drop_table('route_legs')
    op.drop_index(op.f('ix_provider_snapshots_expires_at'), table_name='provider_snapshots')
    op.drop_table('provider_snapshots')
