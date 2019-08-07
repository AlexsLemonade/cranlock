import argparse
from bs4 import BeautifulSoup
from enum import Enum
from functools import reduce
import os
import re
import requests

CRAN_PACKAGE_URL_FORMAT = "https://cran.r-project.org/web/packages/{package}/index.html"


def get_cran_url(package_name: str) -> str:
    return CRAN_PACKAGE_URL_FORMAT.format(package=package_name)


def get_table_row(table, td_text):
    """ Find a row in a table that has td_text as one column's text """
    td = table.find('td', string=td_text)

    if td is None:
        return None

    return td.find_parent('tr')


# Cache the responses for all CRAN URLs we have visited, since a package often appears more than
# once in a dependency tree.
url_cache = dict()


def get_info_table(package: str):
    """Get the HTML table from the CRAN site for a package, which holds all the dependency info"""
    url = get_cran_url(package)
    if url_cache.get(url, None):
        response = url_cache[url]
    else:
        response = requests.get(url)
        url_cache[url] = response

    if response.status_code != 200:
        raise Exception("Package {} does not exist on CRAN".format(package))

    soup = BeautifulSoup(response.text, 'html.parser')

    # Dependency information lives in an html table called 'Package $PKGNAME summary'
    return soup.find('table', summary=re.compile('Package [\\w\\W]+ summary'))


def get_dependencies(package: str):
    """ Get all of the packages that a package `depends` or `imports` whose names are links.
    (If their names aren't links, they're base packages that we don't need to worry about)
    """

    table = get_info_table(package)

    imports_row = get_table_row(table, "Imports:")
    depends_row = get_table_row(table, "Depends:")

    imports = imports_row.find_all('a') if imports_row is not None else []
    depends = depends_row.find_all('a') if depends_row is not None else []

    return list(map(lambda a: a.string, imports + depends))


# Cache the dependencies for every dependency, because packages often appear multiple times in
# the depedency tree.
dependencies_cache = dict()


def get_all_dependencies(package: str):
    """Recursively finds all the dependencies of a package, and builds up a dependency tree"""
    if dependencies_cache.get(package, None) is not None:
        return dependencies_cache[package]

    first_level_dependencies = get_dependencies(package)

    if first_level_dependencies == []:
        return []

    # Construct a dict from a list of tuples so that the reducer doesn't mutate anything
    return dict(reduce(lambda deps, dependency:
                       deps + [(dependency, get_all_dependencies(dependency))],
                       first_level_dependencies, []))


def add_to_graph(graph: dict, dependency_tree):
    """Add a dependency tree to our depedency graph recursively. This truns the tree into a
    (hopefully) directed acyclic graph that we can sort using a depth-first search.
    """
    if len(dependency_tree.keys()) == 0:
        return

    for dep, nesteds in dependency_tree.items():

        if graph.get(dep, None) is None:
            graph[dep] = set()

        if nesteds == []:
            continue

        for nested in nesteds.keys():
            graph[dep].add(nested)

        add_to_graph(graph, nesteds)


def get_dependency_graph(packages: [str]):
    """Get the dependency graph for a list of packages by getting the tree for each one then
    adding them to a graph using `add_to_graph`"""
    dependencies = dict(map(lambda package: (package, get_all_dependencies(package)), packages))

    graph = {}
    add_to_graph(graph, dependencies)
    return graph


class Mark(Enum):
    Permanent = 0
    Temporary = 1
    Empty = 2


def have_visited_all(visited: dict) -> bool:
    """Have we visited all the nodes in the graph?"""
    for mark in visited.values():
        if mark == Mark.Empty:
            return False

    return True


def get_first_unvisited(visited: dict) -> str:
    """Get the first unvisited node in the graph, or None if we've visited all of them"""
    for (key, mark) in visited.items():
        if mark == Mark.Empty:
            return key

    return None


def visit(graph, node, visited, output):
    """Visit a node in a depth-first search"""
    mark = visited[node]
    if mark == Mark.Permanent:
        return
    elif mark == Mark.Temporary:
        # This should (hopefully) never happen because package dependencies *shouldn't* have cycles
        raise Exception("Somehow, the dependency graph is not directed and acyclic")

    visited[node] = Mark.Temporary

    for child_node in graph[node]:
        visit(graph, child_node, visited, output)

    visited[node] = Mark.Permanent

    # Append the nodes, rather than adding them to the head, because we want to install
    # dependencies before their dependents
    output.append(node)


def sort_dependency_graph(graph: dict):
    """Sort the dependency graph into a list using depth-first search"""
    visited = dict.fromkeys(graph.keys(), Mark.Empty)

    output = []

    while not have_visited_all(visited):
        node = get_first_unvisited(visited)

        visit(graph, node, visited, output)

        visited[node] = True

    return output


def extract_name_and_version(input_line: str) -> (str, str):
    """Extract the name and version of a package from an input line from a versions.tsv file.
    The file format is TSV, with the name in the first column and the version in the second
    """
    info = list(filter(lambda s: len(s) > 0, input_line.strip().split('\t')))
    name = info[0]
    version = info[1]
    return (name, version)


def main(input_file, version_file, output_file):
    # Get the requested version of every package using extract_name_and_version
    versions = dict(map(extract_name_and_version, version_file))

    # Build a dependency graph from all the requested dependencies then sort it
    graph = get_dependency_graph([line.strip() for line in input_file])
    sorted_packages = sort_dependency_graph(graph)

    # Write the output file
    output_file.write("# Generated from cranlock\n")
    output_file.write("options(warn=2)\n")
    output_file.write("options(Ncpus=parallel::detectCores())\n")
    output_file.write("options(repos=structure(c(CRAN=\"https://cran.revolutionanalytics.com\")))\n")
    for package in sorted_packages:
        if package in versions:
            output_file.write("devtools::install_version('{package}', version='{version}')\n".format(
                package=package, version=versions[package]))


if __name__ == "__main__":
    # Initialize the argument parser
    parser = argparse.ArgumentParser(description='Parse a list of R dependencies and topologically \
sort the dependency graph.')
    parser.add_argument('input_file', type=argparse.FileType('r'),
                        help='the input file for the dependencies')
    parser.add_argument('version_file', type=argparse.FileType('r'),
                        help='the file containing the version for each dependency')
    parser.add_argument('--output-file', type=argparse.FileType('r'),
                        help='the output file, or dependencies.R if none is specified')

    # Parse the arguments into variables
    args = parser.parse_args()
    input_file = args.input_file
    version_file = args.version_file
    output_file = args.output_file
    if output_file is None:
        output_file = open(os.path.dirname(input_file) + "/dependencies.R", 'w')

    main(input_file, version_file, output_file)
