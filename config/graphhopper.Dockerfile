FROM eclipse-temurin:21-jre AS base

RUN apt-get update && apt-get install -y --no-install-recommends curl wget && rm -rf /var/lib/apt/lists/*

FROM israelhikingmap/graphhopper:latest AS graphhopper

FROM base

ENV JAVA_OPTS="-Xmx1g -Xms1g"

WORKDIR /graphhopper

COPY --from=graphhopper /graphhopper /graphhopper
COPY --from=graphhopper /data /data

VOLUME ["/data"]

EXPOSE 8989 8990

HEALTHCHECK --interval=5s --timeout=3s CMD curl --fail http://localhost:8989/health || exit 1

ENTRYPOINT ["./graphhopper.sh", "-c", "config-example.yml"]
