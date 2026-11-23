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
            if r.status_code == 200 and "V75 restart-safe sales sheets" in r.text:
                print("V75 website is live")
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
    # Render deploys can briefly return 502 while swapping instances.
    # Retry those gateway failures without looping endlessly or hiding
    # persistent application failures.
    for attempt in range(5):
        try:
            response=requests.get(BASE+"/api/competitors/4832",timeout=85,
                                  headers={"Accept":"application/json"})
            print("Competitor endpoint HTTP",response.status_code,
                  "attempt",attempt+1,flush=True)
            if response.status_code==200:
                break
            if response.status_code not in (429,502,503,504):
                raise AssertionError("Unexpected HTTP status: "+
                                     str(response.status_code)+" "+response.text[:450])
        except requests.RequestException as exc:
            print("Temporary Render gateway/network error",type(exc).__name__,flush=True)
        if attempt<4:
            time.sleep(12)
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
    # Render Free stops/restarts and clears in-memory cache. The verified
    # evidence and exact PDF must ALREADY be in this response, so the button
    # can work hours later without an additional server call.
    import base64
    pack=report.get("why_laser_pack") or {}
    assert pack.get("sheet",{}).get("part")=="4832",repr(pack)
    assert len(pack["sheet"].get("competitors",[]))>=4
    assert pack.get("review_required") is True
    assert pack["sheet"]["public_claim_approved"] is False
    pdf=base64.b64decode(pack.get("pdf_base64") or "",validate=True)
    assert pdf.startswith(b"%PDF-"),"No genuine PDF shipped with initial response"
    assert len(pdf)>700,"Empty PDF in report"
    print("Inline restart-safe PDF ready",len(pdf),"bytes")
    sheet=requests.get(BASE+"/api/competitors/4832/why-laser",timeout=25)
    assert sheet.status_code==200,(sheet.status_code,sheet.text[:350])
    body=sheet.json()
    assert body["part"]=="4832"
    assert len(body.get("competitors",[]))>=4,repr(body)
    assert body["public_claim_approved"] is False
    print("PASS: 4832 live research contains source-checked comparison AND self-contained downloadable PDF")


if __name__=="__main__":
    main()
