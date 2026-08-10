"""Fictional legacy integration used only to demonstrate the static scanner."""

from googleapiclient.discovery import build

content = build("content", "v2.1")
content.products.insert(merchantId="SYNTHETIC", body={"offerId": "SYNTHETIC-SKU"})
content.productstatuses.list(merchantId="SYNTHETIC")
