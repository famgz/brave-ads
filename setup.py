from setuptools import setup, find_packages

with open('requirements.txt') as f:
    REQUIREMENTS = f.readlines()

setup(
    name='brave_ads',
    version='0.1',
    license='MIT',
    author="famgz",
    author_email='famgz@proton.me',
    url='https://github.com/famgz/brave-ads',
    packages=['brave_ads'],
    package_dir={'brave_ads': 'src/brave_ads'},
    include_dirs=True,
    include_package_data=True,
    install_requires=REQUIREMENTS
)
