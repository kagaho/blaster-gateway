# Read-only KV v2 access. No writes, root policy, or unseal capability.
path "apisix/data/consumers/*" {
  capabilities = ["read"]
}
path "auth/token/lookup-self" {
  capabilities = ["read"]
}
