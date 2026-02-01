from dataclasses import dataclass


@dataclass(frozen=True)
class WhiteboxResult:
    whitebox_url: str
    depth_url: str


def mock_generate_whitebox(*, base_url: str) -> WhiteboxResult:
    base = base_url.rstrip("/")
    return WhiteboxResult(
        whitebox_url=f"{base}/static/mock/whitebox.obj",
        depth_url=f"{base}/static/mock/depth.png",
    )
