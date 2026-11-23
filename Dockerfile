FROM eclipse-temurin:25-jdk-alpine AS java-builder
RUN apk add --no-cache git
WORKDIR /build
ENV HOST=github.com
ENV ORG=ReceitaFederal
RUN git clone --depth 1 https://${HOST}/${ORG}/calculadora-rtc-regime-regular.git regular && \
    git clone --depth 1 https://${HOST}/${ORG}/calculadora-rtc-simples-nacional.git simples && \
    cp -r regular/flyway simples/
RUN cd regular && chmod +x mvnw && mkdir -p ../calculadora/db && ./mvnw flyway:migrate -Dflyway.configFiles=./flyway/flyway-pro.conf --batch-mode && ./mvnw clean package -DskipTests
RUN cd simples && chmod +x mvnw && mkdir -p ../calculadora/db && ./mvnw flyway:migrate -Dflyway.configFiles=./flyway/flyway-pro.conf --batch-mode && ./mvnw clean package -DskipTests

FROM golang:alpine AS go-builder
RUN apk add --no-cache git
WORKDIR /build
ENV HOST=github.com
ENV ORG=ReceitaFederal
RUN git clone --depth 1 https://${HOST}/${ORG}/calculadora-rtc-gerador-danfse.git . && go build -o danfse-service ./cmd/danfse

FROM eclipse-temurin:25-jre-alpine
RUN apk add --no-cache python3 py3-pip bash
WORKDIR /app
COPY --from=java-builder /build/regular/calculadora ./calculadora
COPY --from=java-builder /build/regular/target/*.jar ./api-regime-geral.jar
COPY --from=java-builder /build/simples/target/*.jar ./api-simples-nacional.jar
COPY --from=go-builder /build/danfse-service ./danfse-service
COPY backend ./backend
COPY frontend ./frontend
COPY start.sh ./start.sh
RUN chmod +x start.sh && pip3 install --no-cache-dir --break-system-packages -r backend/requirements.txt
CMD ["./start.sh"]
