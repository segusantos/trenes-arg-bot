from collections import defaultdict
import httpx
from bs4 import BeautifulSoup, Tag


async def scrape_alerts(url: str) -> defaultdict[str, list[dict]]:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
    return parse_alerts(BeautifulSoup(response.text, "html.parser"))


def parse_alerts(soup: BeautifulSoup) -> defaultdict[str, list[dict]]:
    alerts_by_line = defaultdict(list)

    summaries = soup.find_all("summary")
    for summary in summaries:
        line = summary.get_text(strip=True)
        if not line:
            continue

        header_container = summary.find_parent("p") or summary.find_parent("details") or summary

        curr = header_container.next_sibling
        while curr:
            if isinstance(curr, Tag):
                if curr.find("summary") or curr.name in ["summary", "details"]:
                    break

                if curr.name == "div" and "alert" in curr.get("class", []):
                    alert = build_alert(curr)
                    if alert:
                        alerts_by_line[line].append(alert)
                else:
                    for alert_div in curr.find_all("div", class_="alert"):
                        alert = build_alert(alert_div)
                        if alert:
                            alerts_by_line[line].append(alert)
            curr = curr.next_sibling

    return alerts_by_line


def build_alert(alert_div: Tag) -> dict:
    media_body = alert_div.find("div", class_="media-body")
    if not media_body:
        return {}

    h5 = media_body.find(["h5", "p"], class_="h5")
    title = h5.get_text(strip=True) if h5 else ""

    p_elements = media_body.find_all("p")
    desc_p = [p for p in p_elements if p != h5 and "h5" not in p.get("class", [])]
    if desc_p:
        description = ("\n".join(p.decode_contents() for p in desc_p)
                        .replace("<strong>", "<b>").replace("</strong>", "</b>")
                        .replace("&nbsp;", " ")
                        .replace("blank:#", "")
                        .strip())
    else:
        description = ""

    alert_classes = alert_div.get("class", [])
    alert_type = next((cls.split("-")[1] for cls in alert_classes if cls.startswith("alert-")), "info")

    return {
        "type": alert_type,
        "title": title,
        "description": description,
    }

