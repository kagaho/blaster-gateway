#!/bin/sh
set -eu
# The image runs as UID 636, while private host output belongs to its operator.
# Bootstrap only writable APISIX state, then drop to the runtime directory owner.
# Never relax the private directory or key file to world/group-readable permissions.
runtime=/usr/local/apisix/conf/rendered
runtime_uid=$(stat -c %u "$runtime")
runtime_gid=$(stat -c %g "$runtime")
if [ "$runtime_uid" -eq 0 ] || [ "$runtime_gid" -eq 0 ]; then
    echo 'Render as a non-root operator; refusing a root-owned runtime directory.' >&2
    exit 1
fi
chown "$runtime_uid:$runtime_gid" /usr/local/apisix /usr/local/apisix/conf
# Replace vendor stdout/stderr symlinks: reopening root-owned descriptor paths after
# dropping UID is denied on some hosts. Private regular logs retain diagnostics.
for log in error.log access.log; do
    path="/usr/local/apisix/logs/$log"
    if [ -L "$path" ]; then rm "$path"; fi
    touch "$path"
    chmod 600 "$path"
done
chown -R "$runtime_uid:$runtime_gid" /usr/local/apisix/logs
chmod 700 /usr/local/apisix/logs
ln -sf "$runtime/apisix.yaml" /usr/local/apisix/conf/apisix.yaml
export APISIX_STAND_ALONE=true
exec setpriv --reuid "$runtime_uid" --regid "$runtime_gid" --clear-groups \
    /docker-entrypoint.sh docker-start
