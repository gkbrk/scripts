#!/usr/bin/env python3
import sys
import subprocess

# git-edit-commit-time.py: Edit the times of commits in a git repository
# Gokberk Yaltirakli, 2022

try:
    N_COMMIT = int(sys.argv[1])
except IndexError:
    N_COMMIT = 25
except ValueError:
    print("Invalid number")
    sys.exit(1)


def get_output(cmd: list[str]) -> str:
    """Get the output of a command as a string.

    Parameters
    ----------
    cmd : list[str]
        The command to run.

    Returns
    -------
    str
        The output of the command.
    """
    return subprocess.check_output(cmd).decode("utf-8").strip()


def is_git_repo() -> bool:
    """Check if the current directory is a git repository.

    Returns
    -------
    bool
        True if the current directory is a git repository, False otherwise.
    """
    try:
        res = get_output(["git", "rev-parse", "--is-inside-work-tree"])
        return res == "true"
    except subprocess.CalledProcessError:
        return False


if not is_git_repo():
    print("Not in a git repository")
    sys.exit(1)

commits = get_output(
    ["git", "log", "--pretty=format:%H %cD %s", "-n", str(N_COMMIT)]
).split("\n")


def fzf(choices: list[str]) -> str:
    """Pick an item from a list using fzf.

    Parameters
    ----------
    choices : list[str]
        The list of items to pick from.

    Returns
    -------
    str
        The selected item.
    """

    input_bytes = "\n".join(choices).encode("utf-8")
    out = subprocess.check_output(["fzf"], input=input_bytes)

    return out.decode("utf-8").strip()


CHOICE = fzf(commits)
COMMIT = CHOICE.split(" ", maxsplit=1)[0]


def get_date_of_commit(commit):
    return get_output(["git", "show", "-s", "--format=%cD", commit])


print("Current date:", get_date_of_commit(COMMIT))
print("Date of previous commit:", get_date_of_commit(COMMIT + "~"))

# Ask for new date
new_date = input("New date: ")

# Edit commit

env_filter = f"""
if [ $GIT_COMMIT = {COMMIT} ]
then
    export GIT_AUTHOR_DATE="{new_date}"
    export GIT_COMMITTER_DATE="{new_date}"
fi
"""

subprocess.run(["git", "filter-branch", "-f", "--env-filter", env_filter])
