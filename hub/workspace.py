"""Lay the factories out on disk somewhere the user can actually write.

An installed copy lives in Program Files (or wherever the installer put it) and
is read-only for a normal account. The factories, though, are meant to be poked
at: config.json is a file the user edits, topics.json is a list they add to, and
output/ fills up with videos. So on first run the program copies the factories
out of the install into a workspace folder and runs them from there.

The copy is one-way and never overwrites. If the user edits config.json, a later
version of the program must not silently reset it - a new default that matters
belongs in a release note, not in a surprise overwrite.
"""
import shutil

from hub.paths import CODE, FACTORIES, IS_CI, IS_FROZEN, workspace

SKIP_DIRS = {"__pycache__", "output", "cache", ".git", "build", "dist"}


def needed():
    """In CI and when running from source the checkout *is* the workspace."""
    return IS_FROZEN and not IS_CI


def _copy_tree(source, target, log):
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        if item.name in SKIP_DIRS:
            continue
        destination = target / item.name
        if item.is_dir():
            _copy_tree(item, destination, log)
        elif not destination.exists():
            shutil.copy2(item, destination)
            log(f"  + {destination.relative_to(target.parent.parent)}")


def ensure(log=lambda *_: None):
    """Make sure every factory exists in the workspace. Returns the root."""
    root = workspace()
    if not needed():
        return root

    root.mkdir(parents=True, exist_ok=True)
    for name in FACTORIES:
        source = CODE / "factories" / name
        if not source.exists():
            continue
        target = root / "factories" / name
        first_time = not target.exists()
        if first_time:
            log(f"setting up {name} in {target}")
        _copy_tree(source, target, log)
        for folder in ("output", "cache", "assets/music", "assets/stock"):
            (target / folder).mkdir(parents=True, exist_ok=True)
    return root


def reset_factory(name, log=lambda *_: None):
    """Put a factory's shipped defaults back, keeping output/ and cache/.

    For when a user has edited config.json into a state that will not run and
    wants the original back without reinstalling.
    """
    root = workspace()
    target = root / "factories" / name
    for item in ("config.json", "topics.json"):
        source = CODE / "factories" / name / item
        if source.exists():
            shutil.copy2(source, target / item)
            log(f"restored {name}/{item}")
    return target
