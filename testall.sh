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
ec1=$?

echo '----------------------------------------------------------------------'
echo 'pyflakes'
echo '----------------------------------------------------------------------'
pyflakes forhire
ec2=$?

if [ ! $ec1 -eq 0 ] || [ ! $ec2 -eq 0 ]; then
    exit 1
fi
