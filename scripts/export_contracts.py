"""Generate the complete model schema and field reference, including internal models."""
import inspect
import json
from pathlib import Path
from pydantic import BaseModel
from pydantic.json_schema import models_json_schema
from shared import models
from shared.rules import CONTRACT_VERSION


def export():
    classes = sorted({cls for _, cls in inspect.getmembers(models, inspect.isclass)
                      if issubclass(cls, BaseModel) and cls.__module__ == models.__name__
                      and cls.__name__ not in ('StrictModel', 'Page')}, key=lambda c: c.__name__)
    _, schema = models_json_schema([(cls, 'validation') for cls in classes], title=f'LOTUS {CONTRACT_VERSION}')
    Path('contracts/models.schema.json').write_text(json.dumps(schema, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['# 공통 필드 명세 (자동 생성)', '',
             '`python -m scripts.export_contracts`로 갱신한다. 타입·길이·범위·null·기본값은 아래 JSON Schema 조각을 따른다.',
             '교차 필드 검증과 의미는 CONTRACT.md 및 shared/models를 함께 읽는다.', '']
    for cls in classes:
        model_schema = cls.model_json_schema()
        lines.extend([f'## {cls.__name__}', '', '| 필드 | 필수 | 타입·기본값·제한 |', '|---|---|---|'])
        for name, prop in model_schema.get('properties', {}).items():
            prop = {k: v for k, v in prop.items() if k != 'title'}
            encoded = json.dumps(prop, ensure_ascii=False).replace('|', '&#124;')
            lines.append(f'| {name} | {"예" if name in model_schema.get("required", []) else "아니요"} | `{encoded}` |')
        lines.append('')
    Path('contracts/FIELDS.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    export()
