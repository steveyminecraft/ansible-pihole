# Secrets Management

## Required secrets

- `pihole_environment_variables.FTLCONF_webserver_api_password`
- `nebula_sync_primary_password`
- `nebula_sync_replicas[*].password`

## Validation behavior

- Pi-hole deploy asserts a non-placeholder password with minimum length.
- Nebula Sync deploy asserts non-placeholder primary and replica credentials.
- Known placeholders (`CHANGE_ME`, `Intranet`, `Testing 101`, empty) are rejected.

## Storage recommendations

- Store production credentials in Ansible Vault or equivalent secret backend.
- Keep plaintext credentials out of versioned inventory files.

## File permissions

- Pi-hole compose file is rendered root-owned with mode `0600`.
- Nebula Sync secret files are mode `0400` when secret-file mode is enabled.

## Nebula Sync mode

- Default is `nebula_sync_use_secret_files: true`.
- Credentials are mounted as files and referenced using `PRIMARY_FILE` and
  `REPLICAS_FILE`.
