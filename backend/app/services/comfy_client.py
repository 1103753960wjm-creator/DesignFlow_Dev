from dataclasses import dataclass


@dataclass(frozen=True)
class GalleryResult:
    images: list[str]


def mock_generate_gallery(*, base_url: str, count: int = 6) -> GalleryResult:
    base = base_url.rstrip("/")
    images = [f"{base}/static/mock/gallery/g{i}.png" for i in range(1, count + 1)]
    return GalleryResult(images=images)
