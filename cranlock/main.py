import argparse
import subprocess
import sys
import os

from cranlock import lock

SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

DESCRIPTION = """
Locks all R dependencies and transitive dependencies for reproducible builds.
Relies on a docker image with the dependencies installed to sort out the proper
versions for transitive dependencies.
"""


def get_package_versions(container, version_file):
    # Get the package versions
    package_version_command = "{dir}/get_package_versions.sh {container} > {versions}"
    package_version_po = subprocess.Popen(package_version_command.format(dir=SCRIPT_DIRECTORY,
                                                                         container=container,
                                                                         versions=version_file),
                                          shell=True, stderr=subprocess.PIPE)

    for line in package_version_po.stderr:
        print(line.decode('utf-8'), end='', file=sys.stderr)

    package_version_po.wait()

    if package_version_po.returncode != 0:
        print("Error: could not get the package versions from the container '{}'"
              .format(container),
              file=sys.stderr)
        if os.path.exists(version_file):
            os.remove(version_file)
        sys.exit(1)


def main():
    # Initialize the argument parser
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('package_file', help='A list of packages to install, one per line')
    parser.add_argument('docker_container', nargs='?', help='A docker container holding a previous successful \
build to get the dependency versions from. Not required if \'version_file\' exists.')
    parser.add_argument('--version_file', help='A location for the versions file. \
The default is \'versions.tsv\' in the same directory as \'package_file\'.')
    parser.add_argument('--output_file', help='A location for the output R script. \
The default is \'dependencies.R\' in the same directory as \'package_file\'.')

    # Parse arguments
    args = parser.parse_args()
    package_file = os.path.realpath(args.package_file)
    container = args.docker_container
    # Handle fallbacks for optional arguments
    version_file = args.version_file or os.path.dirname(package_file) + '/versions.tsv'
    output_file = args.output_file or os.path.dirname(package_file) + '/dependencies.R'

    # Verify arguments
    if not os.path.isfile(package_file):
        print("Error: {} does not exist".format(package_file), file=sys.stderr)
        sys.exit(1)

    # Get package versions if a versions.tsv file does not already exist
    if not os.path.isfile(version_file):
        if container is None:
            print("Error: you must specify a docker container, since {} does not exist"
                  .format(version_file), file=sys.stderr)
            sys.exit(1)
        get_package_versions(container, version_file)

    # Parse the dependency tree and generate the final R script
    package_file = open(package_file, 'r')
    version_file = open(version_file, 'r')
    output_file = open(output_file, 'w')

    try:
        lock.main(package_file, version_file, output_file)
    except Exception as e:
        print(e)
        package_file.close()
        version_file.close()
        output_file.close()

        if os.path.exists(version_file):
            os.remove(version_file)

        if os.path.exists(output_file):
            os.remove(output_file)

        sys.exit(1)


if __name__ == "__main__":
    main()
