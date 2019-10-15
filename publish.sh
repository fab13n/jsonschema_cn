#!/bin/bash
VERSION=$1
if [[ "$VERSION" == "" ]]; then
    echo "Usage: $0 <version number>"
    exit 1
fi

sed -i "s/^__version__\\s*=.*/__version__ = \"$VERSION\"/" jsonschema_cn/__init__.py

git commit -am "Published version $VERSION"
git tag -a "v$VERSION" -m "Published version $VERSION"
git push

python3 setup.py sdist bdist_wheel && \
. .credentials && \
twine upload \
      --username "$LOGIN" \
      --password "$PASSWORD" \
      --repository-url https://upload.pypi.org/legacy/ \
      dist/*
