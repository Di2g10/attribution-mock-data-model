"""Module to store relevant filepaths in.

Files should not be stored on your local machine if possible and instead use Sharepoint. Create filepaths which are
not hardcoded with your username using os.getlogin()
"""

from pathlib import Path
import os

example_path = Path(
    "C://",
    "Users",
    os.getlogin(),
    "CleverTouch",
    "Data Team - Documents",
    "General",
)

ROOT_DIR = Path(__file__).resolve().parent
