"""initial schema: trips, members, places (PostGIS), expenses, shares, transfers

Revision ID: 0001
Revises: 
Create Date: 2026-11-23 10:56:03.487941
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql

revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostGIS is shared by the whole database, so downgrade leaves it installed.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_geospatial_table('places',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('provider', sa.String(length=40), nullable=False),
    sa.Column('provider_place_id', sa.String(length=255), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('location', Geography(geometry_type='POINT', srid=4326, dimension=2, spatial_index=False, from_text='ST_GeogFromText', name='geography', nullable=False), nullable=False),
    sa.Column('categories', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_places')),
    sa.UniqueConstraint('provider', 'provider_place_id', name=op.f('uq_places_provider_provider_place_id'))
    )
    op.create_geospatial_index('idx_places_location', 'places', ['location'], unique=False, postgresql_using='gist', postgresql_ops={})
    op.create_table('trips',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('origin', sa.String(length=120), nullable=False),
    sa.Column('destination', sa.String(length=120), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=False),
    sa.Column('travellers', sa.Integer(), nullable=False),
    sa.Column('interests', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
    sa.Column('pace', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("pace IN ('relaxed', 'balanced', 'packed')", name=op.f('ck_trips_pace_valid')),
    sa.CheckConstraint('end_date >= start_date', name=op.f('ck_trips_dates_ordered')),
    sa.CheckConstraint('travellers BETWEEN 1 AND 20', name=op.f('ck_trips_travellers_range')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_trips'))
    )
    op.create_table('trip_members',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('trip_id', sa.Uuid(), nullable=False),
    sa.Column('display_name', sa.String(length=80), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], name=op.f('fk_trip_members_trip_id_trips'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_trip_members')),
    sa.UniqueConstraint('trip_id', 'display_name', name=op.f('uq_trip_members_trip_id_display_name'))
    )
    op.create_index(op.f('ix_trip_members_trip_id'), 'trip_members', ['trip_id'], unique=False)
    op.create_table('expenses',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('trip_id', sa.Uuid(), nullable=False),
    sa.Column('description', sa.String(length=255), nullable=False),
    sa.Column('amount', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('payer_id', sa.Uuid(), nullable=False),
    sa.Column('incurred_on', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('amount > 0', name=op.f('ck_expenses_amount_positive')),
    sa.CheckConstraint('char_length(currency) = 3', name=op.f('ck_expenses_currency_iso')),
    sa.ForeignKeyConstraint(['payer_id'], ['trip_members.id'], name=op.f('fk_expenses_payer_id_trip_members')),
    sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], name=op.f('fk_expenses_trip_id_trips'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_expenses'))
    )
    op.create_index(op.f('ix_expenses_payer_id'), 'expenses', ['payer_id'], unique=False)
    op.create_index(op.f('ix_expenses_trip_id'), 'expenses', ['trip_id'], unique=False)
    op.create_table('transfers',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('trip_id', sa.Uuid(), nullable=False),
    sa.Column('sender_id', sa.Uuid(), nullable=False),
    sa.Column('recipient_id', sa.Uuid(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('sent_on', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('amount > 0', name=op.f('ck_transfers_amount_positive')),
    sa.CheckConstraint('char_length(currency) = 3', name=op.f('ck_transfers_currency_iso')),
    sa.CheckConstraint('sender_id <> recipient_id', name=op.f('ck_transfers_distinct_parties')),
    sa.ForeignKeyConstraint(['recipient_id'], ['trip_members.id'], name=op.f('fk_transfers_recipient_id_trip_members')),
    sa.ForeignKeyConstraint(['sender_id'], ['trip_members.id'], name=op.f('fk_transfers_sender_id_trip_members')),
    sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], name=op.f('fk_transfers_trip_id_trips'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_transfers'))
    )
    op.create_index(op.f('ix_transfers_trip_id'), 'transfers', ['trip_id'], unique=False)
    op.create_table('expense_shares',
    sa.Column('expense_id', sa.Uuid(), nullable=False),
    sa.Column('member_id', sa.Uuid(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.CheckConstraint('amount >= 0', name=op.f('ck_expense_shares_amount_non_negative')),
    sa.ForeignKeyConstraint(['expense_id'], ['expenses.id'], name=op.f('fk_expense_shares_expense_id_expenses'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['member_id'], ['trip_members.id'], name=op.f('fk_expense_shares_member_id_trip_members')),
    sa.PrimaryKeyConstraint('expense_id', 'member_id', name=op.f('pk_expense_shares'))
    )
    op.create_index(op.f('ix_expense_shares_member_id'), 'expense_shares', ['member_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_expense_shares_member_id'), table_name='expense_shares')
    op.drop_table('expense_shares')
    op.drop_index(op.f('ix_transfers_trip_id'), table_name='transfers')
    op.drop_table('transfers')
    op.drop_index(op.f('ix_expenses_trip_id'), table_name='expenses')
    op.drop_index(op.f('ix_expenses_payer_id'), table_name='expenses')
    op.drop_table('expenses')
    op.drop_index(op.f('ix_trip_members_trip_id'), table_name='trip_members')
    op.drop_table('trip_members')
    op.drop_table('trips')
    op.drop_geospatial_index('idx_places_location', table_name='places', postgresql_using='gist', column_name='location')
    op.drop_geospatial_table('places')
