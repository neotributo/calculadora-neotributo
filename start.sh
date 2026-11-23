#!/bin/bash
java -Xmx320m -Dspring.profiles.active=offline -Dserver.port=8080 -jar api-regime-geral.jar &
java -Xmx256m -Dspring.profiles.active=offline -Dserver.port=8082 -jar api-simples-nacional.jar &
SERVER_PORT=8081 ./danfse-service &
sleep 12
uvicorn backend.main:app --host 0.0.0.0 --port 10000
