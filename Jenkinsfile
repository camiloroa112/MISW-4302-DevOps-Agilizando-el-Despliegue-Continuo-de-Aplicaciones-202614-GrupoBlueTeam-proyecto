
pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        UV_LINK_MODE = 'copy'
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Repositorio BlueTeam descargado desde GitHub'
                sh 'git rev-parse --short HEAD'
            }
        }

        stage('Setup') {
            steps {
                sh '''
                    uv --version
                    uv sync --frozen
                '''
            }
        }

        stage('Test') {
            steps {
                sh '''
                    mkdir -p reports

                    uv run --frozen --with pytest pytest tests/ -v \
                        --junitxml=reports/pytest-results.xml
                '''
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true,
                  testResults: 'reports/pytest-results.xml'
        }

        success {
            echo 'Pipeline y pruebas completadas correctamente'
        }

        failure {
            echo 'La pipeline ha fallado. Revisar Console Output.'
        }
    }
}
