"""transport options

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-24 12:33:47.854886
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0005'
down_revision: str | None = '0004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('transport_options',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('trip_id', sa.Uuid(), nullable=False),
    sa.Column('search_id', sa.Uuid(), nullable=False),
    sa.Column('direction', sa.String(length=10), nullable=False),
    sa.Column('provider', sa.String(length=40), nullable=False),
    sa.Column('offer_id', sa.String(length=300), nullable=False),
    sa.Column('offer', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('total_amount', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('stops', sa.SmallInteger(), nullable=False),
    sa.Column('departs_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('arrives_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('selected_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name=op.f('ck_transport_options_currency_iso')),
    sa.CheckConstraint("direction IN ('outbound', 'return')", name=op.f('ck_transport_options_direction_valid')),
    sa.CheckConstraint('expires_at > fetched_at', name=op.f('ck_transport_options_ttl_positive')),
    sa.CheckConstraint('stops >= 0', name=op.f('ck_transport_options_stops_non_negative')),
    sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], name=op.f('fk_transport_options_trip_id_trips'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_transport_options')),
    sa.UniqueConstraint('trip_id', 'search_id', 'offer_id', name=op.f('uq_transport_options_trip_id_search_id_offer_id'))
    )
    op.create_index(op.f('ix_transport_options_search_id'), 'transport_options', ['search_id'], unique=False)
    op.create_index(op.f('ix_transport_options_trip_id'), 'transport_options', ['trip_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_transport_options_trip_id'), table_name='transport_options')
    op.drop_index(op.f('ix_transport_options_search_id'), table_name='transport_options')
    op.drop_table('transport_options')
