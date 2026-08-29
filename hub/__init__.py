"""Shared plumbing for the Automation Hub.

The two video factories under `factories/` stay independent - different market,
different language, different voice - and each keeps its own `pipeline` package.
That means they can never be imported into the same process (identical package
name), so everything here talks to them by running them as subprocesses.

What lives here is only the part both share: where files go, the Planly
publisher, run status, and notifications.
"""
__version__ = "1.0.0"
