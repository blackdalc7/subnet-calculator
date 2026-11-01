"""Unit tests for the subnet maths, cross-checked against the stdlib."""

from __future__ import annotations

import ipaddress

import pytest

from subnetcalc.core import (
    Subnet,
    int_to_ip,
    ip_to_int,
    mask_to_prefix,
    prefix_to_mask,
)


@pytest.mark.parametrize(
    "ip",
    ["0.0.0.0", "192.168.1.1", "10.0.0.255", "255.255.255.255", "8.8.8.8"],
)
def test_ip_roundtrip(ip):
    assert int_to_ip(ip_to_int(ip)) == ip


@pytest.mark.parametrize("bad", ["1.2.3", "1.2.3.4.5", "256.0.0.1", "a.b.c.d", "10.0.0.-1"])
def test_ip_to_int_rejects_bad(bad):
    with pytest.raises(ValueError):
        ip_to_int(bad)


@pytest.mark.parametrize("prefix", list(range(0, 33)))
def test_mask_matches_stdlib(prefix):
    mask = prefix_to_mask(prefix)
    expected = int(ipaddress.IPv4Network(f"0.0.0.0/{prefix}").netmask)
    assert mask == expected
    assert mask_to_prefix(mask) == prefix


def test_mask_to_prefix_rejects_non_contiguous():
    with pytest.raises(ValueError):
        mask_to_prefix(ip_to_int("255.0.255.0"))


@pytest.mark.parametrize(
    "cidr",
    ["192.168.1.0/24", "10.0.0.0/8", "172.16.5.0/22", "203.0.113.64/26", "0.0.0.0/0"],
)
def test_subnet_matches_stdlib(cidr):
    net = Subnet.parse(cidr)
    ref = ipaddress.ip_network(cidr, strict=False)
    assert int_to_ip(net.network) == str(ref.network_address)
    assert int_to_ip(net.broadcast) == str(ref.broadcast_address)
    assert int_to_ip(net.netmask) == str(ref.netmask)
    assert net.num_addresses == ref.num_addresses
    assert net.num_usable == max(ref.num_addresses - 2, 0)


def test_parse_normalises_host_bits():
    # 192.168.1.200/24 should collapse to the .0 network base.
    net = Subnet.parse("192.168.1.200/24")
    assert str(net) == "192.168.1.0/24"


def test_parse_accepts_dotted_mask_and_bare_address():
    assert str(Subnet.parse("10.0.0.5 255.0.0.0")) == "10.0.0.0/8"
    assert str(Subnet.parse("10.0.0.5/255.0.0.0")) == "10.0.0.0/8"
    assert str(Subnet.parse("8.8.8.8")) == "8.8.8.8/32"


def test_point_to_point_and_host_routes():
    p2p = Subnet.parse("10.0.0.0/31")
    assert p2p.num_usable == 2
    assert int_to_ip(p2p.first_host) == "10.0.0.0"
    assert int_to_ip(p2p.last_host) == "10.0.0.1"

    host = Subnet.parse("10.0.0.7/32")
    assert host.num_usable == 1
    assert host.first_host == host.last_host == ip_to_int("10.0.0.7")


def test_contains():
    net = Subnet.parse("192.168.1.0/24")
    assert net.contains("192.168.1.1")
    assert net.contains("192.168.1.255")
    assert not net.contains("192.168.2.1")
    assert net.contains(ip_to_int("192.168.1.100"))


def test_split_into_prefix():
    parts = Subnet.parse("10.0.0.0/24").subnets(26)
    assert [str(p) for p in parts] == [
        "10.0.0.0/26",
        "10.0.0.64/26",
        "10.0.0.128/26",
        "10.0.0.192/26",
    ]


def test_split_rejects_larger_prefix():
    with pytest.raises(ValueError):
        Subnet.parse("10.0.0.0/24").subnets(23)


def test_as_dict_keys():
    d = Subnet.parse("192.168.0.0/30").as_dict()
    assert d["num_usable"] == 2
    assert d["first_host"] == "192.168.0.1"
    assert d["last_host"] == "192.168.0.2"
