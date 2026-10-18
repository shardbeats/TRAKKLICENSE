"""Canonical variables for TRAKKLICENSE.

Supports BeatStars {VAR} + TRAKK {{var}} syntax.
Alias map keeps PRODUCT_* = TRACK_* compatibility.
No personal data here — only variable names + descriptions.
"""

VARIABLES = {
    "CONTRACT_DATE": "Transaction Date",
    "COUNTRY": "Arbitration Country where Governing Law is applied",
    "CUSTOMER_ADDRESS": "Customer Address (when available)",
    "CUSTOMER_ALIAS": "Customer Artist Name",
    "CUSTOMER_IPI": "Customer IPI/CAE identifier (optional, renders only when filled)",
    "CUSTOMER_FULLNAME": "Customer's Fullname",
    "DISTRIBUTE_COPIES": "Number of Distribution Copies allowed (number)",
    "DISTRIBUTE_COPIES_WORD": "Number of Distribution Copies allowed (in words)",
    "FILE_TYPE": "File Types included in this License",
    "LICENSE_NAME": "Name of License",
    "PRODUCER_ALIAS": "Producer Display Name",
    "PRODUCER_IPI": "Producer IPI/CAE identifier (optional, renders only when filled)",
    "PRODUCT_OWNER_FULLNAME": "Full Name of Owner",
    "PRODUCT_PRICE": "Price of Product",
    "PRODUCT_PRICE_WORD": "Product Price (in words)",
    "PRODUCT_TITLE": "Name of Product (beat title)",
    "PUBLISHING_RIGHTS": "Publishing Rights Based on Seller/Buyer Agreement",
    "PUBLISHING_SHARES": "Publishing Share (e.g. 50/50)",
    "ROYALTY_AMOUNT": "Percentage of Licensee's Net Receipts",
    "SAMPLES": "List of Samples Used on This Beat",
    "STATE_PROVINCE_COUNTRY": "Arbitration State/Province and Country",
    # Extended (BeatStars compat + exclusive template needs)
    "TRACK_TITLE": "Alias of PRODUCT_TITLE",
    "TRACK_PRICE": "Alias of PRODUCT_PRICE",
    "AUDIO_STREAMS": "Monetized audio streams allowed",
    "AUDIO_STREAMS_WORD": "Audio streams allowed (in words)",
    "TERM_YEARS": "License term in years",
    "TERM_START": "License term start date",
    "TERM_END": "License term end date",
    "CREDIT_LINE": "Producer credit line (e.g. Prod. by X)",
    "GOVERNING_LAW": "Governing law text",
    "FOLIO": "License folio (e.g. LIC-2026-0001, DRAFT in preview)",
}

# Alias → canonical. Renderer resolves alias first.
ALIASES = {
    "TRACK_TITLE": "PRODUCT_TITLE",
    "TRACK_PRICE": "PRODUCT_PRICE",
    "TRACK_PRICE_WORD": "PRODUCT_PRICE_WORD",
    "TRACK_OWNER_FULLNAME": "PRODUCT_OWNER_FULLNAME",
    "DISTRIBUTE_COPIES": "DISTRIBUTE_COPIES",
}
