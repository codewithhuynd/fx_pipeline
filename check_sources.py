import requests
for name, url in [
    ("VCB", "https://portal.vietcombank.com.vn/UserControls/TVPortal.TyGia/pXML.aspx"),
    ("ECB", "https://api.frankfurter.dev/v1/latest?base=USD&symbols=EUR,JPY"),
]:
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        print(name, r.status_code, len(r.text))
        print(r.text[:600])
        print("-" * 40)
    except Exception as e:
        print(name, "LỖI:", e)