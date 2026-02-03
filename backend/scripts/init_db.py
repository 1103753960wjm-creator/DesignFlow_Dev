import sys
from pathlib import Path


def main():
    backend_dir = Path(__file__).resolve().parents[1]
    sys.path.append(str(backend_dir))

    from app.db.session import Base, engine

    import app.models.user
    import app.models.cad_revision

    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    main()
