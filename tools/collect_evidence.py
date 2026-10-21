"""Verify source / installed / wheel equality; compare an explicit historical baseline."""
import argparse
from datetime import datetime, timezone
import difflib
from email.parser import BytesParser
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


def compare_baseline(wheel, old, namespace, version):
    """Same version must be identical; a new version gets a complete recorded diff."""
    with ZipFile(wheel) as new, ZipFile(old) as previous:
        def payload(z):
            keys=[n for n in z.namelist() if n.endswith('.dist-info/METADATA')]
            assert len(keys)==1, 'Expected one wheel distribution'
            meta=BytesParser().parsebytes(z.read(keys[0]))
            assert meta['Name'].replace('-','_')==namespace, 'Baseline distribution mismatch'
            values={n:z.read(n) for n in z.namelist() if n.startswith(namespace+'/') and not n.endswith('/')}
            values['METADATA']=z.read(keys[0])
            values['WHEEL']=z.read(keys[0].removesuffix('METADATA')+'WHEEL')
            return meta['Version'],values
        current_version,current=payload(new);old_version,prior=payload(previous)
    assert current_version==version, 'Current wheel version mismatch'
    added=sorted(current.keys()-prior.keys());removed=sorted(prior.keys()-current.keys())
    changed=sorted(k for k in current.keys()&prior.keys() if current[k]!=prior[k])
    if old_version==version:
        assert current==prior, 'Same-version historical payload mismatch'
    diff=[]
    for key in sorted(set(added+removed+changed)):
        a,b=prior.get(key,b''),current.get(key,b'')
        try:
            diff.extend(difflib.unified_diff(a.decode('utf-8').splitlines(keepends=True),b.decode('utf-8').splitlines(keepends=True),fromfile=old_version+'/'+key,tofile=version+'/'+key))
        except UnicodeDecodeError:
            diff.append(f'Binary difference: {key}: {sha(a)} -> {sha(b)}\n')
    return dict(version=old_version,mode='same_version_equal' if old_version==version else 'cross_version_diff',
                added=added,removed=removed,changed=changed,
                before={k:sha(v) for k,v in prior.items()},after={k:sha(v) for k,v in current.items()}),''.join(diff)


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
    parser.add_argument('--baseline-wheel', action='append', default=[], metavar='PACKAGE=PATH',
                        help='Historical wheel to compare; required if no same-version historical wheel exists')
    parser.add_argument('--report-dir', type=Path, required=True, help='Must not exist')
    args = parser.parse_args()
    packages=('s01', 's02') if args.package=='all' else (args.package,)
    baselines={}
    for value in args.baseline_wheel:
        name,separator,path=value.partition('=')
        if not separator or not path or name not in packages or name in baselines:
            parser.error('--baseline-wheel requires one PACKAGE=PATH per selected package')
        baselines[name]=Path(path).resolve(strict=True)
    report = args.report_dir.resolve()
    report.mkdir(parents=True, exist_ok=False)
    records = []
    for name in packages:
        package = WORKSPACE / 'packages' / name
        project = tomllib.loads((package / 'pyproject.toml').read_text())['project']
        namespace = project['name'].replace('-', '_')
        version = project['version']
        wheel_name = f'{namespace}-{version}-py3-none-any.whl'
        wheel = args.wheel_dir.resolve() / wheel_name
        old = baselines.get(name,WORKSPACE / ('dist' if name == 's01' else 's02/dist') / wheel_name)
        if not old.is_file():
            parser.error(f'{name}: no historical wheel; provide --baseline-wheel {name}=PATH')
        module = importlib.import_module(namespace)
        installed = Path(module.__file__).parent
        assert 'site-packages' in installed.parts, installed
        assert metadata.version(project['name']) == version
        a, b, c = tree(package / 'src' / namespace), tree(installed), wheel_tree(wheel, namespace)
        assert a == b == c, f'{name}: package inventory/content mismatch'
        dist = metadata.distribution(project['name'])
        direct = json.loads(dist.read_text('direct_url.json'))
        assert not direct.get('dir_info', {}).get('editable', False)
        assert direct['archive_info']['hashes']['sha256'] == sha(wheel.read_bytes())
        with ZipFile(wheel) as new:
            for field in ('METADATA', 'WHEEL'):
                key = f'{namespace}-{version}.dist-info/{field}'
                assert new.read(key) == dist.read_text(field).encode()
        baseline,baseline_diff=compare_baseline(wheel,old,namespace,version)
        (report/(name+'-baseline.diff')).write_text(baseline_diff)
        records.append(dict(package=name,version=version,import_path=str(module.__file__),files=a,
                            comparison='source = installed = rebuilt wheel; full file inventory; historical baseline compared separately',baseline=baseline,
                            rebuilt_wheel=str(wheel),rebuilt_sha256=sha(wheel.read_bytes()),
                            historical_wheel=str(old),historical_sha256=sha(old.read_bytes()),direct_url=direct))
    manifest = dict(captured_at=datetime.now(timezone.utc).isoformat(),python=sys.version,executable=sys.executable,
                    platform=platform.platform(),sqlite=sqlite3.sqlite_version,gil_enabled=sys._is_gil_enabled(),
                    dependencies={d.metadata['Name']:d.version for d in metadata.distributions()},packages=records)
    (report / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(dict(packages=[dict(name=p['package'],files=len(p['files']),version=p['version']) for p in records])))


if __name__ == '__main__':
    main()
