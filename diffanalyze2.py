#!/usr/bin/env python3
import contextlib
import json
import logging
import shutil
import subprocess
import tempfile
from collections import OrderedDict

import pygit2
import os
import sys

GIT_EMPTY_TREE_ID = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'


class FileAnalyzer:
    def __init__(self):
        # find ctags
        self.ctags = shutil.which('universalctags')
        if not self.ctags:
            self.ctags = shutil.which('ctags')
        if not self.ctags:
            raise FileNotFoundError(
                "universalctags or ctags not found make sure its executable is available in the searchable path")

    def analyse_file(self, path):
        """
        Analyse the given file and return tokens part of the analysed file
        :param path:
        :return:
        """
        if not os.path.isfile(path):
            raise FileNotFoundError("File '{}' to analyse does not exist or is not accessible.".format(path))
        proc = subprocess.Popen(
            [self.ctags,
             '--quiet=yes',  # Don't print any additional info
             '--C-kinds=fp',  # Generate: function definitions (f), function prototypes (p),
             '--C++-kinds=fp',  # Generate: function definitions (f), function prototypes (p)
             '--fields=+ne',  # Add line number and end of type information in output
             '--languages=C,C++',  # Restrict to C and C++
             '--output-format=json',  # Output ctags format as json
             path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        out, err = proc.communicate()

        if err:
            raise RuntimeError(err.decode('utf-8'))

        # ctags output format contains each entry as a dict per single line
        # Parse each line independently
        result = []
        for line in out.decode('utf-8').split('\n'):
            # skip empty lines - not parseable
            if not len(line):
                continue
            result += [json.loads(line)]
        return result

    def analyse_blob(self, blob, filename):
        """
        Analyse the provided blob and associated filename
        :param blob:
        :param filename:
        :return:
        """
        # Create tempfile for analysis
        with tempfile.NamedTemporaryFile(suffix=filename) as tf:
            # Write content
            tf.write(blob)
            tf.flush()
            return self.analyse_file(tf.name)


@contextlib.contextmanager
def temporary_repository(url):
    """
    Create a temporary repository of the provided url if needed.
    If the object goes out-of-scope remove the temporary directory

    :param url:
    :return:
    """
    delete_on_exit = False
    temporary_path = None
    try:
        if os.path.exists(url) and os.path.isdir(url):
            logging.info("Use existing path {}...".format(url))
            yield pygit2.Repository(url)
        else:
            temporary_path = tempfile.mkdtemp()
            delete_on_exit = True
            logging.info("Clone {} into {} ...".format(url, temporary_path))
            repository_clone = pygit2.clone_repository(url, temporary_path)
            yield repository_clone
    finally:
        if delete_on_exit and temporary_path:
            # Remove the directory if requested
            shutil.rmtree(temporary_path)


def generate_repository_changes(url, new_revision, old_revision):
    with temporary_repository(url) as repository:
        # Set start commit to parse from
        start_commit = repository.revparse_single(new_revision)

        # Iterate from the newest commit to the oldest
        walker = repository.walk(start_commit.id)  # type: pygit2.Walker

        # Mark commit and ancestors as not interesting if provided
        if old_revision:
            end_commit = repository.revparse_single(old_revision)
            walker.hide(end_commit.id)

        fa = FileAnalyzer()

        logging.info("Analyse")

        changes = []
        for commit in walker:  # type: pygit2.Commit
            commit_change = {}

            # Get parent commit if available otherwise use an empty tree commit
            for parent_commit in get_parent_or_empty_commit(repository, commit):
                patch_summary = gather_diff_information(repository, parent_commit, commit)
                logging.debug("Commit {}".format(commit.id))

                for single_change in patch_summary:
                    # Skip entries that don't have a new file, i.e. no content was added/modified, old files have
                    # been deleted
                    if "new_file" not in single_change:
                        continue

                    file_name = single_change['new_file']
                    file_blob = retrieve_file_from_commit(commit, file_name)

                    if isinstance(file_blob, pygit2.Commit):
                        logging.warning(
                            "Submodule update detected {} but currently not supported.".format(file_blob.name))
                        continue

                    # Extract all the functions from the file, their start and their end
                    # TODO Add name demangling to fully support C++
                    file_structure = fa.analyse_blob(file_blob.data, file_blob.name)
                    # Select name, start line and end line. `end line` might not be available assume large file
                    functions = [{'name': f.get('name'), 'start': f.get('line'), 'end': f.get('end')} for f in
                                 file_structure if f.get("kind", "") == "function"]

                    # Iterate over all patch changes and check to which function they map
                    for change in single_change['changes']:
                        # Skip removals
                        if change['add'] == -1:
                            continue
                        for f in functions:
                            if not f['end']:
                                logging.warning(
                                    "Function end for {} unknown in commit {}. Ignoring.".format(f['name'], commit.id))
                                continue
                            match = False
                            change_start = change['add']
                            change_end = change_start + change['nr']

                            # Check if the beginning of patch inside of the function
                            if f['start'] <= change_start <= f['end']:
                                match = True

                            # Check if the end of the patch is inside the function
                            if f['start'] <= change_end <= f['end']:
                                match = True

                            # Check if the function is inside the patch
                            if change_start <= f['start'] <= change_end:
                                match = True

                            if not match:
                                continue

                            commit_change.setdefault(file_name, {}).setdefault(f['name'], []).append(
                                (change_start, change_end))
            changes.append((str(commit.id), commit_change))

    return changes


def retrieve_file_from_commit(commit, file_name) -> pygit2.Blob:
    """
    Retrieves the file associated with the commit
    :param commit: commit to extract the file from
    :param file_name: name of the file
    :return:
    """

    # file_name is split into its elements
    path_elements = []
    while len(file_name):
        (file_name, tail) = os.path.split(file_name)
        path_elements.insert(0, tail)
    tree = commit.tree  # type: pygit2.Tree

    # Walk the tree using the elements
    for e in path_elements:
        tree = tree / e  # type: pygit2.Tree

    # The last element refers to actual file
    return tree


def get_parent_or_empty_commit(repository, child_commit):
    """
    Returns a list of parent commits for the provided child commit or an empty commit if the child commit is the initial commit of the repository
    :param repository:
    :param child_commit:
    :return:
    """
    return child_commit.parents if len(child_commit.parents) else [repository.revparse_single(GIT_EMPTY_TREE_ID)]


def gather_diff_information(repository, left_side_commit, right_side_commit):
    """
    Generate the diff information of two commits for the provided repository
    :param repository:
    :param left_side_commit:
    :param right_side_commit:
    :return: list of commit summaries
    """
    diff: pygit2.Diff = repository.diff(left_side_commit, right_side_commit, context_lines=0)

    commit_summary = []
    for patch in diff:  # type: pygit2.Patch
        patch_summary = dict({'changes': []})
        new_file: pygit2.DiffFile = patch.delta.new_file
        old_file: pygit2.DiffFile = patch.delta.old_file

        # Check if the file has been deleted, in that case `new_file` won't be set
        if patch.delta.status != pygit2.GIT_DELTA_DELETED:
            patch_summary['new_file'] = new_file.path

        # If the file has just been added, `old_file` won't be set
        if patch.delta.status != pygit2.GIT_DELTA_ADDED:
            patch_summary['old_file'] = old_file.path

        for hunk in patch.hunks:  # type: pygit2.DiffHunk
            for line in hunk.lines:  # type: pygit2.DiffLine
                patch_summary['changes'].append(
                    {'add': line.new_lineno, 'remove': line.old_lineno, 'nr': line.num_lines, 'origin': line.origin})

        commit_summary.append(patch_summary)
    return commit_summary


def main(main_args):
    # Parse arguments from command line
    import argparse
    parser = argparse.ArgumentParser(
        description='Analyses patches of a repository')
    parser.add_argument('repo', help='git repository: url or local path')
    parser.add_argument('--new-revision', help='newest target revision (including) [HEAD]', default="HEAD")
    parser.add_argument('--old-revision', help='oldest target revision (excluding) [First]', default=None)
    parser.add_argument('--log', help='Set the log level', default="WARNING")
    args = parser.parse_args(main_args)

    # Setup logging
    numeric_level = getattr(logging, args.log.upper())
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % args.log)
    logging.basicConfig(format='%(levelname)s:%(message)s', level=numeric_level)

    results = generate_repository_changes(args.repo, args.new_revision, args.old_revision)
    print(json.dumps(results, indent=1))


if __name__ == '__main__':
    main(sys.argv[1:])
