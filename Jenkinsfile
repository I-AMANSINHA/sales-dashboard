pipeline {
    agent any

    environment {
        SERVER = "ubuntu@10.0.15.121"
        APP_DIR = "/home/ubuntu/python-app"
        PORT = "5004"
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Deploy') {
            steps {
                sh """
                ssh ${SERVER} << 'EOF'

                if [ ! -d "${APP_DIR}" ]; then
                    git clone https://github.com/<YOUR_USERNAME>/<YOUR_REPO>.git ${APP_DIR}
                else
                    cd ${APP_DIR}
                    git pull origin main
                fi

                cd ${APP_DIR}

                python3 -m venv venv || true

                source venv/bin/activate

                pip install -r requirements.txt

                pkill -f gunicorn || true

                nohup gunicorn \
                    --bind 0.0.0.0:${PORT} \
                    app:app \
                    > app.log 2>&1 &

                EOF
                """
            }
        }

    }
}
