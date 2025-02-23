stage('Run New Container') {
    steps {
        script {
            sh """
            docker run -d --name ${CONTAINER_NAME} \
            --network mynetwork \
            -p ${APP_PORT}:${APP_PORT} \
            -v ${VOLUME_PATH}:/root/ism ${IMAGE_NAME} \
            bash -c 'cd /root/ism && python3.9 app.py'
            """
            
            # בדיקה שהקונטיינר באמת רץ
            sh "sleep 5 && docker logs ${CONTAINER_NAME} --tail 50"
        }
    }
}
