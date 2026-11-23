"""Post-deploy live smoke for Laser 4832 competitor and Why Laser endpoints.

Run only in a separately labelled GitHub Actions integration workflow. The
normal regression suite remains offline/deterministic. One live competitor
research request; retries are limited to avoid overloading Render Free.
"""
import os
import time

import requests

BASE = os.environ.get("STUDIO_URL", "https://laser-product-studio.onrender.com").rstrip("/")


def wait_for_v74():
    for attempt in range(18):
        try:
            r = requests.get(BASE, timeout=15)
            if r.status_code == 200 and "V74 competitor intelligence" in r.text:
                print("V74 website is live")
                return
            print("Waiting for V74 deploy", attempt + 1, "HTTP", r.status_code)
        except requests.RequestException as error:
            print("Waiting for Render startup", attempt + 1, type(error).__name__)
        time.sleep(8)
    raise AssertionError("V74 release not live within bounded smoke window")


def main():
    wait_for_v74()
    expected={"22495", "12724211", "VS820", "29358"}
    response=None
    for attempt in range(3):
        response=requests.get(BASE+"/api/competitors/4832",timeout=85,
                              headers={"Accept":"application/json"})
        print("Competitor endpoint HTTP",response.status_code,
              "attempt",attempt+1)
        if response.status_code==200:
            break
        if response.status_code not in (429,503):
            raise AssertionError("Unexpected HTTP status: "+
                                 str(response.status_code)+" "+response.text[:450])
        time.sleep(10)
    assert response is not None and response.status_code == 200, (
        "Render did not accept 4832 competitor research after bounded retries")
    report=response.json()
    rivals=report.get("results",[])
    skus={r.get("part_number") for r in rivals}
    print("Competitor count",report.get("count"),"SKUs",sorted(skus))
    print("Evidence",[(x.get("brand"),x.get("source_type")) for x in rivals])
    assert expected.issubset(skus), (
        "Official manufacturer comparison sources missing: "+repr(expected-skus))
    assert report["laser"]["part"]=="4832"
    assert all(row.get("url","").startswith("https://") for row in rivals)
    sheet=requests.get(BASE+"/api/competitors/4832/why-laser",timeout=25)
    assert sheet.status_code==200,(sheet.status_code,sheet.text[:350])
    body=sheet.json()
    assert body["part"]=="4832"
    assert len(body.get("competitors",[]))>=4,repr(body)
    assert body["public_claim_approved"] is False
    print("PASS: 4832 live research and the Why Choose Laser sheet contain real sourced alternatives")


if __name__=="__main__":
    main()
