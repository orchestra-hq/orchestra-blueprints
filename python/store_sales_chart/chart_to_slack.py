import os, re, io, json, zipfile, hmac, hashlib, datetime, collections
import urllib.parse, urllib.request, urllib.error
from xml.etree import ElementTree as ET

AK = os.environ["S3_ACCESS_KEY_ID"]
SK = os.environ["S3_SECRET_ACCESS_KEY"]
REGION = os.environ.get("S3_REGION", "eu-west-2")
BUCKET = os.environ.get("S3_BUCKET", "orchestra-demo-account")
SRC_KEY = os.environ.get("S3_SOURCE_KEY", "vape_data_test/Vape Data.xlsx")
PREFIX = os.environ.get("S3_CHART_PREFIX", "charts")
CHANNEL = os.environ.get("SLACK_CHANNEL", "C05JRE8LTMJ")
TOKEN = os.environ["SLACK_BOT_TOKEN"]
HOST = f"{BUCKET}.s3.{REGION}.amazonaws.com"
BLUE, ORANGE = "#2a78d6", "#eb6834"
SURFACE, GRID, BASELINE = "#fcfcfb", "#e1e0d9", "#c3c2b7"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"

def _sign(key, msg):
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()

def _skey(datestamp):
    k = _sign(("AWS4" + SK).encode(), datestamp)
    return _sign(_sign(_sign(k, REGION), "s3"), "aws4_request")

def s3_request(method, path, query=None, body=b"", content_type=None):
    t = datetime.datetime.now(datetime.timezone.utc)
    amzdate = t.strftime("%Y%m%dT%H%M%SZ"); datestamp = t.strftime("%Y%m%d")
    ph = hashlib.sha256(body).hexdigest()
    uri = urllib.parse.quote(path, safe="/~")
    qs = "&".join(f"{urllib.parse.quote(k, safe='~')}={urllib.parse.quote(str(v), safe='~')}"
                  for k, v in sorted((query or {}).items()))
    headers = f"host:{HOST}\nx-amz-content-sha256:{ph}\nx-amz-date:{amzdate}\n"
    signed = "host;x-amz-content-sha256;x-amz-date"
    creq = f"{method}\n{uri}\n{qs}\n{headers}\n{signed}\n{ph}"
    scope = f"{datestamp}/{REGION}/s3/aws4_request"
    sts = f"AWS4-HMAC-SHA256\n{amzdate}\n{scope}\n" + hashlib.sha256(creq.encode()).hexdigest()
    sig = hmac.new(_skey(datestamp), sts.encode(), hashlib.sha256).hexdigest()
    url = f"https://{HOST}{uri}" + (f"?{qs}" if qs else "")
    req = urllib.request.Request(url, method=method, data=body or None)
    req.add_header("Authorization", f"AWS4-HMAC-SHA256 Credential={AK}/{scope}, "
                                    f"SignedHeaders={signed}, Signature={sig}")
    req.add_header("x-amz-date", amzdate)
    req.add_header("x-amz-content-sha256", ph)
    if content_type:
        req.add_header("Content-Type", content_type)
    try:
        r = urllib.request.urlopen(req)
        return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()

def s3_presign(path, expires=604800):
    t = datetime.datetime.now(datetime.timezone.utc)
    amzdate = t.strftime("%Y%m%dT%H%M%SZ"); datestamp = t.strftime("%Y%m%d")
    scope = f"{datestamp}/{REGION}/s3/aws4_request"
    q = {"X-Amz-Algorithm": "AWS4-HMAC-SHA256", "X-Amz-Credential": f"{AK}/{scope}",
         "X-Amz-Date": amzdate, "X-Amz-Expires": str(expires), "X-Amz-SignedHeaders": "host"}
    uri = urllib.parse.quote(path, safe="/~")
    qs = "&".join(f"{urllib.parse.quote(k, safe='~')}={urllib.parse.quote(v, safe='~')}"
                  for k, v in sorted(q.items()))
    creq = f"GET\n{uri}\n{qs}\nhost:{HOST}\n\nhost\nUNSIGNED-PAYLOAD"
    sts = f"AWS4-HMAC-SHA256\n{amzdate}\n{scope}\n" + hashlib.sha256(creq.encode()).hexdigest()
    sig = hmac.new(_skey(datestamp), sts.encode(), hashlib.sha256).hexdigest()
    return f"https://{HOST}{uri}?{qs}&X-Amz-Signature={sig}"

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

def xlsx_rows(blob):
    z = zipfile.ZipFile(io.BytesIO(blob))
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(f"{NS}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{NS}t")))
    names = sorted(n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
    rows = []
    for row in ET.fromstring(z.read(names[0])).iter(f"{NS}row"):
        cells = {}
        for c in row.findall(f"{NS}c"):
            t = c.get("t"); v = c.find(f"{NS}v")
            if v is None and t != "inlineStr":
                continue
            n = 0
            for ch in re.match(r"([A-Z]+)", c.get("r")).group(1):
                n = n * 26 + (ord(ch) - 64)
            if t == "s":
                val = shared[int(v.text)]
            elif t == "inlineStr":
                val = "".join(x.text or "" for x in c.iter(f"{NS}t"))
            else:
                try:
                    val = float(v.text)
                except (TypeError, ValueError):
                    val = v.text
            cells[n - 1] = val
        if cells:
            rows.append([cells.get(i) for i in range(max(cells) + 1)])
    return rows

def load():
    st, blob = s3_request("GET", "/" + SRC_KEY)
    if st != 200:
        raise RuntimeError(f"S3 GET {SRC_KEY} returned {st}")
    rows = xlsx_rows(blob)
    dates = hdr_i = None
    for i, r in enumerate(rows):
        if "Date" in r:
            j = r.index("Date")
            dates = [datetime.date(1899, 12, 30) + datetime.timedelta(days=int(v))
                     for v in r[j + 1:] if isinstance(v, float)]
            hdr_i = i
            break
    if not dates:
        raise RuntimeError("No 'Date' header row found in workbook")
    totals = collections.defaultdict(lambda: [0] * len(dates))
    city = None; n = 0
    for r in rows[hdr_i + 1:]:
        if not r or len(r) < 5:
            continue
        # city label appears only on the first row of each block -> forward-fill
        if isinstance(r[0], str) and r[0].strip() and r[0] != "Store":
            city = r[0].strip()
        vals = r[4:4 + len(dates)]
        if city is None or not any(isinstance(v, float) for v in vals):
            continue
        n += 1
        for k, v in enumerate(vals):
            if isinstance(v, float):
                totals[city][k] += int(v)
    if not totals:
        raise RuntimeError("No city rows parsed from workbook")
    print(f"Parsed {n} store/SKU rows, {len(dates)} days, {len(totals)} cities")
    return dates, dict(totals)

def render(dates, series, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=160)
    fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
    x = list(range(len(dates)))
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE); ax.spines["bottom"].set_linewidth(1)
    for (name, vals), c in zip(sorted(series.items()), [BLUE, ORANGE]):
        ax.plot(x, vals, color=c, linewidth=2, marker="o", markersize=4.5,
                markerfacecolor=c, markeredgecolor=SURFACE, markeredgewidth=1.5,
                label=f"{name} ({sum(vals):,} total)", zorder=3, solid_capstyle="round")
        for idx in (vals.index(max(vals)), vals.index(min(vals))):
            ax.annotate(f"{vals[idx]:,}", (x[idx], vals[idx]), textcoords="offset points",
                        xytext=(0, 11), ha="center", fontsize=9, color=INK,
                        fontweight="bold", zorder=4)
    ax.set_xticks(x)
    ax.set_xticklabels([d.strftime("%-d %b") for d in dates], fontsize=9, color=MUTED)
    ax.tick_params(axis="y", labelsize=9, colors=MUTED, length=0)
    ax.tick_params(axis="x", length=0)
    ax.set_ylim(0, max(max(v) for v in series.values()) * 1.18)
    ax.set_ylabel("Units sold", fontsize=10, color=INK2, labelpad=10)
    ax.set_title("Daily units sold by city", fontsize=14, color=INK,
                 fontweight="bold", loc="left", pad=16)
    leg = ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, -0.13),
                    ncol=2, fontsize=10, handlelength=1.6)
    for t in leg.get_texts():
        t.set_color(INK2)
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)

def publish(png_path, dates, series):
    key = f"/{PREFIX}/store_sales_{dates[0]:%Y%m%d}_{dates[-1]:%Y%m%d}.png"
    st, body = s3_request("PUT", key, body=open(png_path, "rb").read(),
                          content_type="image/png")
    if st not in (200, 201):
        raise RuntimeError(f"S3 PUT failed {st}: {body[:200]!r}")
    url = s3_presign(key)
    ranked = sorted(series.items(), key=lambda kv: -sum(kv[1]))
    lead, second = ranked[0], ranked[1]
    drop, dcity, di = max((series[c][i] - series[c][i + 1], c, i)
                          for c in series for i in range(len(dates) - 1))
    pct = round(drop / series[dcity][di] * 100) if series[dcity][di] else 0
    period = f"{dates[0]:%-d} - {dates[-1]:%-d %b %Y}"
    summary = (f"*{lead[0]}* leads the period on volume - *{sum(lead[1]):,}* units "
               f"vs {second[0]}'s *{sum(second[1]):,}*.\n")
    if pct >= 40:
        summary += (f"Worth a look: *{dcity}* falls from *{series[dcity][di]:,}* on "
                    f"{dates[di]:%-d %b} to *{series[dcity][di + 1]:,}* the next day - a "
                    f"*{pct}% overnight drop*. That shape usually means a stock-out or a "
                    f"closed store rather than demand.")
    else:
        summary += f"Largest single-day drop was {pct}% ({dcity}) - nothing unusual."
    blocks = [
        {"type": "header", "text": {"type": "plain_text",
                                    "text": f"Store sales - {period}", "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn", "text": summary}},
        {"type": "image", "image_url": url,
         "alt_text": (f"Line chart of daily units sold by city, {period}. "
                      + "; ".join(f"{c} totals {sum(v):,} units" for c, v in ranked) + ".")},
        {"type": "context", "elements": [{"type": "mrkdwn",
         "text": f"Source: `s3://{BUCKET}/{SRC_KEY}` - generated by Orchestra"}]},
    ]
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps({"channel": CHANNEL, "blocks": blocks,
                         "text": f"Store sales - {period}"}).encode(),
        headers={"Authorization": f"Bearer {TOKEN}",
                 "Content-Type": "application/json; charset=utf-8"})
    r = json.load(urllib.request.urlopen(req))
    if not r.get("ok"):
        raise RuntimeError(f"Slack post failed: {r.get('error')}")
    return key, r["ts"]

dates, series = load()
render(dates, series, "chart.png")
key, ts = publish("chart.png", dates, series)
print(f"Published s3://{BUCKET}{key} -> Slack {CHANNEL} ts={ts}")
