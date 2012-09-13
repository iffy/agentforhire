#!/usr/bin/env bash

files=$(python -c 'import glob, os
files = glob.glob("forhire/*.py")
result = []
for f in files:
    base = os.path.basename(f)
    if base.startswith("_"):
        continue
    result.append(os.path.splitext(f)[0].replace("/","."))
print " ".join(result)')

echo "$files"
trial $files
