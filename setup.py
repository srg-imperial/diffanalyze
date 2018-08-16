try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = dict()

setup(
    name='diffanalyze',
    description='DiffAnalyze checks a set of commits of a git repository',
    author='David Buterez',
    url='',
    download_url='https://github.com/davidbuterez/diffanalyze',
    author_email='',
    version='0.1',
    packages=[],
    scripts=['diffanalyze.py'],
    install_requires=['pygit2', 'matplotlib', 'termcolor'],
    python_requires='>2.7',
)
