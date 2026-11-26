"""Package the public Markdown Skill; never include project or runtime files."""
import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills" / "steam-release-guard"
OUTPUT = ROOT / "downloads" / "steam-release-guard-skill.zip"
FILES = ("SKILL.md", "LICENSE", "INSTALL.md", "INSTALL.en.md", "EXAMPLES.md", "EXAMPLES.en.md")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check the archive without changing it")
    args = parser.parse_args()
    contents = {"steam-release-guard/" + name: (SOURCE / name).read_text(encoding="utf-8").encode("utf-8")
                for name in FILES}
    if args.check:
        with zipfile.ZipFile(OUTPUT) as archive:
            if len(archive.namelist()) != len(contents) or set(archive.namelist()) != set(contents):
                raise SystemExit("Skill ZIP has unexpected, missing or duplicate files. Rebuild it.")
            for name, data in contents.items():
                if archive.read(name) != data:
                    raise SystemExit("Skill ZIP is out of date. Run python scripts/package_skill.py")
        print("Skill ZIP matches all 6 public Markdown/license source files.")
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in contents.items():
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 27, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    print("Created downloads/steam-release-guard-skill.zip (6 public files).")


if __name__ == "__main__":
    main()
