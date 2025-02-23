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
