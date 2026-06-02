"""Konfigurasi logo brand yang env-driven.

Satu sumber kebenaran untuk logo di seluruh app (desk, web/portal, print/PDF,
dan app eksternal seperti portal React) lewat environment variable / site_config.

Urutan prioritas tiap logo:
    1. site_config.json / common_site_config.json  (per-site / per-bench)
    2. OS environment variable                      (mis. dari docker-compose)
    3. default: file ter-bundle di public/images app ini

Atur via salah satu:
    # common_site_config.json (berlaku ke semua site di bench)
    {"brand_logo_main": "...", "brand_logo_pdf": "..."}

    # atau environment (docker-compose):
    BRAND_LOGO_MAIN=https://cdn.contoh.com/oak-emblem.png
    BRAND_LOGO_PDF=https://cdn.contoh.com/oak-logo.png

Nilainya boleh path asset Frappe (/assets/...), path file (/files/...),
atau URL absolut (CDN).
"""

import os

import frappe

# Default ter-bundle (dilayani Frappe di /assets/<app>/...)
DEFAULT_MAIN = "/assets/container_depot/images/oak-emblem.png"  # emblem (navbar/web)
DEFAULT_PDF = "/assets/container_depot/images/oak-logo.png"     # logo lengkap (PDF)


def _resolve(conf_key: str, env_key: str, default: str) -> str:
    """Resolve nilai logo mengikuti urutan prioritas."""
    value = None
    try:
        # frappe.conf = site_config + common_site_config (butuh konteks site)
        value = frappe.conf.get(conf_key)
    except Exception:
        value = None
    if not value:
        value = os.getenv(env_key)
    return value or default


def get_logo_main() -> str:
    """Logo utama (navbar desk, web/portal) — emblem."""
    return _resolve("brand_logo_main", "BRAND_LOGO_MAIN", DEFAULT_MAIN)


def get_logo_pdf() -> str:
    """Logo untuk dokumen/print/PDF — logo lengkap dengan teks."""
    return _resolve("brand_logo_pdf", "BRAND_LOGO_PDF", DEFAULT_PDF)


@frappe.whitelist(allow_guest=True)
def get_branding() -> dict:
    """Endpoint publik agar app lain (portal React, dll) ambil logo yang sama.

    GET /api/method/container_depot.branding.get_branding
    """
    return {"logo_main": get_logo_main(), "logo_pdf": get_logo_pdf()}


def update_website_context(context):
    """Set logo navbar website/portal dari env (dipanggil hook update_website_context)."""
    context["app_logo_url"] = get_logo_main()
    return context
