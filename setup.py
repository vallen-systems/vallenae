from setuptools import setup, find_packages

with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    licensee = f.read()

setup(
    name='vallenae',
    version='0.0.1',
    description='Vallen Python Tools to Access *.pridb / *.tradb Files',
    long_description=readme,
    author='Daniel Altmann, the Vallen Software Team',
    author_email='software@vallen.de',
    # url='https://github.com/....', to be defined
    license=licensee,
    packages=find_packages(exclude=('tests', 'docs')),
    install_requires=['matplotlib', 'numpy', 'soundfile', 'pandas', 'pytest',
                      'numba', 'scipy']
)
