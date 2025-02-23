pipeline {
    agent any
    
    environment {
        APP_PORT = '5001'
        CONTAINER_NAME = 'app-new'
        VOLUME_PATH = '/Users/liorkrispin/ism'
        IMAGE_NAME = 'app-image'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
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
