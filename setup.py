import re
from setuptools import setup


with open("README.md", "r") as fh:
    long_description = fh.read()


with open("jsonschema_cn/__init__.py") as fh:
    version = re.search(r'^__version__\s*=\s*["\'](.*)["\']', fh.read(), re.M).group(1)


setup(name='jsonschema_cn',
      version=version,
      description='Compact notation for JSON Schemas',
      long_description=long_description,
      long_description_content_type="text/markdown",
      url='http://github.com/fab13n/jsonschema_cn',
      author='Fabien Fleutot',
      author_email='fleutot@gmail.com',
      classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3.6',
        "Operating System :: OS Independent",
      ],
      keywords='DSL JSON schema jsonschema',
      license='BSD',
      packages=['jsonschema_cn'],
      install_requires=[
          'parsimonious>=0.8.0',
          'jsonschema>=3.0.1'
      ],
      entry_points={
          "console_scripts": ['jscn = jsonschema_cn.cli:main']
      },
)
