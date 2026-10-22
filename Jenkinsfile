
pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                echo 'Repositorio GitHub conectado correctamente'
            }
        }

        stage('Build') {
            steps {
                echo 'Iniciando la compilacion del proyecto DevOps'
            }
        }

        stage('Test') {
            steps {
                echo 'Verificando la ejecucion de la pipeline'
            }
        }
    }

    post {
        success {
            echo 'Pipeline ejecutada exitosamente'
        }
        failure {
            echo 'La pipeline ha fallado'
        }
    }
}
