"""Build unchanged product versions into a new output directory, offline."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tomllib

WORKSPACE = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', choices=('s01', 's02', 'all'), required=True)
    parser.add_argument('--output-dir', type=Path, required=True, help='Must not exist')
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for name in (('s01', 's02') if args.package == 'all' else (args.package,)):
        package = WORKSPACE / 'packages' / name
        project = tomllib.loads((package / 'pyproject.toml').read_text())['project']
        command = [sys.executable, '-B', '-m', 'pip', 'wheel', '--no-index', '--no-deps', '--no-build-isolation',
                   '--wheel-dir', str(output), str(package)]
        result = subprocess.run(command, cwd=output, capture_output=True, text=True)
        (output / (name + '-build.log')).write_text('$ ' + shlex.join(command) + '\ncwd=' + str(output) + '\n' +
            result.stdout + result.stderr + f'\nexit_code={result.returncode}\n')
        results.append(dict(package=name,version=project['version'],command=command,cwd=str(output),exit_code=result.returncode))
        print(name, 'build exit', result.returncode, flush=True)
        if result.returncode:
            break
    (output / 'commands.json').write_text(json.dumps(results, indent=2) + '\n')
    return int(any(r['exit_code'] for r in results))


if __name__ == '__main__':
    raise SystemExit(main())
