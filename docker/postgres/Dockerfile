FROM postgres:16-alpine3.21 AS base

# Upgrade all packages to patch Alpine vulnerabilities
RUN apk update && apk upgrade --no-cache

# Remove gosu (which contains the Go vulnerabilities) and replace with su-exec
RUN rm -f /usr/local/bin/gosu \
    && apk add --no-cache su-exec

# Patch the entrypoint to use su-exec instead of gosu
RUN sed -i 's/exec gosu postgres/exec su-exec postgres/g' /usr/local/bin/docker-entrypoint.sh

# Squash the image to physically remove gosu from the layers
FROM scratch
COPY --from=base / /

# Re-apply necessary Postgres metadata that was lost in the scratch copy
ENV LANG=en_US.utf8
ENV PGDATA=/var/lib/postgresql/data
VOLUME /var/lib/postgresql/data
ENTRYPOINT ["docker-entrypoint.sh"]
EXPOSE 5432
CMD ["postgres"]
