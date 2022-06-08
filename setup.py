from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in annual_leave_tracker/__init__.py
from annual_leave_tracker import __version__ as version

setup(
	name="annual_leave_tracker",
	version=version,
	description="Annual Leave Tracker",
	author="dy",
	author_email="dy@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
