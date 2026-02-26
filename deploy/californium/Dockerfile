FROM maven:3.9.9-eclipse-temurin-17 AS build

WORKDIR /app
COPY pom.xml /app/pom.xml
COPY src /app/src
RUN mvn -q -DskipTests package

FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=build /app/target/californium-backend-0.1.0.jar /app/californium-backend.jar
EXPOSE 5683/udp
CMD ["java", "-jar", "/app/californium-backend.jar"]
