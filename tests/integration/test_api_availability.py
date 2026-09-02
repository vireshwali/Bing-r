import httpx
import pytest


@pytest.mark.external_http
def testIptvOrgCountriesReachable():
    url = "https://iptv-org.github.io/api/countries.json"
    resp = httpx.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 100
    codes = {c["code"] for c in data}
    assert "BA" in codes
