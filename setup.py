from distutils.core import setup
from dendy import __version__

setup(
    name='dendy',
    version=__version__,
    description='Python micro web framework',
    author='cnds',
    author_email='dingsong87@gmail.com',
    license='MIT',
    url='https://github.com/cnds/dendy',
    packages=['dendy'],
    install_requires=['pyjwt>=1.5.0']
)
