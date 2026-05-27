pipeline {
    agent any

    triggers {
        githubPush()
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '15'))
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
    }

    environment {
        VENV_DIR = '.venv'
        SONAR_HOST_URL = 'https://sq.casapomininegri.it'
        SONAR_SCANNER_VERSION = '6.2.1.4610'
    }

    stages {
        stage('Detect Release') {
            steps {
                script {
                    echo 'Checking if this is a release tag...'
                    def tagName = env.TAG_NAME?.trim()
                    if (!tagName) {
                        tagName = env.GIT_TAG?.trim()
                    }
                    if (!tagName) {
                        try {
                            tagName = sh(
                                script: 'git describe --exact-match --tags HEAD 2>/dev/null',
                                returnStdout: true
                            ).trim()
                        } catch (Exception ignored) {
                            tagName = ''
                        }
                    }

                    if (tagName =~ /^v\d+\.\d+\.\d+/) {
                        env.IS_RELEASE = 'true'
                        env.RELEASE_VERSION = tagName
                        echo "Release tag detected: ${tagName}"
                    } else {
                        env.IS_RELEASE = 'false'
                        env.RELEASE_VERSION = 'N/A'
                        if (tagName) {
                            echo "Tag found but not a release: ${tagName}"
                        } else {
                            echo 'No release tag found - regular commit build'
                        }
                    }
                }
            }
        }

        stage('Setup Environment') {
            steps {
                sh '''#!/usr/bin/env bash
                    set -euo pipefail

                    activate_venv() {
                        . "${VENV_DIR}/bin/activate"
                    }

                    ensure_msgfmt() {
                        if command -v msgfmt >/dev/null 2>&1; then
                            return 0
                        fi
                        echo "msgfmt not found; attempting to install gettext..."
                        if command -v apt-get >/dev/null 2>&1; then
                            sudo apt-get update -qq
                            sudo apt-get install -y gettext
                        elif command -v dnf >/dev/null 2>&1; then
                            sudo dnf install -y gettext
                        elif command -v yum >/dev/null 2>&1; then
                            sudo yum install -y gettext
                        fi
                        if ! command -v msgfmt >/dev/null 2>&1; then
                            echo "ERROR: msgfmt unavailable. Install gettext on the Jenkins agent or grant sudo for apt/dnf/yum."
                            exit 1
                        fi
                    }

                    python3 --version
                    python3 -m venv "${VENV_DIR}"
                    activate_venv
                    pip install --upgrade pip setuptools wheel
                    pip install build twine pytest-cov
                    pip install -e ".[dev]"
                    ensure_msgfmt
                    echo "Environment ready"
                '''
            }
        }

        stage('Lint') {
            steps {
                sh '''#!/usr/bin/env bash
                    set -euo pipefail
                    . "${VENV_DIR}/bin/activate"

                    echo "Checking with ruff..."
                    ruff check asteroidpy/ tests/
                    echo "Checking types with mypy..."
                    mypy asteroidpy/
                    echo "Checking import order with isort..."
                    isort --check asteroidpy/ tests/
                    echo "Checking format with black..."
                    black --check asteroidpy/ tests/
                '''
            }
        }

        stage('Test') {
            steps {
                sh '''#!/usr/bin/env bash
                    set -euo pipefail
                    . "${VENV_DIR}/bin/activate"
                    pytest tests/ -v --tb=short --cov=asteroidpy --cov-report=xml --junitxml=test-results.xml
                '''
            }
            post {
                always {
                    junit testResults: 'test-results.xml', allowEmptyResults: false
                }
            }
        }

        // Informational only: SonarQube never fails the build (findings or scanner errors).
        stage('SonarQube Analysis') {
            steps {
                catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE', message: 'SonarQube analysis failed (non-blocking)') {
                    withCredentials([
                        string(credentialsId: 'SONAR_TOKEN', variable: 'SONAR_TOKEN')
                    ]) {
                        sh '''#!/usr/bin/env bash
                            set -euo pipefail

                            ensure_sonar_scanner() {
                                if command -v sonar-scanner >/dev/null 2>&1; then
                                    return 0
                                fi
                                local scanner_zip="/tmp/sonar-scanner-cli-${SONAR_SCANNER_VERSION}-linux-x64.zip"
                                local scanner_dir="/tmp/sonar-scanner-${SONAR_SCANNER_VERSION}-linux-x64"
                                echo "Downloading SonarScanner ${SONAR_SCANNER_VERSION}..."
                                curl -fsSL \
                                    "https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-${SONAR_SCANNER_VERSION}-linux-x64.zip" \
                                    -o "${scanner_zip}"
                                rm -rf "${scanner_dir}"
                                unzip -q "${scanner_zip}" -d /tmp
                                export PATH="${scanner_dir}/bin:${PATH}"
                            }

                            ensure_sonar_scanner

                            sonar-scanner \
                                -Dsonar.host.url="${SONAR_HOST_URL}" \
                                -Dsonar.token="${SONAR_TOKEN}" \
                                -Dsonar.projectVersion="${GIT_COMMIT:-unknown}" \
                                -Dsonar.qualitygate.wait=false
                        '''
                    }
                }
            }
        }

        stage('Build Package') {
            steps {
                sh '''#!/usr/bin/env bash
                    set -euo pipefail
                    . "${VENV_DIR}/bin/activate"
                    rm -rf dist/ build/ *.egg-info

                    echo "Compiling locale catalogs..."
                    for po in asteroidpy/locales/*/LC_MESSAGES/base.po; do
                        msgfmt -o "${po%.po}.mo" "$po"
                    done

                    python -m build
                    ls -lh dist/
                '''
            }
        }

        stage('Validate Package') {
            steps {
                sh '''#!/usr/bin/env bash
                    set -euo pipefail
                    . "${VENV_DIR}/bin/activate"
                    twine check dist/* --strict
                '''
            }
        }

        stage('Install Smoke Test') {
            steps {
                sh '''#!/usr/bin/env bash
                    set -euo pipefail
                    . "${VENV_DIR}/bin/activate"
                    python -m venv test-install
                    . test-install/bin/activate
                    pip install --quiet dist/asteroidpy-*.whl
                    python -c "import asteroidpy; print('Package imported successfully')"
                    python -c "from importlib.resources import files; mo = files('asteroidpy') / 'locales/en/LC_MESSAGES/base.mo'; assert mo.is_file(), mo; print('Locale catalogs packaged')"
                    python -c "from importlib.metadata import entry_points; matches = [ep for ep in entry_points(group='console_scripts') if ep.name == 'asteroidpy']; assert len(matches) == 1 and matches[0].value == 'asteroidpy:main', matches; print('Console script entry point registered')"
                    command -v asteroidpy >/dev/null
                    deactivate
                    rm -rf test-install
                '''
            }
        }

        stage('Publish to PyPI') {
            when {
                expression {
                    return env.IS_RELEASE == 'true'
                }
            }
            steps {
                script {
                    echo "Publishing ${env.RELEASE_VERSION} to PyPI..."
                    withCredentials([
                        string(credentialsId: 'PYPI_API_TOKEN', variable: 'PYPI_TOKEN')
                    ]) {
                        sh '''#!/usr/bin/env bash
                            set -euo pipefail
                            . "${VENV_DIR}/bin/activate"

                            VERSION=$(grep -E '^__version__' asteroidpy/version.py | grep -oE '[0-9]+\\.[0-9]+\\.[0-9]+' | head -1)
                            TAG="${RELEASE_VERSION#v}"

                            if [ "$VERSION" != "$TAG" ]; then
                                echo "ERROR: Version mismatch — upload blocked."
                                echo "  asteroidpy/version.py: $VERSION"
                                echo "  Git tag: $TAG"
                                exit 1
                            fi

                            twine upload \
                                -u __token__ \
                                -p "$PYPI_TOKEN" \
                                --skip-existing \
                                dist/*

                            echo "Upload completed"
                        '''
                    }
                }
            }
        }

        stage('Notify Success') {
            when {
                expression {
                    return env.IS_RELEASE == 'true'
                }
            }
            steps {
                echo "Release ${env.RELEASE_VERSION} successfully published to PyPI"
            }
        }
    }

    post {
        always {
            sh '''
                rm -rf ${VENV_DIR} test-install build *.egg-info
                rm -rf /tmp/sonar-scanner-* /tmp/sonar-scanner-cli-*.zip
            '''
        }
        success {
            archiveArtifacts artifacts: 'dist/*', fingerprint: true, allowEmptyArchive: false
            archiveArtifacts artifacts: 'coverage.xml', allowEmptyArchive: true
            script {
                if (env.IS_RELEASE == 'true') {
                    currentBuild.description = "Released ${env.RELEASE_VERSION}"
                } else {
                    currentBuild.description = 'Build successful'
                }
            }
        }
        failure {
            script {
                currentBuild.description = 'Build failed'
            }
        }
    }
}
