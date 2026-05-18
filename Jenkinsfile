pipeline {
    agent any

    // Trigga automaticamente su push (via webhook GitHub)
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
    }

    stages {
        stage('🔍 Detect Release') {
            steps {
                script {
                    echo "Checking if this is a release tag..."
                    try {
                        // Ottieni il tag attuale (se esiste)
                        def tagName = sh(
                            script: 'git describe --exact-match --tags HEAD 2>/dev/null',
                            returnStdout: true
                        ).trim()
                        
                        // Verifica se matchla il pattern di versione
                        if (tagName =~ /^v\d+\.\d+\.\d+/) {
                            env.IS_RELEASE = 'true'
                            env.RELEASE_VERSION = tagName
                            echo "✅ RELEASE TAG DETECTED: $tagName"
                        } else {
                            env.IS_RELEASE = 'false'
                            echo "⏭️ Tag found but not a release: $tagName"
                        }
                    } catch (Exception e) {
                        env.IS_RELEASE = 'false'
                        env.RELEASE_VERSION = 'N/A'
                        echo "⏭️ No tag found - regular commit"
                    }
                }
            }
        }

        stage('📦 Setup Environment') {
            steps {
                script {
                    echo "Setting up Python environment..."
                    sh '''
                        set -eu
                        python3 --version
                        python3 -m venv ${VENV_DIR}
                        . ${VENV_DIR}/bin/activate
                        pip install --upgrade pip setuptools wheel
                        pip install build twine pytest pytest-cov mypy ruff black isort
                        pip install -e .
                        echo "✓ Environment ready"
                    '''
                }
            }
        }

        stage('🎨 Lint & Format') {
            when {
                expression {
                    return env.IS_RELEASE != 'true'  // Salta se è una release
                }
            }
            steps {
                script {
                    echo "Running code quality checks..."
                    sh '''
                        set -eu
                        . ${VENV_DIR}/bin/activate
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
        }

        stage('🧪 Run Tests') {
            steps {
                script {
                    echo "Running test suite..."
                    sh '''
                        set -eu
                        . ${VENV_DIR}/bin/activate
                        pytest tests/ -v --tb=short --cov=asteroidpy --cov-report=xml --junitxml=test-results.xml
                        if [ -f coverage.xml ]; then
                            echo "✓ Coverage report generated"
                        fi
                    '''
                }
            }
            post {
                always {
                    junit testResults: 'test-results.xml'
                }
            }
        }

        stage('🏗️ Build Package') {
            steps {
                script {
                    echo "Building distribution packages..."
                    sh '''
                        set -eu
                        . ${VENV_DIR}/bin/activate
                        rm -rf dist/ build/ *.egg-info
                        python -m build
                        echo "Build artifacts:"
                        ls -lh dist/
                    '''
                }
            }
        }

        stage('✅ Validate Package') {
            steps {
                script {
                    echo "Validating package metadata..."
                    sh '''
                        set -eu
                        . ${VENV_DIR}/bin/activate
                        twine check dist/* --strict
                    '''
                }
            }
        }

        stage('🧪 Test Installation') {
            steps {
                script {
                    echo "Testing package installation..."
                    sh '''
                        set -eu
                        . ${VENV_DIR}/bin/activate
                        python -m venv test-install
                        . test-install/bin/activate
                        pip install --quiet dist/asteroidpy-*.whl
                        python -c "import asteroidpy; print('✓ Package imported successfully')"
                        deactivate
                        rm -rf test-install
                    '''
                }
            }
        }

        stage('🚀 Publish to PyPI') {
            when {
                expression {
                    return env.IS_RELEASE == 'true'
                }
            }
            steps {
                script {
                    echo "🎉 Publishing ${env.RELEASE_VERSION} to PyPI..."
                    withCredentials([
                        string(credentialsId: 'PYPI_API_TOKEN', variable: 'PYPI_TOKEN')
                    ]) {
                        sh '''#!/usr/bin/env bash
                            set -euo pipefail
                            . ${VENV_DIR}/bin/activate

                            # Verifica versione
                            VERSION=$(grep -E '^__version__' asteroidpy/version.py | grep -oE '[0-9]+\\.[0-9]+\\.[0-9]+' | head -1)
                            TAG="${RELEASE_VERSION#v}"  # Rimuovi il 'v' dal tag
                            
                            if [ "$VERSION" != "$TAG" ]; then
                                echo "ERROR: Version mismatch — upload blocked."
                                echo "  asteroidpy/version.py: $VERSION"
                                echo "  Git tag: $TAG"
                                exit 1
                            fi
                            
                            # Upload
                            twine upload \
                                -u __token__ \
                                -p $PYPI_TOKEN \
                                --skip-existing \
                                dist/*
                            
                            echo "✓ Upload completed"
                        '''
                    }
                }
            }
        }

        stage('📢 Notify Success') {
            when {
                expression {
                    return env.IS_RELEASE == 'true'
                }
            }
            steps {
                script {
                    echo "Sending notifications..."
                    sh '''
                        echo "✅ Release ${RELEASE_VERSION} successfully published to PyPI!"
                        
                        # Opzionale: notifica via ntfy
                        # curl -X POST https://ntfy.example.com/asteroidpy \
                        #   -d "✅ ${RELEASE_VERSION} published to PyPI" \
                        #   -H "Priority: high"
                        
                        # Opzionale: notifica a Discord
                        # curl -X POST $DISCORD_WEBHOOK \
                        #   -H "Content-Type: application/json" \
                        #   -d "{\"content\":\"📦 asteroidpy ${RELEASE_VERSION} released!\"}"
                    '''
                }
            }
        }
    }

    post {
        always {
            script {
                echo "🧹 Cleaning up..."
                sh '''
                    rm -rf ${VENV_DIR} test-install build *.egg-info
                '''
            }
        }
        success {
            script {
                if (env.IS_RELEASE == 'true') {
                    echo "✅ Release Pipeline SUCCESS!"
                    currentBuild.description = "✅ Released ${env.RELEASE_VERSION}"
                } else {
                    echo "✅ Build Pipeline SUCCESS!"
                    currentBuild.description = "✅ Build successful"
                }
            }
        }
        failure {
            script {
                echo "❌ Pipeline FAILED!"
                currentBuild.description = "❌ Build failed"
                // Opzionale: notifica errore
                // sh 'curl -X POST https://ntfy.example.com/asteroidpy -d "❌ Build failed"'
            }
        }
    }
}
