pipeline {
    agent any
    environment {
        CONTAINER_NAME = "app-new"
        IMAGE_NAME = "app-image"
        APP_PORT = "5001"
        VOLUME_PATH = "/Users/liorkrispin/ism"
    }
    stages {
        stage('Clone Repository') {
            steps {
                git branch: 'main', url: 'https://github.com/liorkrispin/ism.git'
            }
        }
        stage('Build Docker Image') {
            steps {
                script {
                    sh "docker build -t ${IMAGE_NAME} ."
                }
            }
        }
        stage('Stop and Remove Old Container') {
            steps {
                script {
                    sh "docker stop ${CONTAINER_NAME} || true"
                    sh "docker rm ${CONTAINER_NAME} || true"
                }
            }
        }
        stage('Run New Container') {
            steps {
                script {
                    sh """
                    docker run -d -p ${APP_PORT}:${APP_PORT} --name ${CONTAINER_NAME} \
                    -v ${VOLUME_PATH}:/root/ism ${IMAGE_NAME} \
                    bash -c 'cd /root/ism && python3.9 app.py'
                    """
                }
            }
        }
    }
}
