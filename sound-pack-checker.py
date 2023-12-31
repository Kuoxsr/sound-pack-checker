#!/usr/bin/env python3

# noinspection GrazieInspection
"""
Problem: Validate a Minecraft Sound Resource pack
Target Users: Me
Target System: GNU/Linux
Interface: Command-line
Functional Requirements: Print out a list of broken links.
Notes:

Command-line arguments:

    --help      (-h)    Show usage
    --version   (-v)    Show version number
"""

__version__ = '2.10'
__maintainer__ = "kuoxsr@gmail.com"
__status__ = "Prototype"

# Import modules
import argparse
import json
import os
import re
import sys
from pathlib import Path
from collections import Counter


# ------------------------------------------------------
# Function definitions
# ------------------------------------------------------


def handle_command_line():
    """
    Handle arguments supplied by the user
    """

    parser = argparse.ArgumentParser(
        prog="Sound Pack Checker",
        description="generates lists of invalid connections between json and sound files.")

    parser.add_argument("-v", "--version", action="version", version="%(prog)s version " + __version__)

    parser.add_argument(
        "path",
        action="store",
        nargs=argparse.REMAINDER,
        help="Path to the sounds.json file you want to check.  The file name itself is not required.")

    args = parser.parse_args()

    args.path = get_real_path(args.path)

#    print("args:",args); exit()
    return args


def get_real_path(args_path: list[str]) -> Path:

    input: Path = args_path[0] if (len(args_path) > 0) else ""

    # Has the user specified a path at all?
    if not input:
        print("Path to sounds.json is required.")
        exit(1)

    path: Path = Path(input)

    # Does path folder exist on the file system?
    if not path.exists():
        print(f"Specified path not found. {path} is not a valid filesystem path.")
        exit(1)

    # Does the path refer only to a folder?  Assume sounds.json
    if path.is_dir():
        path = path / "sounds.json"

    # Has the user specified the wrong file extension?
    if path.suffix != ".json":
        print(f"specified file: {path} is not a JSON file")
        exit(1)

    # Does sounds.json exist, now that we've added it for them (if necessary?)
    if not Path(path).exists():
        print("sounds.json not found.")
        exit(1)

    return Path(path).resolve()


def get_event_dictionary(path: Path) -> dict[str, list[Path]]:

    with open(path, "r") as read_file:
        json_data: dict = dict(json.load(read_file))

    events: dict[str, list] = {}

    for event in json_data.items():

        sound_paths: list[Path] = []
        for sound in event[1]['sounds']:
            sound_paths.append(get_sound_path(path, sound))

        events[event[0]] = sound_paths

    return events


def get_sound_path(path: Path, sound: str) -> Path:

    sound_path: str = ""

    if isinstance(sound, str):
        sound_path = sound

    elif isinstance(sound, dict):
        sound_path = sound['name']

    else:
        sys.exit(f"\nI have no idea how to process this: {sound}\n")

    namespace: str = "minecraft"

    if ":" in sound_path:
        parts = sound_path.split(":")
        namespace = Path(parts[0])
        sound_path = Path(parts[1])

    return path.parent.parent / namespace / Path("sounds") / Path(sound_path).with_suffix(".ogg")


def get_invalid_file_names(events: dict[str, list[Path]]) -> list[Path]:

    bad_names: list[Path] = []
    pattern = re.compile("^[a-z0-9/._-]+$")

    for value in events.values():

        for sound in value:
            # print(f"sound: {sound}")

            # Check for "invalid" characters
            if not pattern.match(str(sound)):
                bad_names.append(sound)

    return bad_names


def get_orphaned_files(events: dict[str, list[Path]], ogg_files: list[Path]) -> list[Path]:

    orphaned_files: list[Path] = []
    # print(f"\nevents.values() -> {len(events.values())} {events.values()}\n")

    sounds: list[Path] = []
    for sound in events.values():
        sounds.extend(sound)

    # print(f"\nsounds() -> {len(sounds)} {sounds}")
    # print(f"\nogg_files: {len(ogg_files)} {ogg_files}\n")

    links: list[Path] = list(set([lnk.resolve() for lnk in ogg_files if lnk.is_symlink()]))
    # print(f"\nlinks: {len(links)} {links}\n")

    orphans: list[Path] = [o for o in ogg_files if o not in sounds and o not in links]
    if len(orphans) > 0:
        orphaned_files.extend(orphans)

    return orphaned_files


def get_broken_links(events: dict[str, list[Path]]) -> list[Path]:

    script_home_path: Path = Path(__file__).absolute().resolve().parent
    # print(f"script_home_path: {script_home_path}")

    vanilla_events = get_event_dictionary(script_home_path / Path("vanilla-sounds.json"))

    broken_links: list[Path] = []
    for event, sounds in events.items():
        # print(f"event: {event}")
        # print(f"sounds-> {sounds}")

        if event in vanilla_events.keys():
            vanilla_sounds = vanilla_events[event]
            # print(f"vanilla_sounds: {vanilla_sounds}")

        bad_paths = list(p for p in sounds if not p.exists())

        for pth in bad_paths:
            # print(f"pth: {pth.name}")

            if pth.is_symlink():
                broken_links.append(pth)
                continue

            if pth.name not in list(v.name for v in vanilla_sounds):
                broken_links.append(pth)

    return broken_links


# Main -------------------------------------------------
def main():
    """
    Main program loop
    This function generates lists of invalid connections between json and sound files
    """

    green = "\033[32m"
    red = "\033[31m"
    yellow = "\033[33m"
    white = "\033[97m"
    bold = "\033[1m"
    default = "\033[0m"

    # Platform independent clearing of screen
    os.system('cls||clear')

    args = handle_command_line()
    print(f"{bold}{white}Scanning file:\n{default}{yellow}{args.path}")

    events: dict[str, list] = get_event_dictionary(args.path)
    # print("\n===============================")
    # print(f"events: {events}")
    # print("===============================")

    # All ogg files in folder structure
    ogg_files: list[Path] = list(args.path.parent.parent.rglob("*.ogg"))
    # print("\nAll ogg files in folder structure:")
    # temp_ogg_files = [print(e) for e in ogg_files]
    # print()

    assets_folder: Path = args.path.parent.parent

    invalid_file_names: list = get_invalid_file_names(events)
    if len(invalid_file_names) > 0:
        print(f"{red}\nThe following file names violate Mojang's new constraints:{default}")
        temp = [print(f" .../{i.relative_to(assets_folder)}") for i in invalid_file_names]

    broken_links: list[Path] = get_broken_links(events)
    if len(broken_links) > 0:
        print(f"{red}\nThe following paths exist in JSON, but do not correspond to actual file system files:{default}")
        temp = [print(f".../{a.relative_to(assets_folder)}") for a in broken_links]

    orphaned_files: list[Path] = get_orphaned_files(events, ogg_files)
    if len(orphaned_files) > 0:
        print(f"{red}\nThe following .ogg files exist, but no JSON record refers to them:{default}")
        temp = [print(f".../{b.relative_to(assets_folder)}") for b in orphaned_files]

    print(f"{green}\n-------------------------------------------------------")
    print("Sound count:\n")

    count: int = 0
    for key in events:
        paths = [pth for pth in events[key] if not pth.is_symlink() and pth.exists()]
        links = list(set([lnk.resolve() for lnk in events[key] if lnk.is_symlink() and lnk.resolve().exists()]))
        paths.extend(links)

        c = len(paths)

        if c > 0:
            print(f"{key} -> {c}")
            count += c

    print(f"\nTotal sounds: {count}")
    print(f"-------------------------------------------------------{default}")


# ------------------------------------------------------
# Main program loop
# ------------------------------------------------------

# Run main program loop only if not called as a module
if __name__ == "__main__":
    main()
