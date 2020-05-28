#!/usr/bin/env python
# encoding: utf-8


from setuptools import setup, find_packages
from pyscisci import __package__, __description__, __version__


setup(name=__package__,
      version=__version__,
      description='Science of Science',
      long_description=__description__,
      classifiers=[
            'Development Status :: 4 - Beta',
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 3.7',
            'Intended Audience :: Science/Research',
            'Topic :: Scientific/Engineering :: Information Analysis',
      ],
      keywords="science of science",
      url="https://github.com/ajgates42/pyscisci",
      author = 'Alex Gates <ajgates42@gmail.com>',
      license="MIT",
      packages = find_packages(),
      install_requires=[
            'pandas',
            'numpy',
            'scipy',
            #'networkx',
            #'python-igraph',
            'pytables',
            'nameparser',
            'lxml',
            'requests',
            'unidecode',
            'tqdm'
      ],
      include_package_data=True
      )
