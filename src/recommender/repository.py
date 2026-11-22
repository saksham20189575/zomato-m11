"""Restaurant corpus access."""

from __future__ import annotations

from recommender.config import Settings, get_settings
from recommender.ingestion import DatasetLoader
from recommender.models import Restaurant


class RestaurantRepository:
    """In-memory access to cleaned restaurant records."""

    def __init__(
        self,
        loader: DatasetLoader | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.loader = loader or DatasetLoader(settings=self.settings)
        self._restaurants: list[Restaurant] | None = None

    def load(self) -> list[Restaurant]:
        """Load (or reload) the corpus via the dataset loader."""
        restaurants = self.loader.load()
        if not restaurants:
            raise ValueError("Restaurant corpus is empty after load")
        self._restaurants = restaurants
        return restaurants

    def all(self) -> list[Restaurant]:
        """Return all restaurants, loading once if needed."""
        if self._restaurants is None:
            self.load()
        assert self._restaurants is not None
        return list(self._restaurants)

    def get(self, restaurant_id: str) -> Restaurant | None:
        """Lookup a single restaurant by id."""
        for restaurant in self.all():
            if restaurant.id == restaurant_id:
                return restaurant
        return None

    def distinct_locations(self) -> list[str]:
        """Sorted unique locality strings for UI dropdowns."""
        return sorted({r.location for r in self.all() if r.location})

    def distinct_cuisines(self) -> list[str]:
        """Sorted unique cuisine tokens for UI dropdowns."""
        cuisines: set[str] = set()
        for restaurant in self.all():
            cuisines.update(c for c in restaurant.cuisines if c)
        return sorted(cuisines)

    def __len__(self) -> int:
        return len(self.all())
