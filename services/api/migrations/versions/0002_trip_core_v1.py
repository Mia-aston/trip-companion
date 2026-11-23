"""trip core v1: CORE-001 trip contract, stops, constraints, bookings, users

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-23 11:59:52.687968
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Mirrors TripRow.__table_args__ (autogenerate does not detect CHECKs on existing tables).
TRIP_CHECKS = {
    'adults_range': 'adults BETWEEN 1 AND 20',
    'infants_per_adult': 'infants BETWEEN 0 AND adults',
    'party_size': 'adults + cardinality(children_ages) + infants <= 20',
    'day_window_ordered': 'day_end > day_start',
    'price_level_range': 'price_level BETWEEN 1 AND 4',
    'status_valid': "status IN ('draft', 'planned', 'active', 'done')",
    'mobility_valid': "mobility_needs IN ('none', 'limited_walking', 'wheelchair', 'stroller')",
    'base_currency_iso': "base_currency ~ '^[A-Z]{3}$'",
    'settlement_currency_iso': "settlement_currency ~ '^[A-Z]{3}$'",
    'budget_complete': '(budget_amount IS NULL) = (budget_currency IS NULL) AND (budget_amount IS NULL) = (budget_scope IS NULL)',
    'budget_scope_valid': "budget_scope IS NULL OR budget_scope IN ('per_trip', 'per_person')",
}


def upgrade() -> None:
    op.create_table('users',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('email', sa.String(length=320), nullable=True),
    sa.Column('display_name', sa.String(length=80), nullable=False),
    sa.Column('default_currency', sa.String(length=3), nullable=False),
    sa.Column('locale', sa.String(length=10), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("default_currency ~ '^[A-Z]{3}$'", name=op.f('ck_users_currency_iso')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email', name=op.f('uq_users_email'))
    )
    op.create_table('bookings',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('trip_id', sa.Uuid(), nullable=False),
    sa.Column('kind', sa.String(length=16), nullable=False),
    sa.Column('title', sa.String(length=120), nullable=False),
    sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('stop_seq', sa.SmallInteger(), nullable=True),
    sa.Column('location_name', sa.String(length=200), nullable=True),
    sa.Column('reference', sa.String(length=120), nullable=True),
    sa.Column('cost_amount', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('cost_currency', sa.String(length=3), nullable=True),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("cost_currency IS NULL OR cost_currency ~ '^[A-Z]{3}$'", name=op.f('ck_bookings_cost_currency_iso')),
    sa.CheckConstraint("kind IN ('flight', 'hotel', 'activity', 'transport')", name=op.f('ck_bookings_kind_valid')),
    sa.CheckConstraint("status IN ('confirmed', 'tentative', 'cancelled')", name=op.f('ck_bookings_status_valid')),
    sa.CheckConstraint('(cost_amount IS NULL) = (cost_currency IS NULL)', name=op.f('ck_bookings_cost_complete')),
    sa.CheckConstraint('ends_at >= starts_at', name=op.f('ck_bookings_times_ordered')),
    sa.CheckConstraint('stop_seq IS NULL OR stop_seq >= 0', name=op.f('ck_bookings_stop_seq_non_negative')),
    sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], name=op.f('fk_bookings_trip_id_trips'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bookings'))
    )
    op.create_index(op.f('ix_bookings_trip_id'), 'bookings', ['trip_id'], unique=False)
    op.create_table('trip_constraints',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('trip_id', sa.Uuid(), nullable=False),
    sa.Column('position', sa.SmallInteger(), server_default='0', nullable=False),
    sa.Column('kind', sa.String(length=16), nullable=False),
    sa.Column('hardness', sa.String(length=8), nullable=False),
    sa.Column('source', sa.String(length=16), nullable=False),
    sa.Column('locked', sa.Boolean(), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("hardness IN ('hard', 'soft')", name=op.f('ck_trip_constraints_hardness_valid')),
    sa.CheckConstraint("kind IN ('must_do', 'avoid', 'time_window')", name=op.f('ck_trip_constraints_kind_valid')),
    sa.CheckConstraint("source IN ('user', 'booking', 'system')", name=op.f('ck_trip_constraints_source_valid')),
    sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], name=op.f('fk_trip_constraints_trip_id_trips'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_trip_constraints'))
    )
    op.create_index(op.f('ix_trip_constraints_trip_id'), 'trip_constraints', ['trip_id'], unique=False)
    op.create_table('trip_stops',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('trip_id', sa.Uuid(), nullable=False),
    sa.Column('seq', sa.SmallInteger(), nullable=False),
    sa.Column('city', sa.String(length=120), nullable=False),
    sa.Column('nights', sa.SmallInteger(), nullable=False),
    sa.Column('timezone', sa.String(length=64), nullable=True),
    sa.Column('accommodation_area', sa.String(length=200), nullable=True),
    sa.Column('arrive_on', sa.Date(), nullable=False),
    sa.Column('leave_on', sa.Date(), nullable=False),
    sa.CheckConstraint('leave_on = arrive_on + nights', name=op.f('ck_trip_stops_dates_match_nights')),
    sa.CheckConstraint('nights BETWEEN 0 AND 60', name=op.f('ck_trip_stops_nights_range')),
    sa.CheckConstraint('seq >= 0', name=op.f('ck_trip_stops_seq_non_negative')),
    sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], name=op.f('fk_trip_stops_trip_id_trips'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_trip_stops')),
    sa.UniqueConstraint('trip_id', 'seq', name=op.f('uq_trip_stops_trip_id_seq'))
    )
    # --- trip_members: user link, role, currency; case-insensitive unique names ---
    op.add_column('trip_members', sa.Column('user_id', sa.Uuid(), nullable=True))
    op.add_column('trip_members', sa.Column('role', sa.String(length=16), server_default='owner', nullable=False))
    op.add_column('trip_members', sa.Column('currency_pref', sa.String(length=3), nullable=True))
    op.add_column('trip_members', sa.Column('position', sa.SmallInteger(), server_default='0', nullable=False))
    op.alter_column('trip_members', 'role', server_default=None)
    op.drop_constraint(op.f('uq_trip_members_trip_id_display_name'), 'trip_members', type_='unique')
    op.create_index(op.f('ix_trip_members_user_id'), 'trip_members', ['user_id'], unique=False)
    op.create_index('uq_trip_members_trip_id_lower_display_name', 'trip_members', ['trip_id', sa.literal_column('lower(display_name)')], unique=True)
    op.create_foreign_key(op.f('fk_trip_members_user_id_users'), 'trip_members', 'users', ['user_id'], ['id'], ondelete='SET NULL')
    op.create_check_constraint(op.f('ck_trip_members_role_valid'), 'trip_members', "role IN ('owner', 'editor', 'viewer')")
    op.create_check_constraint(op.f('ck_trip_members_currency_pref_iso'), 'trip_members', "currency_pref IS NULL OR currency_pref ~ '^[A-Z]{3}$'")

    # --- trips: CORE-001 contract. Temporary server defaults backfill rows created under 0001. ---
    backfilled = {
        'title': (sa.String(length=120), sa.text("'Untitled trip'")),
        'status': (sa.String(length=16), sa.text("'draft'")),
        'adults': (sa.Integer(), sa.text('1')),
        'infants': (sa.Integer(), sa.text('0')),
        'base_currency': (sa.String(length=3), sa.text("'GBP'")),
        'settlement_currency': (sa.String(length=3), sa.text("'GBP'")),
        'day_start': (sa.Time(), sa.text("'09:00'")),
        'day_end': (sa.Time(), sa.text("'20:00'")),
        'mobility_needs': (sa.String(length=20), sa.text("'none'")),
        'price_level': (sa.SmallInteger(), sa.text('2')),
    }
    op.add_column('trips', sa.Column('owner_id', sa.Uuid(), nullable=True))
    for name, (type_, default) in backfilled.items():
        op.add_column('trips', sa.Column(name, type_, server_default=default, nullable=False))
    op.add_column('trips', sa.Column('children_ages', postgresql.ARRAY(sa.SmallInteger()), server_default='{}', nullable=False))
    op.add_column('trips', sa.Column('budget_amount', sa.Numeric(precision=14, scale=2), nullable=True))
    op.add_column('trips', sa.Column('budget_currency', sa.String(length=3), nullable=True))
    op.add_column('trips', sa.Column('budget_scope', sa.String(length=16), nullable=True))
    op.add_column('trips', sa.Column('dietary', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False))
    op.add_column('trips', sa.Column('flight_prefs', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False))
    # Preserve 0001 data: old travellers count becomes adults; old destination becomes a single stop.
    op.execute("UPDATE trips SET adults = LEAST(travellers, 20), title = destination")
    op.execute(
        "INSERT INTO trip_stops (id, trip_id, seq, city, nights, arrive_on, leave_on) "
        "SELECT gen_random_uuid(), id, 0, destination, end_date - start_date, start_date, end_date FROM trips"
    )
    for name in backfilled:
        op.alter_column('trips', name, server_default=None)
    op.create_index(op.f('ix_trips_owner_id'), 'trips', ['owner_id'], unique=False)
    op.create_foreign_key(op.f('fk_trips_owner_id_users'), 'trips', 'users', ['owner_id'], ['id'], ondelete='SET NULL')
    op.drop_column('trips', 'destination')
    op.drop_column('trips', 'travellers')  # also drops ck_trips_travellers_range
    for name, condition in TRIP_CHECKS.items():
        op.create_check_constraint(op.f(f'ck_trips_{name}'), 'trips', condition)


def downgrade() -> None:
    for name in TRIP_CHECKS:
        op.drop_constraint(op.f(f'ck_trips_{name}'), 'trips', type_='check')
    op.add_column('trips', sa.Column('travellers', sa.INTEGER(), server_default='1', nullable=False))
    op.add_column('trips', sa.Column('destination', sa.VARCHAR(length=120), server_default='', nullable=False))
    op.execute(
        "UPDATE trips t SET travellers = t.adults + cardinality(t.children_ages) + t.infants, "
        "destination = COALESCE((SELECT city FROM trip_stops s WHERE s.trip_id = t.id ORDER BY seq DESC LIMIT 1), t.title)"
    )
    op.alter_column('trips', 'travellers', server_default=None)
    op.alter_column('trips', 'destination', server_default=None)
    op.create_check_constraint(op.f('ck_trips_travellers_range'), 'trips', 'travellers BETWEEN 1 AND 20')
    op.drop_constraint(op.f('fk_trips_owner_id_users'), 'trips', type_='foreignkey')
    op.drop_index(op.f('ix_trips_owner_id'), table_name='trips')
    for name in ('flight_prefs', 'price_level', 'mobility_needs', 'dietary', 'day_end', 'day_start', 'budget_scope',
                 'budget_currency', 'budget_amount', 'settlement_currency', 'base_currency', 'infants',
                 'children_ages', 'adults', 'status', 'title', 'owner_id'):
        op.drop_column('trips', name)
    op.drop_constraint(op.f('ck_trip_members_currency_pref_iso'), 'trip_members', type_='check')
    op.drop_constraint(op.f('ck_trip_members_role_valid'), 'trip_members', type_='check')
    op.drop_constraint(op.f('fk_trip_members_user_id_users'), 'trip_members', type_='foreignkey')
    op.drop_index('uq_trip_members_trip_id_lower_display_name', table_name='trip_members')
    op.drop_index(op.f('ix_trip_members_user_id'), table_name='trip_members')
    op.create_unique_constraint(op.f('uq_trip_members_trip_id_display_name'), 'trip_members', ['trip_id', 'display_name'])
    op.drop_column('trip_members', 'position')
    op.drop_column('trip_members', 'currency_pref')
    op.drop_column('trip_members', 'role')
    op.drop_column('trip_members', 'user_id')
    op.drop_table('trip_stops')
    op.drop_index(op.f('ix_trip_constraints_trip_id'), table_name='trip_constraints')
    op.drop_table('trip_constraints')
    op.drop_index(op.f('ix_bookings_trip_id'), table_name='bookings')
    op.drop_table('bookings')
    op.drop_table('users')
