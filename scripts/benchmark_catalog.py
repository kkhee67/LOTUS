"""Measure full validation on disposable synthetic catalogs, never production data."""
import copy
import json
import statistics
import tempfile
import time
from pathlib import Path

from backend.importer import import_directory
from backend.catalog_store import read_catalog
from backend.settings import ROOT, Settings


def main():
    examples = ROOT / 'contracts/examples'
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for count in (3, 300, 3000):
            batch = root / str(count)
            batch.mkdir()
            for name in ('sources', 'roles', 'resource_links'):
                (batch / f'{name}.json').write_bytes((examples / f'{name}.json').read_bytes())
            template = json.loads((examples / 'opportunities.json').read_text(encoding='utf-8'))[0]
            rows = []
            for index in range(count):
                item = copy.deepcopy(template)
                item['id'] = f'bench-{index}'
                rows.append(item)
            (batch / 'opportunities.json').write_text(json.dumps(rows), encoding='utf-8')
            db = root / f'{count}.db'
            import_directory(batch, db, mode='demo')
            settings = Settings(_env_file=None, database_url='sqlite:///' + str(db), data_mode='demo')
            read_catalog(settings)
            times = []
            for _ in range(9):
                start = time.perf_counter()
                read_catalog(settings)
                times.append((time.perf_counter() - start) * 1000)
            print(json.dumps({'synthetic_records': count, 'median_ms': round(statistics.median(times), 3)}))


if __name__ == '__main__':
    main()
