import glob
from setuptools import setup

def findfiles(pat):
    #return [x[10:] for x in glob.glob('latex2edx/' + pat)]
    return [x for x in glob.glob('share/' + pat)]

data_files = [
    ('share/render', findfiles('render/*')),
    ('share/testtex', findfiles('testtex/*')),
    ('share/plastexpy', findfiles('plastexpy/*.py')),
    ]

with open("README.md", "r") as fh:
    long_description = fh.read()

# print "data_files = %s" % data_files

setup(
    name='latex2edx',
    version='1.6.2',
    author='I. Chuang',
    author_email='ichuang@mit.edu',
    packages=['latex2edx', 'latex2edx.test'],
    scripts=[],
    url='http://pypi.python.org/pypi/latex2edx/',
    license='LICENSE.txt',
    description='Converter from latex to edX XML format course content files',
    long_description=long_description,
    long_description_content_type="text/markdown",
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'latex2edx = latex2edx.main:CommandLine',
            ],
        },
    install_requires=['lxml',
                      'path.py',
                      'plastex==2.1',
                      'beautifulsoup4',
                      'latex2dnd',
                      'pyyaml',
                      ],
    package_dir={'latex2edx': 'latex2edx'},
    package_data={'latex2edx': ['render/*', 'testtex/*', 'plastexpy/*.py',
                                'python_lib/*.py', 'latex2edx.js',
                                'latex2edx.css']},
    # data_files = data_files,
    test_suite="latex2edx.test",
)
