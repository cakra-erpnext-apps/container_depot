from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# get version from __version__ variable in container_depot/__init__.py
from container_depot import __version__ as version

setup(
    name="container_depot",
    version=version,
    description="Container and ISO Tank Depot Management System",
    author="Oak Depot Team",
    author_email="info@oakdepot.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
