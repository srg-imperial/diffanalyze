# diffanalyze
Script to extract useful patch testing information from git repositories. Currently, it is intended for use only with C programs.

## Usage
diffanalyze has two main functionalities, which will be explained in detail:
- Output the updated functions and corresponding code lines of a patch, given a commit hash
- Look at all the commits in a repository and output histograms that relate the number of updated functions to the number of commits

The information given below can also be briefly accessed via the `--help, -h` flags.

### Updated functions
Sample usage:
```
./diffanalyze.py https://git.savannah.gnu.org/git/findutils.git --revision HEAD --print-mode full
# show last 4 patches
./diffanalyze.py https://git.savannah.gnu.org/git/findutils.git --revision HEAD --range HEAD~4 --print-mode full
# show functions with added lines from last two commits
./diffanalyze.py /path/repo --revision HEAD --range HEAD~2 --print-mode=functions --with-hash --only-added
# show file,function,line for all added lines from last two commits
./diffanalyze.py /path/repo --revision HEAD --range HEAD~1 --print-mode simple
```

The first argument is always required: it is the URL of the repo that is to be queried

Optional arguments:
- `--revision HASH` - this is the patch commit hash we are interested in; the script will compare this revision to the previos one and output the patch updates. It supports normal git revision features: `HEAD~`, `HEAD^3`, `ba6be28~2`, etc.
- `--print-mode` - has 3 possible values: *full*, *simple*, *only-fn*.
    - `full` - prints a human readable version, including the updated function name, source file, and newly added lines
    - `simple` - outputs the source file name and source code line number, for each newly added line in the patch
    - `only-fn` - outputs only the names of the functions that were updated in the patch, one per line
    - `functions` - prints list of file,function,hash
- `--with-hash` - print git hashes in --print-mode=functions
- `--only-added` - print only added lines in --print-mode=functions
- `--verbose` - prints some additional information about what the script is doing (repo already cloned, current commit, etc.)
- `--rangeInt, -ri N` - Looks at N patches, starting from `HASH` (directions is newer -> older commits)
- `--range, -rh INIT_HASH` - Looks at patches between `HASH` (newest) and `INIT_HASH` (oldest) (inclusive, directions is newer -> older commits)

### Histogram
Sample usage:
`./diffanalyze.py https://git.savannah.gnu.org/git/findutils.git -sp`

Arguments:
- `--summary, -s` - prints a summary of the data (how many commits update N functions, how many file extensions were involved in commits, etc.)
- `--plot, -p` - saves a graph of the data given in the summary
- `--skip-initial, -i` - skip the initial commit, as it may very large and not of interest
- `--limit, -l N` - only plot the data of the first N commits (e.g. first 25 commits)
- `--rangeInt, -ri N` - same as above
- `--range, -rh INIT_HASH` - same as above

## Installation
### Ubuntu
If you are using Ubuntu, run the **setup.sh** script:
    `./setup.sh`

This will check and install any missing packages and libraries. The script was tested on a fresh install of Ubuntu 16.04 and Ubuntu 18.04, where the following will be required:

- python3
- pip3
- python3-dev
- git
- cmake
- openssl
- autoconf
- pkg-config
- libffi6 
- libffi-dev
- libssl-dev
- libjansson-dev
- libjansson4

Python also requires the following modules:
- pygit2
- matplotlib
  ```pip3 install --user matplotlib```
- termcolor
  ```pip3 install --user termcolor```

These will be installed automatically by the script (pygit2 is the most problematic, if the script could not install it, it will provide a link to the official installation guide).

The default version of *ctags* that is available on Ubuntu is *Exuberant Ctags*. diffanalyze requires *Universal Ctags*, which provides additional features. The setup script will install the required version as **universalctags** (should avoid conflicts with the default one).

### Mac OS X
Tested on Mac OS X Sierra (10.12).
Make sure you have `git`,`python3` and `pip3` installed.
Assuming you have `brew` installed:
- `brew install jansson`
- `brew install libgit2`
- `pip3 install pygit2`
- `pip3 installl matplotlib`
- `pip3 install pyqt5`
- `pip3 install termcolor`
- `brew install --HEAD universal-ctags/universal-ctags/universal-ctags`
## Known issues
The matplotlib graphs can look weird when inspecting a small number (e.g. 4) of patches with the `--range` arguments.

## Requirements

* install dependencies: `pip3 install --user -e .`
* Use ```python3 setup.py --user``` to install it
* Use ```python3 setup.py --user develop``` for development
