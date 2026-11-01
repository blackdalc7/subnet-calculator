"""Tests for the command-line interface."""

from __future__ import annotations

import json

import pytest

from subnetcalc.cli import _smallest_prefix_for_count, main


def test_info_text(capsys):
    rc = main(["info", "192.168.1.0/24"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Broadcast" in out
    assert "192.168.1.255" in out
    assert "Usable hosts" in out
    assert "254" in out


def test_info_json(capsys):
    rc = main(["info", "10.0.0.0/30", "--json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert rc == 0
    assert data["cidr"] == "10.0.0.0/30"
    assert data["num_usable"] == 2


def test_split_into(capsys):
    rc = main(["split", "10.0.0.0/24", "--into", "26"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "10.0.0.192/26" in out
    assert out.count("/26\n") == 4  # four subnet lines (the header ends "/26:")


def test_split_count_rounds_up(capsys):
    # Asking for 3 subnets needs 2 borrowed bits -> 4 subnets of /26.
    rc = main(["split", "10.0.0.0/24", "--count", "3"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "/26" in out


def test_contains_exit_codes(capsys):
    assert main(["contains", "192.168.1.0/24", "192.168.1.5"]) == 0
    assert main(["contains", "192.168.1.0/24", "10.0.0.1"]) == 1


def test_bad_input_returns_2(capsys):
    rc = main(["info", "999.0.0.0/24"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "subnetcalc:" in err


@pytest.mark.parametrize(
    "parent,count,expected",
    [(24, 1, 24), (24, 2, 25), (24, 3, 26), (24, 4, 26), (24, 5, 27)],
)
def test_smallest_prefix_for_count(parent, count, expected):
    assert _smallest_prefix_for_count(parent, count) == expected


def test_smallest_prefix_overflow():
    with pytest.raises(ValueError):
        _smallest_prefix_for_count(30, 100)
