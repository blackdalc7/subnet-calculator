"""Command-line interface for the subnet calculator."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from subnetcalc.core import Subnet


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="subnetcalc",
        description="IPv4 subnet / CIDR calculator.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_info = sub.add_parser("info", help="show the facts about a network")
    p_info.add_argument("cidr", help='e.g. "192.168.1.0/24" or "10.0.0.5 255.0.0.0"')
    p_info.add_argument("--json", action="store_true", help="emit JSON")

    p_split = sub.add_parser("split", help="divide a network into subnets")
    p_split.add_argument("cidr", help="the parent network, e.g. 10.0.0.0/24")
    group = p_split.add_mutually_exclusive_group(required=True)
    group.add_argument("--into", type=int, metavar="PREFIX", help="target prefix, e.g. 26")
    group.add_argument("--count", type=int, metavar="N", help="at least N equal subnets")
    p_split.add_argument("--json", action="store_true", help="emit JSON")

    p_contains = sub.add_parser("contains", help="test whether an address is in a network")
    p_contains.add_argument("cidr", help="the network, e.g. 192.168.1.0/24")
    p_contains.add_argument("ip", help="the address to test")

    return parser


def _smallest_prefix_for_count(parent_prefix: int, count: int) -> int:
    """Smallest prefix that yields at least ``count`` subnets of a parent."""
    if count < 1:
        raise ValueError("count must be at least 1")
    bits = 0
    while (1 << bits) < count:
        bits += 1
    prefix = parent_prefix + bits
    if prefix > 32:
        raise ValueError(f"cannot fit {count} subnets inside /{parent_prefix}")
    return prefix


def _print_info(net: Subnet, as_json: bool, out) -> None:
    if as_json:
        json.dump(net.as_dict(), out, indent=2)
        out.write("\n")
        return
    d = net.as_dict()
    rows = [
        ("CIDR", d["cidr"]),
        ("Network", d["network"]),
        ("Netmask", d["netmask"]),
        ("Wildcard", d["wildcard"]),
        ("Broadcast", d["broadcast"]),
        ("Host range", f"{d['first_host']} - {d['last_host']}"),
        ("Total addresses", d["num_addresses"]),
        ("Usable hosts", d["num_usable"]),
    ]
    width = max(len(label) for label, _ in rows)
    for label, value in rows:
        out.write(f"{label:<{width}} : {value}\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out = sys.stdout

    try:
        if args.command == "info":
            _print_info(Subnet.parse(args.cidr), args.json, out)
            return 0

        if args.command == "split":
            parent = Subnet.parse(args.cidr)
            new_prefix = args.into if args.into is not None else _smallest_prefix_for_count(
                parent.prefix, args.count
            )
            parts = parent.subnets(new_prefix)
            if args.json:
                json.dump([p.as_dict() for p in parts], out, indent=2)
                out.write("\n")
            else:
                out.write(f"{parent} split into {len(parts)} x /{new_prefix}:\n")
                for p in parts:
                    out.write(f"  {p}\n")
            return 0

        if args.command == "contains":
            net = Subnet.parse(args.cidr)
            inside = net.contains(args.ip)
            out.write(f"{args.ip} is {'in' if inside else 'NOT in'} {net}\n")
            return 0 if inside else 1
    except ValueError as exc:
        print(f"subnetcalc: {exc}", file=sys.stderr)
        return 2

    parser.error("unknown command")  # pragma: no cover - argparse guards this
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
