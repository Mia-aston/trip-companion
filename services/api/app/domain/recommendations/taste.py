from dataclasses import dataclass


@dataclass(frozen=True)
class TasteVector:
    spicy: float = 0.5
    savory: float = 0.5
    sour: float = 0.5
    sweet: float = 0.5
    herbs: float = 0.5
    richness: float = 0.5
    adventurous: float = 0.5
    authenticity: float = 0.5

    def values(self) -> tuple[float, ...]:
        return (
            self.spicy,
            self.savory,
            self.sour,
            self.sweet,
            self.herbs,
            self.richness,
            self.adventurous,
            self.authenticity,
        )


def taste_match(user: TasteVector, restaurant: TasteVector) -> float:
    """Return 0..1 similarity from declared/content-derived taste signals.

    Never infer race or ethnicity from reviewer name, photo, language or profile.
    """
    a, b = user.values(), restaurant.values()
    distance = sum(abs(x - y) for x, y in zip(a, b)) / len(a)
    return max(0.0, min(1.0, 1.0 - distance))
