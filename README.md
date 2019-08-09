# cranlock
Lock our R dependencies to specific versions.

## Introduction
A problem we've had using R inside docker is that builds are still not reproducible.
We pin dependencies to specific versions, but if their dependencies change, everything can still
silently break. Using this script, we can pin all of the dependencies of each of our
dependencies using `devtools::install_version`. Importantly, we use CRAN's website to topologically
sort the dependency graph of your packages before installing them. In other words, we install all
the packes in the proper order so that devtools should never have to download a package without
a specified version. We use a known-good docker image to get all of the versions of packages to install.

## Installation
To install `cranlock`, download one of the `.whl` files from Github's releases and run `pip install
path_to_whl`. Alternatively, you can follow the directions below for building your own wheel.

## Usage
Before you start, you should have a docker image with the correct version of all of your R packages
already installed. You need to do the R package installations via the `Dockerfile` so that the
packages are accessible from a fresh `docker run -it`. You should also have a `packages.txt` file
holding the names of all of your dependencies, one per line.

To create a `dependencies.R` file, run `cranlock path_to_packages/packages.txt docker_container_name`.
This will create a `versions.tsv` file holding the versions of all the R packages installed in your
selected docker container, then use that file along with `packages.txt` to generate `dependencies.R`.

NOTE: `cranlock` may take a while to run with large dependency trees, because we need to visit the
web page for each package to get its dependencies.

## Development
This project uses `pipenv`, so when you clone the project run `pipenv install` to install the
dependencies. To activate a virtual environment, use `pipenv shell`. The virtual environment
contains all of the dependencies to build the package, along with all of the dependencies for
testing the script. To build a release, you can either run
`pipenv run python3 setup.py bdist_wheel`, or you can run `python3 setup.py bdist_wheel` inside the
virtual environment.
