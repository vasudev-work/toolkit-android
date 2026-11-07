#!/usr/bin/env bash
# Downloads the Eclipse batch compiler used instead of javac (the JDK image
# that ships with some CI images has no javac binary) and creates a debug key.
set -euo pipefail
cd "$(dirname "$0")"

ECJ_VERSION="${ECJ_VERSION:-3.33.0}"
if [ ! -f ecj.jar ]; then
  echo "fetching ecj ${ECJ_VERSION}"
  curl -fsSL -o ecj.jar \
    "https://repo1.maven.org/maven2/org/eclipse/jdt/ecj/${ECJ_VERSION}/ecj-${ECJ_VERSION}.jar"
fi

if [ ! -f debug.keystore ]; then
  echo "creating debug.keystore (alias androiddebugkey, password 'android')"
  "${JAVA_HOME:?set JAVA_HOME}"/bin/keytool -genkeypair -v \
    -keystore debug.keystore -storetype PKCS12 \
    -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000 \
    -storepass android -keypass android \
    -dname "CN=Android Debug,O=Android,C=US" >/dev/null
fi
echo "dependencies ready"
