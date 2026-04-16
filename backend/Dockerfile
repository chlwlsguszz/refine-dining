# 1) Build stage
FROM gradle:8.10-jdk17 AS builder
WORKDIR /app

COPY . .
RUN gradle clean bootJar --no-daemon

# 2) Run stage
FROM eclipse-temurin:17-jre
WORKDIR /app

COPY --from=builder /app/build/libs/*.jar app.jar

EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]