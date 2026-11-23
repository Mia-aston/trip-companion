from app.domain.recommendations.taste import TasteVector, taste_match


def test_identical_taste_is_full_match():
    profile = TasteVector(spicy=0.8, savory=0.9, sweet=0.2)
    assert taste_match(profile, profile) == 1.0


def test_different_taste_reduces_match():
    user = TasteVector(spicy=1.0, sweet=0.0)
    restaurant = TasteVector(spicy=0.0, sweet=1.0)
    assert taste_match(user, restaurant) < 1.0
