from pyDSvDCAPIv2.dsuid import DsUid


def test_for_vdc_returns_34_hex_chars():
    uid = DsUid.for_vdc("my-bridge")
    assert len(uid) == 34
    assert all(c in "0123456789abcdefABCDEF" for c in uid)


def test_for_device_returns_34_hex_chars():
    uid = DsUid.for_device("lamp-001")
    assert len(uid) == 34
    assert all(c in "0123456789abcdefABCDEF" for c in uid)


def test_for_vdc_is_deterministic():
    assert DsUid.for_vdc("my-bridge") == DsUid.for_vdc("my-bridge")


def test_for_device_is_deterministic():
    assert DsUid.for_device("lamp-001") == DsUid.for_device("lamp-001")


def test_vdc_and_device_differ_for_same_seed():
    assert DsUid.for_vdc("same-seed") != DsUid.for_device("same-seed")


def test_different_seeds_produce_different_ids():
    assert DsUid.for_device("lamp-001") != DsUid.for_device("lamp-002")
