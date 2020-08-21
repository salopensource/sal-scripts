import pathlib
from setuptools import setup


namespace = {}
path = (pathlib.Path(__file__).parent / 'sal/version.py').resolve()
exec(path.read_text(), namespace)

setup(
    name='sal',
    version=namespace['__version__'],
    description='Sal client utilities',
    install_requires=[
        'pyobjc == 6.2 ; platform_system=="Darwin"',
        'macsesh == 0.3.0 ; platform_system=="Darwin"',
        'requests >= 2.23.0'],
    packages=['sal'])