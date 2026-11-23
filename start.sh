#!/bin/bash
SERVER_PORT=8081 /app/danfse-service &
java -Xmx180m -Xms64m -XX:+UseSerialGC -Dserver.port=8080 -Dspring.profiles.active=offline -jar /app/api-regime-geral.jar &
java -Xmx160m -Xms64m -XX:+UseSerialGC -Dserver.port=8082 -Dspring.profiles.active=offline -jar /app/api-simples-nacional.jar &
uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-10000}
