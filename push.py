#!/usr/bin/env python3
"""Fetch Serenity's latest tweets and push fund signals to WeChat via Server酱."""

import json
import os
import re
import urllib.request
from datetime import datetime, timezone, timedelta

SENDKEY = os.environ["SCT_SENDKEY"]
BEIJING_TZ = timezone(timedelta(hours=8))

# ── Fund mapping ──────────────────────────────────────────────
FUNDS = {
    "减速器":   ["020256", "020973"],
    "绿的谐波": ["020973", "020256"],
    "谐波":     ["020973", "020256"],
    "汇川":     ["020256"],
    "伺服":     ["020256"],
    "执行器":   ["020256"],
    "传感器":   ["007579"],
    "VPG":      ["007579"],
    "SIVE":     [],
    "Agility":  ["020256", "020973"],
    "Unitree":  ["020973", "020256"],
    "宇树":     ["020973", "020256"],
    "半导体":   ["008888", "024418"],
    "芯片":     ["008888", "024418"],
    "AI":       ["012734", "008888"],
    "人工智能": ["012734"],
    "光模块":   ["012734"],
    "Optimus":  ["020973", "020256"],
    "Figure":   ["020973", "020256"],
    "Tesla":    ["020973", "020256"],
    "特斯拉":   ["020973", "020256"],
    "HBM":      ["008888"],
    "存储":     ["008888"],
    "SK海力士": ["008888"],
    "设备":     ["024418"],
    "寒武纪":   ["012734", "008888"],
}

FUND_NAMES = {
    "020256": "中欧机器人C",
    "020973": "易方达机器人联接C",
    "007579": "宝盈先进制造C",
    "008888": "华夏芯片联接C",
    "024418": "科创半导体联接C",
    "012734": "易方达AI联接C",
}


def fetch_latest_tweets():
    """Fetch the latest tweet batch from the archive repo."""
    url = "https://api.github.com/repos/yan-labs/serenity-aleabitoreddit/commits?per_page=3"
    req = urllib.request.Request(url, headers={"User-Agent": "serenity-push/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        commits = json.loads(resp.read().decode())

    tweets = []
    for commit in commits:
        # Check if this commit touched data files
        commit_url = commit["url"]
        req2 = urllib.request.Request(commit_url, headers={"User-Agent": "serenity-push/1.0"})
        with urllib.request.urlopen(req2, timeout=30) as resp2:
            detail = json.loads(resp2.read().decode())
        for f in detail.get("files", []):
            filename = f.get("filename", "")
            if "data/" in filename and filename.endswith(".json"):
                # Fetch the raw file
                raw_url = f"https://raw.githubusercontent.com/yan-labs/serenity-aleabitoreddit/main/{filename}"
                try:
                    req3 = urllib.request.Request(raw_url, headers={"User-Agent": "serenity-push/1.0"})
                    with urllib.request.urlopen(req3, timeout=30) as resp3:
                        data = json.loads(resp3.read().decode())
                        if isinstance(data, list):
                            tweets.extend(data)
                        elif isinstance(data, dict):
                            tweets.extend(data.values())
                except Exception:
                    pass
        if len(tweets) >= 100:
            break

    return tweets


def filter_recent_tweets(tweets, hours=36):
    """Filter tweets from the last N hours."""
    cutoff = datetime.now(BEIJING_TZ) - timedelta(hours=hours)
    recent = []
    for t in tweets:
        created = t.get("created_at") or t.get("date") or t.get("timestamp", "")
        try:
            # Handle ISO format
            if "T" in str(created):
                ts = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
            else:
                ts = datetime.fromisoformat(str(created))
        except Exception:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=BEIJING_TZ)
        if ts >= cutoff.replace(tzinfo=BEIJING_TZ):
            recent.append(t)
    return recent


def analyze_tweets(tweets):
    """Simple keyword-based analysis; return fund signals."""
    text = " ".join(
        t.get("text") or t.get("content") or t.get("body") or ""
        for t in tweets
    ).lower()

    if not text.strip():
        return None

    signals = {}
    for keyword, fund_codes in FUNDS.items():
        if keyword.lower() in text:
            for code in fund_codes:
                signals[code] = signals.get(code, 0) + 1

    if not signals:
        return None

    # Classify: >2 mentions = increase, 1 = hold, 0 = no signal
    result = {"increase": [], "decrease": [], "hold": []}
    all_funds = ["020256", "020973", "007579", "008888", "024418", "012734"]
    for code in all_funds:
        count = signals.get(code, 0)
        if count >= 3:
            result["increase"].append(code)
        elif count >= 1:
            result["hold"].append(code)
        else:
            result["hold"].append(code)

    return result


def format_message(tweets, signals):
    """Format the WeChat push message."""
    now = datetime.now(BEIJING_TZ).strftime("%m-%d %H:%M")
    title = f"🤖 Serenity 信号 {now}"

    # Build body
    lines = []
    if tweets:
        lines.append("📢 最新动态：")
        for t in tweets[:5]:
            text = t.get("text") or t.get("content") or ""
            text = text[:100].replace("\n", " ")
            lines.append(f"  · {text}")
        lines.append("")

    lines.append("📊 基金信号：")
    inc = [f"{FUND_NAMES[c]}({c})" for c in signals["increase"]]
    dec = [f"{FUND_NAMES[c]}({c})" for c in signals["decrease"]]
    hold = [f"{FUND_NAMES[c]}({c})" for c in signals["hold"]]

    if inc:
        lines.append(f"  🟢 增仓：{', '.join(inc)}")
    else:
        lines.append("  🟢 增仓：—")
    if dec:
        lines.append(f"  🔴 减仓：{', '.join(dec)}")
    else:
        lines.append("  🔴 减仓：—")
    lines.append(f"  ⚪ 不动：{', '.join(hold)}")

    return title, "\n".join(lines)


def send_wechat(title, content):
    """Push to WeChat via Server酱."""
    url = f"https://sctapi.ftqq.com/{SENDKEY}.send"
    data = json.dumps({"title": title, "desp": content}).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json;charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main():
    print("Fetching latest tweets...")
    try:
        all_tweets = fetch_latest_tweets()
        print(f"  Got {len(all_tweets)} tweets from archive")
    except Exception as e:
        print(f"  Fetch error: {e}")
        # Fallback: send a minimal message
        send_wechat(
            "🤖 Serenity 信号 (离线)",
            "今日无法获取数据，请手动检查。\n⚪ 不动：全部 6 只"
        )
        return

    recent = filter_recent_tweets(all_tweets)
    print(f"  {len(recent)} recent tweets (36h)")

    if not recent:
        send_wechat(
            "🤖 Serenity 信号 (无新帖)",
            "最近 36 小时无新帖。\n⚪ 不动：全部 6 只"
        )
        return

    signals = analyze_tweets(recent)
    if signals is None:
        send_wechat(
            "🤖 Serenity 信号 (无匹配)",
            "新帖未匹配到机器人/半导体关键词。\n⚪ 不动：全部 6 只"
        )
        return

    title, body = format_message(recent, signals)
    result = send_wechat(title, body)
    print(f"  Push result: {result}")


if __name__ == "__main__":
    main()
