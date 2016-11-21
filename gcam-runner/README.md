Docker-hosted process to check for pending GCAM jobs and execute them.

Some commands:

docker build -t beaucronin/gcam-runner:latest .
docker push beaucronin/gcam-runner:latest
docker run -it --env-file aws_env --memory="6G" beaucronin/gcam-runner