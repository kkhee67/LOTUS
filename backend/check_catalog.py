"""Read-only catalog preflight for local startup and deployment scripts."""
import json

from backend.catalog_store import CatalogUnavailable, read_catalog
from backend.settings import Settings


def main() -> int:
    try:
        settings = Settings()
    except (ValueError, OSError):
        print(json.dumps({'status': 'invalid_configuration', 'code': 'CONFIGURATION_ERROR'}))
        return 2
    try:
        catalog = read_catalog(settings)
    except CatalogUnavailable:
        print(json.dumps({'status': 'unavailable', 'code': 'CATALOG_UNAVAILABLE'}))
        return 1
    except Exception:
        # Unexpected failures must not expose settings, paths, or source payloads.
        print(json.dumps({'status': 'error', 'code': 'CHECK_FAILED'}))
        return 3
    print(json.dumps({'status': 'ok', 'data_mode': settings.data_mode,
                      'counts': {name: len(items) for name, items in catalog.items()}}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
