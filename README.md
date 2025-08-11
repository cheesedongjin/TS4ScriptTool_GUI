# TS4ScriptTool GUI
A simple Tkinter GUI to **extract**, **edit**, and **repack** Sims 4 `.ts4script` archives.
No external dependencies.

## Features
- Extract: Unpack a `.ts4script` to a workspace folder.
- Pack: Build a `.ts4script` from a workspace folder.
- Watch: Auto-pack on file changes via polling (no external libs).
- Ignore list editor: Manage `.ts4ignore` patterns per workspace.

## Run
Double-click `ts4script_tool_gui.py` (or run `python ts4script_tool_gui.py`).

## Tips
- `.ts4script` is a zip archive. This tool enforces consistent packing and ignores junk files.
- When packing, an automatic backup is created if the destination exists.
- The watcher uses mtime+size scanning for portability.

