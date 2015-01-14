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

# print "data_files = %s" % data_files

setup(
    name='latex2edx',
    version='1.4.0',
    author='I. Chuang',
    author_email='ichuang@mit.edu',
    packages=['latex2edx', 'latex2edx.test'],
    scripts=[],
    url='http://pypi.python.org/pypi/latex2edx/',
    license='LICENSE.txt',
    description='Converter from latex to edX XML format course content files.',
    long_description=open('README.txt').read(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'latex2edx = latex2edx.main:CommandLine',
            ],
        },
    install_requires=['lxml',
                      'path.py',
                      'plastex',
                      'beautifulsoup',
                      'latex2dnd',
                      ],
    package_dir={'latex2edx': 'latex2edx'},
    package_data={ 'latex2edx': ['render/*', 'testtex/*', 'plastexpy/*.py', 'python_lib/*.py'] },
    # data_files = data_files,
    test_suite = "latex2edx.test",
)

