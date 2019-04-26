#!/usr/bin/env python
# (C) GPLv3 Frederik M.J. Vestre - 2014, 2015
import re, os, subprocess, sys
reflogparse = re.compile(r"(?P<ooid>[0-9a-f]+) (?P<noid>[0-9a-f]+) (?P<name>.*?) (?P<email><.*?>) (?P<time>\d+) \+(?P<time_offset>\d+)\t?(?P<message>.*)$")
checkout_move = re.compile(r"checkout: moving from (?P<from>.*?) to (?P<to>.*?)$")

select_idx = None
filter_str = re.compile(r".*")

if len(sys.argv) >= 2:
    try:
        select_idx = int(sys.argv[1])
    except ValueError:
        filter_str = re.compile(str(sys.argv[1]))
        if len(sys.argv) >= 3:
            try:
                select_idx = int(sys.argv[2])
            except ValueError:
                pass


class logitem(object):
    def __init__(self, line):
        for name, value in reflogparse.match(line).groupdict().items():
            setattr(self, name, value)
        movematch = checkout_move.match(self.message)
        if movematch:
            self.move_from = movematch.group("from")
            self.move_to = movematch.group("to")

    def __repr__(self):
        return self.message

#  Find git directory
if len(sys.argv) > 1:
    curpath = sys.argv[1]
else:
    curpath = os.getcwd()
tmppath = curpath
while True:
    repo_path = os.path.join(tmppath, ".git")
    if os.path.exists(repo_path):
        break
    nextpath = os.path.abspath(os.path.join(tmppath, os.path.pardir))
    if nextpath == tmppath:
        raise Exception("No .git directory found in parent directories")
    tmppath = nextpath

# Parse log
log_contents = None
with open(os.path.join(repo_path, "logs", "HEAD"), 'rb') as lh:
    log_contents = lh.read().decode("utf-8")
log = [logitem(line) for line in log_contents.split("\n") if line]

# Get all known branches from git
git = subprocess.Popen(["git", "branch", "-a"], cwd=os.path.join(repo_path, os.path.pardir), stdout=subprocess.PIPE)
git_output = git.communicate()[0].decode("utf-8")
known_branches = [extracted_branch.strip() for extracted_branch in git_output.split("\n")]

# Create unique sorted branch list
branches = []
for item in reversed(log):
    if hasattr(item, "move_to") and item.move_to in known_branches and item.move_to not in [branch for branch in branches]:
        branches.append(item.move_to)
    if hasattr(item, "move_from") and item.move_from in known_branches and item.move_from not in [branch for branch in branches]:
        branches.append(item.move_from)

filtered_branches = [branch for branch in branches if filter_str.search(branch)]
# Print & prompt user
for i, branch in enumerate(filtered_branches[0:40]):
    print(i + 1, branch)
print("?")
sys.stdout.flush()

if len(filtered_branches) == 1:
    print("Only one branch matching.")
    nr = 1
elif select_idx is None:
    input_str = sys.stdin.readline()

    # Checkout selected path
    nr = None
    try:
        nr = int(input_str)
    except:
        pass
else:
    nr = select_idx

if nr and nr < len(filtered_branches) + 1:
    print("Select branch", nr, filtered_branches[nr - 1])
    # Must use git instead of libgit to do checkout to get correct info in the reflog
    subprocess.call(["git", "checkout", filtered_branches[nr - 1]], cwd=os.path.join(repo_path, os.path.pardir))
    if os.path.exists(os.path.join(repo_path, os.path.pardir, ".gitmodules")):
        subprocess.call(["git", "submodule", "foreach", "git", "submodule", "update"], cwd=os.path.join(repo_path, os.path.pardir))
        print("Updated submodule")
else:
    print("Cannot find a branch matching your input")
