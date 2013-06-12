import sys
import os

from setuptools import setup, find_packages


here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()

version = '0.1dev'

requires = [
    'pymongo==2.5.1',
    'eduid_am',
]

testing_extras = [
    'nose==1.2.1',
    'nosexcover==1.0.8',
    'coverage==3.6',
]


setup(name='eduid-dashboard-amp',
      version=version,
      description="eduID DashboardAttribute Manager Plugin",
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
          # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      ],
      keywords='',
      author='NORDUnet A/S',
      author_email='',
      url='',
      license='',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      extra_requires={
          'testing': testing_extras,
      },
      test_suite='eduid_dashboard_amp',
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
