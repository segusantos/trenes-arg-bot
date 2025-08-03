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

    for summary in soup.find_all("summary"):
        line = summary.get_text(strip=True)
        if not line:
            continue            

        p_container = summary.find_parent("p")
        if not p_container:
            continue

        current = p_container.next_sibling
        while current.name != "p":
            if current.name == "div" and "alert" in current.get("class", []):
                alert = build_alert(current)
                if alert:
                    alerts_by_line[line].append(alert)
            current = current.next_sibling

    return alerts_by_line


def build_alert(alert_div: Tag) -> dict:
    media_body = alert_div.find("div", class_="media-body")
    if not media_body:
        return {}
        
    h5 = media_body.find("h5", class_="h5")
    title = h5.get_text(strip=True) if h5 else ""
    
    p_element = media_body.find("p", class_="margin-0")
    description = (p_element.decode_contents()
                            .replace("<strong>", "<b>").replace("</strong>", "</b>")
                            .replace("blank:#", "")
                            .strip()) if p_element else ""

    alert_classes = alert_div.get("class", [])
    alert_type = next((cls.split("-")[1] for cls in alert_classes if cls.startswith("alert-")), "info")

    return {
        "type": alert_type,
        "title": title,
        "description": description,
    }
