import contextlib
import os
import shutil
import tempfile


@contextlib.contextmanager
def make_temp_directory():
    temp_dir = tempfile.mkdtemp('l2etmp')
    current_dir = os.getcwd()
    yield temp_dir
    os.chdir(current_dir)
    shutil.rmtree(temp_dir)
