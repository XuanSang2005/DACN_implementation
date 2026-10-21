"""Compare complete source / installed / rebuilt / historical package payloads."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.metadata as metadata
import json
from pathlib import Path
import platform
import sqlite3
import sys
import tomllib
from zipfile import ZipFile

WORKSPACE = Path(__file__).resolve().parents[1]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def tree(path):
    return {str(p.relative_to(path)): sha(p.read_bytes()) for p in path.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts}


def wheel_tree(path, namespace):
    with ZipFile(path) as z:
        return {n.removeprefix(namespace + '/'): sha(z.read(n)) for n in z.namelist()
                if n.startswith(namespace + '/') and not n.endswith('/')}


def main(*, fixed_package=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    if fixed_package is None:
        parser.add_argument('--package', choices=('s01', 's02', 'all'), required=True)
    else:
        # Package entry points have no public selector to override.
        if fixed_package not in ('s01', 's02'):
            raise ValueError('Invalid fixed package')
        parser.set_defaults(package=fixed_package)
    parser.add_argument('--wheel-dir', type=Path, required=True)
    parser.add_argument('--report-dir', type=Path, required=True, help='Must not exist')
    args = parser.parse_args()
    report = args.report_dir.resolve()
    report.mkdir(parents=True, exist_ok=False)
    records = []
    for name in (('s01', 's02') if args.package == 'all' else (args.package,)):
        package = WORKSPACE / 'packages' / name
        project = tomllib.loads((package / 'pyproject.toml').read_text())['project']
        namespace = project['name'].replace('-', '_')
        version = project['version']
        wheel_name = f'{namespace}-{version}-py3-none-any.whl'
        wheel = args.wheel_dir.resolve() / wheel_name
        old = WORKSPACE / ('dist' if name == 's01' else 's02/dist') / wheel_name
        module = importlib.import_module(namespace)
        installed = Path(module.__file__).parent
        assert 'site-packages' in installed.parts, installed
        assert metadata.version(project['name']) == version
        a, b, c, d = tree(package / 'src' / namespace), tree(installed), wheel_tree(wheel, namespace), wheel_tree(old, namespace)
        assert a == b == c == d, f'{name}: package inventory/content mismatch'
        dist = metadata.distribution(project['name'])
        direct = json.loads(dist.read_text('direct_url.json'))
        assert not direct.get('dir_info', {}).get('editable', False)
        assert direct['archive_info']['hashes']['sha256'] == sha(wheel.read_bytes())
        with ZipFile(wheel) as new, ZipFile(old) as previous:
            for field in ('METADATA', 'WHEEL'):
                key = f'{namespace}-{version}.dist-info/{field}'
                assert new.read(key) == previous.read(key) == dist.read_text(field).encode()
        records.append(dict(package=name,version=version,import_path=str(module.__file__),files=a,
                            comparison='source = installed = rebuilt wheel = historical wheel; full file inventory',
                            rebuilt_wheel=str(wheel),rebuilt_sha256=sha(wheel.read_bytes()),
                            historical_wheel=str(old),historical_sha256=sha(old.read_bytes()),direct_url=direct))
    manifest = dict(captured_at=datetime.now(timezone.utc).isoformat(),python=sys.version,executable=sys.executable,
                    platform=platform.platform(),sqlite=sqlite3.sqlite_version,gil_enabled=sys._is_gil_enabled(),
                    dependencies={d.metadata['Name']:d.version for d in metadata.distributions()},packages=records)
    (report / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(dict(packages=[dict(name=p['package'],files=len(p['files']),version=p['version']) for p in records])))


if __name__ == '__main__':
    main()
