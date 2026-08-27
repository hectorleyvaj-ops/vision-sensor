"""Atomically activate one release while preserving the previous target."""

import argparse

from core.deployment_paths import DeploymentPaths, switch_release


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default="/opt/vision-sensor")
    parser.add_argument("--installation", default="vision-station")
    parser.add_argument("--target", required=True)
    args = parser.parse_args(argv)
    paths = DeploymentPaths.from_values(args.prefix, args.installation)
    previous = switch_release(paths, args.target)
    print("Release anterior: {}".format(previous or "ninguno"))
    print("Release activa: {}".format(paths.current.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
