#!/bin/bash
VERSION=$1
if [[ "$VERSION" == "" ]]; then
    CURRENT_VERSION=$(cat jsonschema_cn/__init__.py | grep '^\s*__version__\s*=' | cut -d'"' -f2)
    echo "Usage: $0 <new_version number>. Current version is $CURRENT_VERSION."
    if git tag | grep -q "^v$CURRENT_VERSION$"; then
        echo "This version has already been tagged."
    else
        echo "This version has not been tagged yet."
    fi
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
