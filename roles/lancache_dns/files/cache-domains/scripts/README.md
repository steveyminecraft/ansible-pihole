Vendored `create-dnsmasq.sh` from https://github.com/uklans/cache-domains
at commit `9061355d60e7643cc70aa3cc395f2777c2d86b5d`.

Ansible uses `scripts/lancache_dns.py` (reviewed port, jq-free) so CI does not
execute a freshly downloaded script. Keep this copy for audit against upstream.
Steam-only `cache_domains.json` is a subset of that commit; do not add other
publishers without a PR.
