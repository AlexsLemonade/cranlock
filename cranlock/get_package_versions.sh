#!/bin/bash
# Get the versions of all R packages installed inside a dockerfile.

# This script should always run as if it were being called from
# the directory it lives in.
script_directory="$(perl -e 'use File::Basename;
 use Cwd "abs_path";
 print dirname(abs_path(@ARGV[0]));' -- "$0")"
cd "$script_directory" || exit

# Exit on errors
set -e

# Exit on errors inside pipes
set -o pipefail

if [ -n "$1" ]; then
    docker_image=$1
else
    echo "Error: missing docker image argument" >&2
    exit 1
fi

# Run list_dependencies, then discard the first row and print the 1st and 3rd columns
docker run -it "$docker_image" Rscript -e "$(cat ./list_dependencies.R)" \
    | tr -d '\r' | tail -n+2 | awk '{ print $1 "\t" $3 }'
