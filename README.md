# subnet-calculator

[![CI](https://github.com/blackdalc7/subnet-calculator/actions/workflows/ci.yml/badge.svg)](https://github.com/blackdalc7/subnet-calculator/actions/workflows/ci.yml)

An IPv4 subnet / CIDR calculator you can use from the command line. The maths is
written out with plain integer **bit operations** rather than leaning on
Python's `ipaddress` module — the whole point of the project was to understand
how netmasks, broadcast addresses and host ranges actually fall out of the bits.
(The test-suite then cross-checks every result against `ipaddress`, so the hand
-rolled version has to agree with the standard library.)

No third-party dependencies: standard library only.

## What it can tell you

Given `192.168.1.0/26`:

```text
CIDR            : 192.168.1.0/26
Network         : 192.168.1.0
Netmask         : 255.255.255.192
Wildcard        : 0.0.0.63
Broadcast       : 192.168.1.63
Host range      : 192.168.1.1 - 192.168.1.62
Total addresses : 64
Usable hosts    : 62
```

It also handles the awkward edges correctly: a **/31** reports two usable hosts
(RFC 3021 point-to-point links) and a **/32** reports a single host route.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt    # only needed for the tests

# facts about a network (accepts /prefix, a dotted mask, or a bare address)
PYTHONPATH=src python -m subnetcalc info 192.168.1.0/24
PYTHONPATH=src python -m subnetcalc info "10.0.0.5 255.0.0.0"

# split a block into smaller subnets
PYTHONPATH=src python -m subnetcalc split 10.0.0.0/24 --into 26
PYTHONPATH=src python -m subnetcalc split 10.0.0.0/24 --count 3   # rounds up to 4

# membership test (exit code 0 = inside, 1 = outside; handy in scripts)
PYTHONPATH=src python -m subnetcalc contains 192.168.1.0/24 192.168.1.42
```

Add `--json` to `info` or `split` for machine-readable output.

## Commands

| Command | Purpose |
|---|---|
| `info CIDR` | Network, netmask, wildcard, broadcast, host range, counts |
| `split CIDR --into PREFIX` | Divide into equal subnets of that prefix |
| `split CIDR --count N` | Divide into the fewest equal subnets that gives ≥ N |
| `contains CIDR IP` | Report (and exit-code) whether an address is in the network |

## Layout

```text
src/subnetcalc/
    core.py        ip_to_int / int_to_ip, prefix<->mask, the Subnet dataclass
    cli.py         argparse front-end: info / split / contains
    __main__.py    enables `python -m subnetcalc`
tests/
    test_core.py   maths, cross-checked against the stdlib ipaddress module
    test_cli.py    the three subcommands and their exit codes
```

## How the maths works

An address is just a 32-bit number. A `/24` netmask is 24 one-bits followed by
8 zero-bits (`0xFFFFFF00`). From there:

- **network** = `address & netmask`
- **wildcard** = `~netmask` (the host bits)
- **broadcast** = `network | wildcard`
- **total addresses** = `2 ** (32 - prefix)`

`mask_to_prefix` also validates that a dotted mask is *contiguous* (a run of 1s
then 0s), rejecting nonsense like `255.0.255.0`.

## Tests

```bash
PYTHONPATH=src pytest --cov      # 68 tests, coverage gate 90%
```

## Licence

MIT. See [LICENSE](LICENSE).
