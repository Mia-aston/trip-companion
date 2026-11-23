from app.providers.base import Place


class MockPlacesProvider:
    def search(self, query: str, latitude: float, longitude: float) -> list[Place]:
        return [
            Place(
                id="mock-place-1",
                name=f"Sample result for {query}",
                latitude=latitude,
                longitude=longitude,
                categories=("attraction",),
            )
        ]
