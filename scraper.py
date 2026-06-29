#!/usr/bin/env python3
"""Torshov Sport size scraper — checks product 50368 every 5 min for new sizes."""

import asyncio
import json
import logging
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Optional

from playwright.async_api import async_playwright

PRODUCT_ID = int(os.environ.get("PRODUCT_ID", 50368))
URL = os.environ.get(
    "URL",
    "https://www.torshovsport.no/fotball/supporterutstyr/landslag/norge/nike-norge-herrelandslaget-vm-2026-fotballdrakt-hjemme",
)
STATE_FILE = Path(os.environ.get("STATE_FILE", str(Path(__file__).parent / "state.json")))
LOG_FILE = Path(os.environ.get("LOG_FILE", str(Path(__file__).parent / "scraper.log")))
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", 300))

SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER)
SMTP_TO = os.environ.get("SMTP_TO", SMTP_USER)
SMTP_TLS = os.environ.get("SMTP_TLS", "1") == "1"


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("scraper")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s  %(levelname)-5s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    fh = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    return logger


def load_previous_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logging.getLogger("scraper").warning("Could not load previous state: %s", exc)
    return None


def send_email(subject: str, body: str, logger: logging.Logger) -> bool:
    """Send an email alert via SMTP. Returns True on success."""
    if not SMTP_HOST or not SMTP_USER or not SMTP_TO:
        logger.debug("Email not configured — skipping.")
        return False

    msg = MIMEMultipart()
    msg["From"] = SMTP_FROM
    msg["To"] = SMTP_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        if SMTP_TLS:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15)
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_FROM, [SMTP_TO], msg.as_string())
        server.quit()
        logger.info("Email sent to %s: %s", SMTP_TO, subject)
        return True
    except Exception as exc:
        logger.error("Failed to send email: %s", exc)
        return False


class AlertCollector:
    def __init__(self, product_name: str, url: str):
        self.product_name = product_name
        self.url = url
        self.alerts: list[str] = []

    def add(self, msg: str) -> None:
        self.alerts.append(msg)

    def has_alerts(self) -> bool:
        return len(self.alerts) > 0

    def build_email(self) -> tuple[str, str]:
        subject = f"Torshov Sport – {self.product_name}"
        lines = [
            f"Endring oppdaget på {self.product_name}",
            f"URL: {self.url}",
            f"Tid: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]
        lines.extend(self.alerts)
        lines.append("")
        lines.append("— Torshov Sport Scraper")
        return subject, "\n".join(lines)


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _resolve_ref(apollo_state: dict, ref: Optional[dict]) -> Optional[dict]:
    """Resolve a GraphQL reference (object with type="id") to the actual object."""
    if not isinstance(ref, dict) or ref.get("type") != "id":
        return None
    obj = apollo_state.get(ref["id"])
    return obj if isinstance(obj, dict) else None


def _unwrap_json_value(value: Any) -> Any:
    """Unwrap Apollo's {type:'json', json: [...]} encoding."""
    if isinstance(value, dict) and value.get("type") == "json":
        return value.get("json", value)
    return value


def extract_variants(apollo_state: dict, product_id: int) -> list[dict]:
    """Resolve all variant data from the Apollo normalized cache."""
    variants: list[dict] = []
    prefix = f"$Product:{product_id}.variants.values."

    for key, value in apollo_state.items():
        if not isinstance(value, dict):
            continue
        if value.get("__typename") != "ProductVariant":
            continue
        if not key.startswith(prefix):
            continue

        # Resolve stock status
        stock_status = {}
        stock_obj = _resolve_ref(apollo_state, value.get("stockStatus"))
        if stock_obj:
            stock_status = {
                "buyable": stock_obj.get("buyable"),
                "text": stock_obj.get("text"),
                "stockDate": stock_obj.get("stockDate"),
            }

        # Resolve price
        price_data = {}
        price_obj = _resolve_ref(apollo_state, value.get("price"))
        if price_obj:
            price_data = {
                "incVat": price_obj.get("incVat"),
                "exVat": price_obj.get("exVat"),
                "currency": price_obj.get("currency"),
            }

        # Warehouse stock
        warehouse_stock = []
        for ws_ref in value.get("warehouseStock", []):
            ws_obj = _resolve_ref(apollo_state, ws_ref)
            if ws_obj:
                loc_obj = _resolve_ref(apollo_state, ws_obj.get("location"))
                location_name = loc_obj.get("name", "") if loc_obj else ""
                warehouse_stock.append({
                    "location": location_name,
                    "stockLevel": ws_obj.get("stockLevel"),
                })

        # Unwrap the size values
        raw_values = _unwrap_json_value(value.get("values", []))

        variant = {
            "id": key,
            "articleNumber": value.get("articleNumber"),
            "barcode": value.get("barcode"),
            "values": raw_values if isinstance(raw_values, list) else [],
            "stockStatus": stock_status,
            "price": price_data,
            "warehouseStock": warehouse_stock,
        }
        variants.append(variant)

    return variants


def summarize_size(variants: list[dict]) -> dict:
    """Create a summary keyed by size label."""
    summary = {}
    for v in variants:
        size = v["values"][0] if v["values"] else "Unknown"
        summary[size] = {
            "articleNumber": v["articleNumber"],
            "buyable": v["stockStatus"].get("buyable"),
            "stockText": v["stockStatus"].get("text"),
            "priceIncVat": v["price"].get("incVat"),
            "warehouseStock": {ws["location"]: ws["stockLevel"] for ws in v["warehouseStock"]},
        }
    return summary


def build_full_state(variants: list[dict], product_info: dict) -> dict:
    return {
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "product": {
            "id": PRODUCT_ID,
            "name": product_info.get("name", "Unknown"),
            "articleNumber": product_info.get("articleNumber", "Unknown"),
        },
        "sizes": summarize_size(variants),
        "sizeCount": len(variants),
    }


def diff_states(old: Optional[dict], new: dict, logger: logging.Logger, alerts: AlertCollector) -> None:
    if old is None:
        logger.info("First run – no previous state to compare.")
        return

    old_sizes: dict = old.get("sizes", {})
    new_sizes: dict = new.get("sizes", {})

    # Check for new sizes
    for size, info in new_sizes.items():
        if size not in old_sizes:
            stock = "PÅ LAGER" if info["buyable"] else "ikke på lager"
            msg = f"Ny størrelse: {size} ({stock}) — {info['articleNumber']}"
            logger.info("🆕 %s", msg)
            alerts.add(msg)

    # Check for removed sizes
    for size in old_sizes:
        if size not in new_sizes:
            msg = f"Størrelse fjernet: {size}"
            logger.info("🗑 %s", msg)
            alerts.add(msg)

    # Check for stock status changes
    for size, info in new_sizes.items():
        if size in old_sizes:
            old_info = old_sizes[size]
            if old_info["buyable"] != info["buyable"]:
                if info["buyable"]:
                    msg = f"{size} ER NÅ PÅ LAGER! — {info['articleNumber']} — {info['priceIncVat']} kr"
                    logger.info("✅ %s", msg)
                    alerts.add(msg)
                else:
                    msg = f"{size} gikk utsolgt — {info['articleNumber']}"
                    logger.info("❌ %s", msg)
                    alerts.add(msg)

            if old_info["priceIncVat"] != info["priceIncVat"]:
                msg = f"{size} prisendring: {old_info['priceIncVat']} → {info['priceIncVat']} kr"
                logger.info("💲 %s", msg)
                alerts.add(msg)


async def scrape(logger: logging.Logger) -> None:
    logger.info("=" * 50)
    logger.info("Starting scrape of %s", URL)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            logger.debug("Navigating to product page...")
            await page.goto(URL, timeout=30000)
            await page.wait_for_timeout(5000)  # Let React hydrate

            # Extract Apollo state directly from the JavaScript context
            logger.debug("Extracting Apollo state...")
            apollo_data = await page.evaluate(
                """() => {
                    const state = window.__APOLLO_STATE__;
                    if (!state) return {error: 'No __APOLLO_STATE__ found'};

                    const relevant = {};
                    const productKey = 'Product:""" + str(PRODUCT_ID) + """';
                    const variantPrefix = '$' + productKey + '.variants.values.';

                    for (const key in state) {
                        if (key === productKey) {
                            relevant[key] = {name: state[key].name, articleNumber: state[key].articleNumber, hasVariants: state[key].hasVariants};
                        }

                        // Include all ProductVariant entries for this product
                        if (key.startsWith(variantPrefix) && state[key].__typename === 'ProductVariant') {
                            relevant[key] = state[key];
                        }

                        // Include referenced StockStatus, Price, Warehouse, Store
                        const typename = state[key].__typename;
                        if (typename === 'StockStatus' || typename === 'Price' || typename === 'Warehouse' || typename === 'Store') {
                            relevant[key] = state[key];
                        }
                    }
                    return relevant;
                }"""
            )

            if "error" in apollo_data:
                logger.error("Failed: %s", apollo_data["error"])
                return

            product_info = apollo_data.get(f"Product:{PRODUCT_ID}", {})

            variants = extract_variants(apollo_data, PRODUCT_ID)
            logger.debug("Raw variants found: %d", len(variants))

            if not variants:
                logger.warning("No variant data found in Apollo state!")
                return

            # Build full state
            new_state = build_full_state(variants, product_info)

            # Compare with previous
            previous = load_previous_state()
            alerts = AlertCollector(
                product_name=new_state["product"]["name"],
                url=URL,
            )
            diff_states(previous, new_state, logger, alerts)

            # Send email if there are alerts
            if alerts.has_alerts():
                subject, body = alerts.build_email()
                send_email(subject, body, logger)

            # Log current state
            logger.info("Product: %s (%s)", new_state["product"]["name"], new_state["product"]["articleNumber"])
            logger.info("Size count: %d", new_state["sizeCount"])
            for size, info in new_state["sizes"].items():
                stock_symbol = "✅" if info["buyable"] else "❌"
                logger.info("  %s %s  %s (%s)  %s kr",
                            stock_symbol, size, info["stockText"], info["articleNumber"], info["priceIncVat"])
                for loc, level in info["warehouseStock"].items():
                    if level != 0:
                        logger.info("    🏪 %s: %d", loc, level)

            # Save state
            save_state(new_state)
            logger.info("State saved to %s", STATE_FILE)

        except Exception as exc:
            logger.error("Scrape failed: %s", exc, exc_info=True)
        finally:
            await browser.close()
            logger.info("Scrape finished.")


async def main_loop() -> None:
    logger = setup_logging()
    logger.info("🚀 Torshov Sport size scraper started")
    logger.info("Product ID: %d — %s", PRODUCT_ID, URL)
    logger.info("Polling every %d seconds", POLL_INTERVAL)

    while True:
        await scrape(logger)
        logger.info("Sleeping for %d seconds...\n", POLL_INTERVAL)
        await asyncio.sleep(POLL_INTERVAL)


async def main_once() -> None:
    logger = setup_logging()
    logger.info("🚀 Torshov Sport size scraper (single run)")
    await scrape(logger)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Torshov Sport size scraper")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    if args.once:
        asyncio.run(main_once())
    else:
        asyncio.run(main_loop())
