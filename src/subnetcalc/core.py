"""Core IPv4 subnet maths.

Everything here works on a 32-bit integer view of an address and uses only bit
operations, so the arithmetic that a subnet calculator is really about stays
visible rather than hidden behind the standard library's ``ipaddress`` module.
(The test-suite cross-checks the results against ``ipaddress`` all the same.)
"""

from __future__ import annotations

from dataclasses import dataclass

MAX_UINT32 = 0xFFFFFFFF


def ip_to_int(ip: str) -> int:
    """Convert dotted-quad ``"192.168.1.1"`` to its 32-bit integer value."""
    parts = ip.strip().split(".")
    if len(parts) != 4:
        raise ValueError(f"{ip!r} is not a dotted-quad IPv4 address")
    value = 0
    for part in parts:
        if not part.isdigit():
            raise ValueError(f"{ip!r} has a non-numeric octet {part!r}")
        octet = int(part)
        if octet > 255:
            raise ValueError(f"{ip!r} has octet {octet} > 255")
        value = (value << 8) | octet
    return value


def int_to_ip(value: int) -> str:
    """Convert a 32-bit integer back to dotted-quad notation."""
    if not 0 <= value <= MAX_UINT32:
        raise ValueError(f"{value} is outside the 32-bit range")
    return ".".join(str((value >> shift) & 0xFF) for shift in (24, 16, 8, 0))


def prefix_to_mask(prefix: int) -> int:
    """Return the netmask for a prefix length as a 32-bit integer."""
    if not 0 <= prefix <= 32:
        raise ValueError(f"prefix /{prefix} is out of range 0-32")
    if prefix == 0:
        return 0
    return (MAX_UINT32 << (32 - prefix)) & MAX_UINT32


def mask_to_prefix(mask: int) -> int:
    """Return the prefix length for a contiguous netmask, or raise if it is not
    a valid (left-contiguous) mask such as ``255.255.255.0``."""
    if not 0 <= mask <= MAX_UINT32:
        raise ValueError("mask outside 32-bit range")
    # A valid mask is a run of 1s followed by a run of 0s. Inverting and adding
    # one must give a power of two (or zero for the all-ones mask).
    inverted = (~mask) & MAX_UINT32
    if inverted & (inverted + 1):
        raise ValueError(f"{int_to_ip(mask)} is not a contiguous netmask")
    return bin(mask).count("1")


@dataclass(frozen=True)
class Subnet:
    """An IPv4 network: a base address plus a prefix length."""

    network: int
    prefix: int

    @classmethod
    def parse(cls, spec: str) -> Subnet:
        """Parse ``"10.0.0.0/8"`` or ``"10.0.0.5 255.0.0.0"`` or a bare address
        (treated as /32). The address is normalised down to the network base."""
        spec = spec.strip()
        if "/" in spec:
            addr, _, suffix = spec.partition("/")
            prefix = _parse_prefix_or_mask(suffix)
        elif " " in spec:
            addr, _, mask = spec.partition(" ")
            prefix = mask_to_prefix(ip_to_int(mask.strip()))
        else:
            addr, prefix = spec, 32
        base = ip_to_int(addr) & prefix_to_mask(prefix)
        return cls(network=base, prefix=prefix)

    # --- derived values ---------------------------------------------------

    @property
    def netmask(self) -> int:
        return prefix_to_mask(self.prefix)

    @property
    def wildcard(self) -> int:
        return (~self.netmask) & MAX_UINT32

    @property
    def broadcast(self) -> int:
        return self.network | self.wildcard

    @property
    def num_addresses(self) -> int:
        return 1 << (32 - self.prefix)

    @property
    def first_host(self) -> int:
        if self.prefix >= 31:  # /31 and /32 have no reserved network address
            return self.network
        return self.network + 1

    @property
    def last_host(self) -> int:
        if self.prefix == 32:
            return self.network
        if self.prefix == 31:
            return self.broadcast
        return self.broadcast - 1

    @property
    def num_usable(self) -> int:
        """Usable host addresses.

        For /31 both addresses are usable (RFC 3021, point-to-point links); a
        /32 is a single host; otherwise the network and broadcast addresses are
        subtracted.
        """
        if self.prefix == 32:
            return 1
        if self.prefix == 31:
            return 2
        return self.num_addresses - 2

    def contains(self, ip: str | int) -> bool:
        """True if ``ip`` falls inside this network."""
        value = ip if isinstance(ip, int) else ip_to_int(ip)
        return self.network <= value <= self.broadcast

    def subnets(self, new_prefix: int) -> list[Subnet]:
        """Split this network into equal subnets of ``new_prefix`` length."""
        if new_prefix < self.prefix:
            raise ValueError(f"/{new_prefix} is larger than the parent /{self.prefix}")
        if new_prefix > 32:
            raise ValueError("prefix cannot exceed /32")
        step = 1 << (32 - new_prefix)
        return [
            Subnet(network=self.network + offset, prefix=new_prefix)
            for offset in range(0, self.num_addresses, step)
        ]

    def as_dict(self) -> dict[str, object]:
        """A plain dictionary of the key facts, ready for JSON output."""
        return {
            "cidr": f"{int_to_ip(self.network)}/{self.prefix}",
            "network": int_to_ip(self.network),
            "netmask": int_to_ip(self.netmask),
            "wildcard": int_to_ip(self.wildcard),
            "broadcast": int_to_ip(self.broadcast),
            "first_host": int_to_ip(self.first_host),
            "last_host": int_to_ip(self.last_host),
            "num_addresses": self.num_addresses,
            "num_usable": self.num_usable,
        }

    def __str__(self) -> str:
        return f"{int_to_ip(self.network)}/{self.prefix}"


def _parse_prefix_or_mask(suffix: str) -> int:
    suffix = suffix.strip()
    if "." in suffix:  # a dotted-quad mask such as 255.255.255.0
        return mask_to_prefix(ip_to_int(suffix))
    if not suffix.isdigit():
        raise ValueError(f"prefix {suffix!r} is not a number")
    return int(suffix)
