#!/usr/bin/env python3
"""Generate and validate isolated Pi-hole LanCache dnsmasq rules.

Reviewed port of uklans/cache-domains scripts/create-dnsmasq.sh at the
commit recorded in roles/lancache_dns/files/cache-domains/PIN. Steam-only
domain files are vendored; the generator refuses empty output, unknown
directives, foreign IPs, and reserved suffixes (package-cache, QoS, LAN).
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
from pathlib import Path

ADDRESS_RE = re.compile(r"^address=/([^/]+)/([^/]+)$")
LOCAL_RE = re.compile(r"^local=/([^/]+)/$")
COMMENT_RE = re.compile(r"^#")

DEFAULT_RESERVED_SUFFIXES = (
    "coalhill.zz",
    "ubuntu.com",
    "debian.org",
    "raspbian.org",
    "raspberrypi.org",
    "devuan.org",
    "twitch.tv",
    "ttvnw.net",
    "jtvnw.net",
    "twitchcdn.net",
    "live-video.net",
    "googlevideo.com",
    "youtube.com",
    "youtu.be",
    "ytimg.com",
    "civitai.com",
    "civitai.green",
    "pkg-cache",
)

MANAGED_HEADER = (
    "# Managed by ansible-pihole roles/lancache_dns. Do not edit by hand.\n"
    "# Isolated Steam CDN overrides; fail-open removes only this file.\n"
    "# IPv4 only. local=/ suppresses other address families for these names.\n"
)


def repo_cache_domains(root: Path) -> Path:
    return root / "roles" / "lancache_dns" / "files" / "cache-domains"


def read_pin(pin_path: Path) -> str:
    text = pin_path.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", text):
        raise ValueError("cache-domains PIN must be a 40-character commit SHA")
    return text


def load_enabled_domains(cache_domains_dir: Path, enabled: tuple[str, ...]) -> list[str]:
    manifest = json.loads((cache_domains_dir / "cache_domains.json").read_text(encoding="utf-8"))
    services = {item["name"]: item for item in manifest["cache_domains"]}
    unknown = [name for name in enabled if name not in services]
    if unknown:
        raise ValueError(f"unknown cache_domains services: {unknown}")
    extra = sorted(set(services) - set(enabled))
    if extra:
        raise ValueError(f"vendored cache_domains.json must be steam-only; extra: {extra}")
    domains: list[str] = []
    for name in enabled:
        for filename in services[name]["domain_files"]:
            path = cache_domains_dir / filename
            for raw in path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                domains.append(line.lstrip("*."))
    if not domains:
        raise ValueError("domain list is empty")
    return sorted(set(domains))


def generate_conf(cache_ip: str, domains: list[str], service_title: str = "Steam") -> str:
    ipaddress.IPv4Address(cache_ip)
    lines = [MANAGED_HEADER.rstrip(), f"# {service_title}"]
    for domain in domains:
        lines.append(f"address=/{domain}/{cache_ip}")
        lines.append(f"local=/{domain}/")
    return "\n".join(lines) + "\n"


def _suffix_match(domain: str, reserved: tuple[str, ...]) -> str | None:
    lowered = domain.lower().rstrip(".")
    for suffix in reserved:
        suffix = suffix.lower().rstrip(".")
        if lowered == suffix or lowered.endswith("." + suffix):
            return suffix
    return None


def validate_conf(
    text: str,
    cache_ip: str,
    allowed_domains: list[str],
    reserved_suffixes: tuple[str, ...] = DEFAULT_RESERVED_SUFFIXES,
) -> list[str]:
    errors: list[str] = []
    ipaddress.IPv4Address(cache_ip)
    allowed = set(allowed_domains)
    seen_address: set[str] = set()
    seen_local: set[str] = set()
    if not text.strip():
        return ["generated config is empty"]
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or COMMENT_RE.match(line):
            continue
        address = ADDRESS_RE.fullmatch(line)
        local = LOCAL_RE.fullmatch(line)
        if address:
            domain, ip = address.group(1), address.group(2)
            try:
                parsed_ip = ipaddress.ip_address(ip)
            except ValueError:
                errors.append(f"line {lineno}: address target is not a valid IP")
            else:
                if parsed_ip.version != 4:
                    errors.append(f"line {lineno}: address target is IPv6; LAN is IPv4-only")
                elif ip != cache_ip:
                    errors.append(f"line {lineno}: address target is not the cache IPv4")
            conflict = _suffix_match(domain, reserved_suffixes)
            if conflict:
                errors.append(f"line {lineno}: domain conflicts with reserved suffix")
            if domain not in allowed:
                errors.append(f"line {lineno}: domain is not in the enabled Steam set")
            seen_address.add(domain)
            continue
        if local:
            domain = local.group(1)
            if domain not in allowed:
                errors.append(f"line {lineno}: local= domain is not in the enabled Steam set")
            seen_local.add(domain)
            continue
        errors.append(f"line {lineno}: unsupported dnsmasq directive")
    missing_address = sorted(allowed - seen_address)
    missing_local = sorted(allowed - seen_local)
    if missing_address:
        errors.append("missing address= records for enabled domains")
    if missing_local:
        errors.append("missing local= records for enabled domains")
    if not seen_address:
        errors.append("no address= records generated")
    return errors


def generate_from_tree(root: Path, cache_ip: str, enabled: tuple[str, ...] = ("steam",)) -> str:
    cache_dir = repo_cache_domains(root)
    read_pin(cache_dir / "PIN")
    domains = load_enabled_domains(cache_dir, enabled)
    conf = generate_conf(cache_ip, domains)
    errors = validate_conf(conf, cache_ip, domains)
    if errors:
        raise ValueError("; ".join(errors))
    return conf


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "validate"))
    parser.add_argument("--cache-ip", required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--input", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            conf = generate_from_tree(args.root, args.cache_ip)
            if args.output is None:
                sys.stdout.write(conf)
            else:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(conf, encoding="utf-8")
            return 0
        text = sys.stdin.read() if args.input is None else args.input.read_text(encoding="utf-8")
        cache_dir = repo_cache_domains(args.root)
        domains = load_enabled_domains(cache_dir, ("steam",))
        errors = validate_conf(text, args.cache_ip, domains)
        if errors:
            for item in errors:
                print(item, file=sys.stderr)
            return 1
        return 0
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
