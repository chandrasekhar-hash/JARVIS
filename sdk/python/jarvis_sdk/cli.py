import os
import sys
import json
import tarfile
import argparse


def package_plugin(plugin_dir: str, output_path: str):
    """
    Packages a plugin directory into a `.jpx` tar.gz package.
    """
    manifest_path = os.path.join(plugin_dir, "plugin.json")
    if not os.path.exists(manifest_path):
        print(f"Error: manifest 'plugin.json' not found in '{plugin_dir}'")
        sys.exit(1)

    with tarfile.open(output_path, "w:gz") as tar:
        tar.add(plugin_dir, arcname=os.path.basename(plugin_dir))
    print(f"Successfully packaged plugin into '{output_path}'")


def main():
    parser = argparse.ArgumentParser(prog="jarvis-plugin", description="J.A.R.V.I.S. Plugin CLI")
    subparsers = parser.add_subparsers(dest="command")

    pack_cmd = subparsers.add_parser("pack", help="Package a plugin into a .jpx archive")
    pack_cmd.add_argument("dir", help="Path to plugin directory")
    pack_cmd.add_argument("-o", "--output", default="plugin.jpx", help="Output package path")

    args = parser.parse_args()
    if args.command == "pack":
        package_plugin(args.dir, args.output)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
