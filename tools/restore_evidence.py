"""Restore the archived repository evidence into a new external directory."""
import argparse
import json
from pathlib import Path
from artifact_bundle import verify,restore


def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    if output.exists() or output==root or root in output.parents:parser.error('Restore output must be new and outside checkout')
    spec,entries=verify(args.archive,root/'artifacts/evidence-archive.json')
    restore(args.archive,output,entries)
    print(json.dumps(dict(output=str(output),members=len(entries),sha256=spec['sha256'],all_files_verified=True)))


if __name__=='__main__':main()
