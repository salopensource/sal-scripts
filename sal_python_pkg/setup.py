import pathlib
from setuptools import setup


namespace = {}
path = (pathlib.Path(__file__).parent / 'sal/version.py').resolve()
exec(path.read_text(), namespace)

setup(
    name='sal',
    version=namespace['__version__'],
    description='Sal client utilities',
    packages=['sal'])