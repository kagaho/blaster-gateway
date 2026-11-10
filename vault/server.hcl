# Local administration profile only: published on host loopback.
# Remote Vault access must use an HTTPS endpoint; this file contains no certificate data.
ui = false
disable_mlock = true
disable_clustering = true
listener "tcp" {
  address = "0.0.0.0:8200"
  tls_disable = true
}
storage "file" {
  path = "/vault/data"
}
