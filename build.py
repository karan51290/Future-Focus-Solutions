#!/usr/bin/env python3
"""Assembles the static Future Focus Solutions site from page fragments + shared shell.
Run: python3 build.py   (from the project root)

Single source of truth for business details is business.json - edit that file
and re-run this script; it propagates into every page's header/footer/nav,
body copy, and the client-side WhatsApp form via js/business-config.js.

All internal links and asset paths are computed as real relative paths per
page (not root-relative "/..." paths), so the generated output works
identically opened directly via file://, from any local static server, and
once deployed (GitHub Pages or a custom domain) - no server-relative
resolution required anywhere.
"""
import json
import os
import posixpath
import re
import urllib.parse

SITE_DIR = os.path.dirname(os.path.abspath(__file__))
PAGES_DIR = os.path.join(SITE_DIR, "pages")

with open(os.path.join(SITE_DIR, "business.json"), encoding="utf-8") as f:
    BUSINESS = json.load(f)

GOOGLE_LINK = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote_plus(BUSINESS["address"])
WHATSAPP_URL_GENERIC = f'https://wa.me/{BUSINESS["whatsappNumber"]}?text=' + urllib.parse.quote_plus(
    f'Hi {BUSINESS["name"]}! I\'d like to talk to someone.'
)

# ---------------------------------------------------------------------------
# Output paths (key -> path relative to site root). Explicit "index.html"
# filenames throughout (never a bare "about/") so every link is a real,
# directly-openable file under file:// as well as any HTTP server.
# ---------------------------------------------------------------------------
OUTPUT_PATHS = {
    "home": "index.html",
    "about": "about/index.html",
    "services": "services/index.html",
    "financial-planning": "services/financial-planning/index.html",
    "mutual-funds": "services/mutual-funds/index.html",
    "retirement-tax-planning": "services/retirement-tax-planning/index.html",
    "insurance": "services/insurance/index.html",
    "loans": "services/loans/index.html",
    "real-estate": "services/real-estate/index.html",
    "debt-collection-recovery": "services/debt-collection-recovery/index.html",
    "market-insights": "market-insights/index.html",
    "contact": "contact/index.html",
    "privacy-policy": "privacy-policy/index.html",
    "terms-and-conditions": "terms-and-conditions/index.html",
}

SERVICE_KEYS = [
    ("financial-planning", "Financial Planning"),
    ("mutual-funds", "Mutual Funds"),
    ("retirement-tax-planning", "Retirement &amp; Tax Planning"),
    ("insurance", "Insurance"),
    ("loans", "Loans"),
    ("real-estate", "Real Estate"),
    ("debt-collection-recovery", "Debt Collection &amp; Recovery"),
]

TOP_NAV = [
    ("home", "Home"),
    ("about", "About Us"),
    # "services" handled separately as a dropdown
    ("market-insights", "Market Insights"),
    ("contact", "Contact"),
]


def rel(from_key, to_key_or_path):
    """Relative path from page `from_key`'s output location to another
    page (by key) or a root-relative asset path like 'assets/...'."""
    from_dir = posixpath.dirname(OUTPUT_PATHS[from_key])
    to_path = OUTPUT_PATHS.get(to_key_or_path, to_key_or_path)
    if from_dir == "":
        return to_path
    return posixpath.relpath(to_path, from_dir)


# ---------------------------------------------------------------------------
# Fragment token resolution ({{FIELD}} + single-level {{#FIELD}}...{{/FIELD}})
# ---------------------------------------------------------------------------
SIMPLE_TOKENS = {
    "NAME": BUSINESS["name"],
    "ADDRESS": BUSINESS["address"],
    "PHONE": BUSINESS["phoneTel"],
    "WHATSAPP": BUSINESS["whatsappNumber"],
    "EMAIL": BUSINESS["email"],
    "GOOGLE_LINK": GOOGLE_LINK,
}

CONDITIONAL_TRUTHY = {
    "ADDRESS": bool(BUSINESS.get("address")),
    "WHATSAPP": bool(BUSINESS.get("whatsappNumber")),
    "EMAIL": bool(BUSINESS.get("email")),
    "GOOGLE_LINK": bool(GOOGLE_LINK),
}


def resolve_conditionals(text):
    def repl(m):
        field, inner = m.group(1), m.group(2)
        return inner if CONDITIONAL_TRUTHY.get(field, True) else ""
    # non-nested {{#FIELD}}...{{/FIELD}} blocks
    pattern = re.compile(r"\{\{#(\w+)\}\}(.*?)\{\{/\1\}\}", re.S)
    return pattern.sub(repl, text)


def resolve_tokens(text):
    text = resolve_conditionals(text)
    for token, value in SIMPLE_TOKENS.items():
        text = text.replace("{{%s}}" % token, value)
    return text


# Directory-style root-relative path (as authored in fragment body copy,
# e.g. CTA links and hero images) -> page key / asset root. Fragments were
# originally hand-authored against this scheme before the build script
# existed; rewrite them here to real relative paths per output page.
DIR_PATH_TO_KEY = {"/" + posixpath.dirname(p) + ("/" if posixpath.dirname(p) else ""): k for k, p in OUTPUT_PATHS.items()}
DIR_PATH_TO_KEY["/"] = "home"


def fix_internal_paths(text, page_key):
    def fix_href(m):
        val = m.group(1)
        if val in DIR_PATH_TO_KEY:
            return f'href="{rel(page_key, DIR_PATH_TO_KEY[val])}"'
        return m.group(0)

    text = re.sub(r'href="(/[a-zA-Z0-9\-/]*/)"', fix_href, text)
    text = re.sub(r'src="/(assets/[^"]*)"', lambda m: f'src="{rel(page_key, m.group(1))}"', text)
    return text


# ---------------------------------------------------------------------------
# Nav rendering
# ---------------------------------------------------------------------------
def desktop_nav(page_key, active_service=None):
    parts = []
    for key, label in TOP_NAV[:2]:  # Home, About Us
        cls = "text-sm font-medium text-white transition-colors" if key == page_key else "text-sm font-medium hover:text-white transition-colors"
        parts.append(f'<a href="{rel(page_key, key)}" class="{cls}">{label}</a>')

    services_active = page_key == "services" or active_service is not None
    services_btn_cls = "text-sm font-medium text-white transition-colors flex items-center gap-1" if services_active else "text-sm font-medium hover:text-white transition-colors flex items-center gap-1"
    dropdown_items = []
    for skey, slabel in SERVICE_KEYS:
        item_cls = "block px-5 py-2.5 text-sm text-primary font-semibold hover:bg-surface-elevated-dark transition-colors" if skey == active_service else "block px-5 py-2.5 text-sm text-body hover:bg-surface-elevated-dark hover:text-white transition-colors"
        dropdown_items.append(f'<a href="{rel(page_key, skey)}" class="{item_cls}">{slabel}</a>')
    parts.append(f'''<div class="relative group">
        <button class="{services_btn_cls}">
          Services
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 9 6 6 6-6"/></svg>
        </button>
        <div class="absolute left-0 top-full pt-3 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200">
          <div class="bg-surface-card-dark border border-hairline-on-dark rounded-xl2 shadow-2xl py-2 w-64">
            {''.join(dropdown_items)}
            <div class="border-t border-hairline-on-dark mt-2 pt-2">
              <a href="{rel(page_key, 'services')}" class="block px-5 py-2.5 text-sm font-semibold text-primary hover:bg-surface-elevated-dark transition-colors">All Services →</a>
            </div>
          </div>
        </div>
      </div>''')

    for key, label in TOP_NAV[2:]:  # Market Insights, Contact
        cls = "text-sm font-medium text-white transition-colors" if key == page_key else "text-sm font-medium hover:text-white transition-colors"
        parts.append(f'<a href="{rel(page_key, key)}" class="{cls}">{label}</a>')

    return "\n      ".join(parts)


def mobile_nav(page_key, active_service=None):
    parts = []
    for key, label in [("home", "Home"), ("about", "About Us")]:
        parts.append(f'<a href="{rel(page_key, key)}" class="mobile-link text-white border-b border-hairline-on-dark py-4">{label}</a>')
    parts.append(f'<a href="{rel(page_key, "services")}" class="mobile-link text-white border-b border-hairline-on-dark py-4">Services</a>')
    for skey, slabel in SERVICE_KEYS:
        cls = "mobile-link text-primary font-semibold border-b border-hairline-on-dark py-3 pl-4 text-sm" if skey == active_service else "mobile-link text-muted-strong border-b border-hairline-on-dark py-3 pl-4 text-sm"
        parts.append(f'<a href="{rel(page_key, skey)}" class="{cls}">{slabel}</a>')
    for key, label in [("market-insights", "Market Insights"), ("contact", "Contact")]:
        parts.append(f'<a href="{rel(page_key, key)}" class="mobile-link text-white border-b border-hairline-on-dark py-4">{label}</a>')
    return "\n    ".join(parts)


# ---------------------------------------------------------------------------
# Shell
# ---------------------------------------------------------------------------
def render_shell(page_key, title, description, body, whatsapp_message, active_service=None):
    a = lambda k: rel(page_key, k)  # noqa: E731 - short alias, used heavily below
    logo_white = a("assets/logo/logo-white.png")
    icon_white = a("assets/logo/icon-white.png")
    logo_color = a("assets/logo/logo-color.png")
    favicon = a("assets/logo/icon-color.png")

    wa_fab_text = urllib.parse.quote_plus(whatsapp_message)
    wa_fab_url = f'https://wa.me/{BUSINESS["whatsappNumber"]}?text={wa_fab_text}'

    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="icon" type="image/png" href="{favicon}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&amp;family=JetBrains+Mono:wght@500;700&amp;display=swap" rel="stylesheet">
<script src="https://cdn.tailwindcss.com"></script>
<script>
  tailwind.config = {{
    theme: {{
      extend: {{
        colors: {{
          primary: '#FBBE07',
          'primary-active': '#E0A800',
          'primary-disabled': '#4A430F',
          'canvas-dark': '#0A1F16',
          'canvas-light': '#FFFFFF',
          'surface-card-dark': '#12291D',
          'surface-elevated-dark': '#1B3A28',
          'surface-soft-light': '#FAFAF5',
          'surface-strong-light': '#F2F0E6',
          ink: '#0F1A14',
          body: '#E7ECE8',
          'body-on-light': '#0F1A14',
          muted: '#8AA398',
          'muted-strong': '#A9BFB2',
          'muted-on-light': '#4B6358',
          'hairline-on-dark': '#1B3A28',
          'hairline-on-light': '#E4E7E2',
          emerald: '#2D834D',
          'on-primary': '#0F1A14',
          info: '#3b82f6',
        }},
        fontFamily: {{
          sans: ['Inter', 'sans-serif'],
          mono: ['JetBrains Mono', 'monospace'],
        }},
        spacing: {{ section: '80px' }},
        borderRadius: {{ xl2: '14px' }},
      }}
    }}
  }}
</script>
<style>
  .header-transition{{transition:transform .35s ease, background-color .3s ease, box-shadow .3s ease}}
  .header-hidden{{transform:translateY(-100%)}}
  .reveal{{opacity:0;transform:translateY(28px);transition:opacity .7s cubic-bezier(.16,1,.3,1), transform .7s cubic-bezier(.16,1,.3,1)}}
  .reveal.in-view{{opacity:1;transform:translateY(0)}}
  .no-scrollbar::-webkit-scrollbar{{display:none}}
  .no-scrollbar{{-ms-overflow-style:none;scrollbar-width:none}}
  ::selection{{background:#FBBE07;color:#0F1A14}}
</style>
</head>
<body class="bg-canvas-dark text-body font-sans antialiased overflow-x-hidden">

<div class="bg-surface-card-dark text-muted-strong text-[13px] hidden sm:block">
  <div class="max-w-[1280px] mx-auto px-6 h-10 flex items-center justify-end gap-6">
    <a href="mailto:{BUSINESS['email']}" class="hover:text-primary transition-colors flex items-center gap-2">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16v16H4z" stroke="none"/><path d="M22 6 12 13 2 6" stroke-width="2" fill="none"/><path d="M2 6h20v12H2z" fill="none" stroke-width="2"/></svg>
      {BUSINESS['email']}
    </a>
    <a href="tel:{BUSINESS['phoneTel']}" class="hover:text-primary transition-colors flex items-center gap-2">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
      {BUSINESS['phone']}
    </a>
  </div>
</div>

<header id="main-header" class="sticky top-0 left-0 w-full z-50 bg-canvas-dark border-b border-hairline-on-dark header-transition">
  <div class="max-w-[1280px] mx-auto w-full px-6 h-[88px] flex items-center justify-between">
    <a href="{a('home')}" class="flex items-center shrink-0">
      <img src="{logo_white}" alt="{BUSINESS['name']} logo" class="h-14 md:h-16 w-auto hidden sm:block">
      <img src="{icon_white}" alt="{BUSINESS['name']} logo" class="h-12 w-auto sm:hidden">
    </a>

    <nav class="hidden lg:flex items-center gap-8">
      {desktop_nav(page_key, active_service)}
    </nav>

    <div class="flex items-center gap-4">
      <a href="{a('contact')}" class="hidden lg:flex bg-primary hover:bg-primary-active text-on-primary font-semibold text-sm px-6 py-3 rounded-md transition-colors h-[44px] items-center">
        Book a Free Consultation
      </a>
      <button id="mobile-menu-btn" class="lg:hidden text-white p-2" aria-label="Open menu">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="18" y2="18"/></svg>
      </button>
    </div>
  </div>
</header>

<div id="mobile-menu" class="fixed inset-0 bg-canvas-dark z-[60] transform translate-x-full transition-transform duration-300 pt-6 px-6 overflow-y-auto">
  <div class="flex items-center justify-between mb-8">
    <img src="{logo_white}" alt="{BUSINESS['name']} logo" class="h-11 w-auto">
    <button id="mobile-menu-close" class="text-white p-2" aria-label="Close menu">
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
    </button>
  </div>
  <nav class="flex flex-col gap-1 text-base font-medium">
    {mobile_nav(page_key, active_service)}
    <a href="{a('contact')}" class="mobile-link bg-primary text-on-primary font-semibold text-center rounded-md py-3.5 mt-6">Book a Free Consultation</a>
    <a href="tel:{BUSINESS['phoneTel']}" class="mobile-link text-primary mt-6 font-semibold text-center">{BUSINESS['phone']}</a>
  </nav>
</div>

<main>
{body}
</main>

<footer class="bg-surface-soft-light text-body-on-light">
  <div class="max-w-[1280px] mx-auto px-6 py-16 grid grid-cols-2 md:grid-cols-5 gap-10">
    <div class="col-span-2 flex flex-col justify-between">
      <img src="{logo_color}" alt="{BUSINESS['name']} logo" class="h-20 md:h-24 w-auto self-start">
      <div>
        <p class="text-[13px] text-muted-on-light max-w-sm leading-[1.6] mb-6">{BUSINESS['name']} is a Chennai-based financial services team covering planning, mutual funds, insurance, loans, real estate, and debt recovery - one team, so your finances don't end up scattered across six different advisors.</p>
        <div class="flex gap-4">
          <a href="{BUSINESS['social']['facebook']}" target="_blank" rel="noopener noreferrer" aria-label="Facebook" class="w-9 h-9 rounded-full bg-surface-strong-light flex items-center justify-center text-ink hover:bg-primary transition-colors"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M22 12a10 10 0 1 0-11.6 9.9v-7H7.9V12h2.5V9.8c0-2.5 1.5-3.9 3.8-3.9 1.1 0 2.2.2 2.2.2v2.5h-1.3c-1.2 0-1.6.8-1.6 1.6V12h2.8l-.4 2.9h-2.4v7A10 10 0 0 0 22 12z"/></svg></a>
          <a href="{BUSINESS['social']['instagram']}" target="_blank" rel="noopener noreferrer" aria-label="Instagram" class="w-9 h-9 rounded-full bg-surface-strong-light flex items-center justify-center text-ink hover:bg-primary transition-colors"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="20" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1"/></svg></a>
        </div>
      </div>
    </div>
    <div>
      <h4 class="font-semibold text-[14px] mb-4">Quick Links</h4>
      <ul class="space-y-3">
        <li><a href="{a('about')}" class="text-[13px] text-muted-on-light hover:text-emerald transition-colors">About Us</a></li>
        <li><a href="{a('services')}" class="text-[13px] text-muted-on-light hover:text-emerald transition-colors">Services</a></li>
        <li><a href="{a('market-insights')}" class="text-[13px] text-muted-on-light hover:text-emerald transition-colors">Market Insights</a></li>
        <li><a href="{a('contact')}" class="text-[13px] text-muted-on-light hover:text-emerald transition-colors">Contact</a></li>
      </ul>
    </div>
    <div>
      <h4 class="font-semibold text-[14px] mb-4">Services</h4>
      <ul class="space-y-3">
        {''.join(f'<li><a href="{a(skey)}" class="text-[13px] text-muted-on-light hover:text-emerald transition-colors">{slabel}</a></li>' for skey, slabel in SERVICE_KEYS)}
      </ul>
    </div>
    <div>
      <h4 class="font-semibold text-[14px] mb-4">Contact</h4>
      <ul class="space-y-3 text-[13px] text-muted-on-light leading-[1.6]">
        <li>{BUSINESS['name']}</li>
        <li>{BUSINESS['address']}</li>
        <li><a href="tel:{BUSINESS['phoneTel']}" class="hover:text-emerald transition-colors">{BUSINESS['phone']}</a></li>
        <li>WhatsApp: <a href="https://wa.me/{BUSINESS['whatsappNumber']}" class="hover:text-emerald transition-colors">{BUSINESS['whatsappDisplay']}</a></li>
        <li><a href="mailto:{BUSINESS['email']}" class="hover:text-emerald transition-colors">{BUSINESS['email']}</a></li>
      </ul>
    </div>
  </div>
  <div class="max-w-[1280px] mx-auto px-6 pb-8">
    <div class="flex flex-col sm:flex-row justify-between items-center gap-4 pt-6 border-t border-hairline-on-light text-[12px] text-muted-on-light">
      <p>© {BUSINESS['name']} {BUSINESS['copyrightYear']}. All rights reserved.</p>
      <div class="flex gap-6">
        <a href="{a('privacy-policy')}" class="hover:text-emerald transition-colors">Privacy Policy</a>
        <a href="{a('terms-and-conditions')}" class="hover:text-emerald transition-colors">Terms &amp; Conditions</a>
      </div>
    </div>
  </div>
</footer>

<div class="fixed bottom-5 right-5 md:bottom-8 md:right-8 z-50 flex flex-col gap-3">
  <button id="scroll-top" aria-label="Scroll to top" class="w-11 h-11 md:w-12 md:h-12 bg-surface-card-dark border border-hairline-on-dark rounded-full flex items-center justify-center text-white hover:bg-surface-elevated-dark transition-all opacity-0 translate-y-4 pointer-events-none shadow-lg">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 15l-6-6-6 6"/></svg>
  </button>
  <a href="tel:{BUSINESS['phoneTel']}" aria-label="Call us" class="w-11 h-11 md:w-12 md:h-12 bg-primary rounded-full flex items-center justify-center text-on-primary hover:scale-105 transition-transform shadow-lg">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
  </a>
  <a href="{wa_fab_url}" target="_blank" rel="noopener noreferrer" aria-label="Chat on WhatsApp" class="w-11 h-11 md:w-12 md:h-12 bg-emerald rounded-full flex items-center justify-center text-white hover:scale-105 transition-transform shadow-lg">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
  </a>
</div>

<script src="{a('js/business-config.js')}"></script>
<script>
  (function(){{
    let lastScroll = 0;
    const header = document.getElementById('main-header');
    window.addEventListener('scroll', () => {{
      const cur = window.pageYOffset;
      if (cur <= 0) {{ header.classList.remove('header-hidden'); return; }}
      if (cur > lastScroll && cur > 120) header.classList.add('header-hidden');
      else header.classList.remove('header-hidden');
      lastScroll = cur;
    }}, {{ passive: true }});
  }})();

  (function(){{
    const btn = document.getElementById('scroll-top');
    window.addEventListener('scroll', () => {{
      if (window.pageYOffset > 500) btn.classList.remove('opacity-0','translate-y-4','pointer-events-none');
      else btn.classList.add('opacity-0','translate-y-4','pointer-events-none');
    }}, {{ passive: true }});
    btn.addEventListener('click', () => window.scrollTo({{ top: 0, behavior: 'smooth' }}));
  }})();

  (function(){{
    const btn = document.getElementById('mobile-menu-btn');
    const closeBtn = document.getElementById('mobile-menu-close');
    const menu = document.getElementById('mobile-menu');
    const links = document.querySelectorAll('.mobile-link');
    function open(){{ menu.classList.remove('translate-x-full'); document.body.classList.add('overflow-hidden'); }}
    function close(){{ menu.classList.add('translate-x-full'); document.body.classList.remove('overflow-hidden'); }}
    btn.addEventListener('click', open);
    closeBtn.addEventListener('click', close);
    links.forEach(l => l.addEventListener('click', close));
  }})();

  (function(){{
    const els = document.querySelectorAll('.reveal');
    const io = new IntersectionObserver((entries) => {{
      entries.forEach(e => {{ if (e.isIntersecting) {{ e.target.classList.add('in-view'); io.unobserve(e.target); }} }});
    }}, {{ threshold: 0.15, rootMargin: '0px 0px -40px 0px' }});
    els.forEach(el => io.observe(el));
  }})();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Page registry: key -> (title, meta description, whatsapp fab message, active_service)
# ---------------------------------------------------------------------------
PAGES = [
    ("home", f"{BUSINESS['name']} - Financial Planning, Mutual Funds, Insurance, Loans, Real Estate & Debt Recovery in Chennai",
     "One team across financial planning, mutual funds, retirement &amp; tax planning, insurance, loans, real estate, and debt recovery in Chennai. Book a free consultation.",
     f"Hi {BUSINESS['name']}! I'd like to talk to someone.", None),
    ("about", f"About Us - {BUSINESS['name']}",
     f"One team across financial planning, mutual funds, insurance, loans, real estate, and debt recovery in Chennai - meet {BUSINESS['name']}.",
     f"Hi {BUSINESS['name']}! I'd like to talk to someone.", None),
    ("services", f"Services - {BUSINESS['name']}",
     "Seven services, one team, one plan: financial planning, mutual funds, retirement & tax planning, insurance, loans, real estate, and debt recovery.",
     f"Hi {BUSINESS['name']}! I'd like to talk to someone about your services.", None),
    ("financial-planning", f"Financial Planning - {BUSINESS['name']}",
     "One plan for your income, savings, investments, and goals - not a different answer from every product you ask about.",
     f"Hi {BUSINESS['name']}! I'd like to talk to someone about Financial Planning.", "financial-planning"),
    ("mutual-funds", f"Mutual Funds - {BUSINESS['name']}",
     "Fund selection matched to your goals and timeline, with plain answers about risk, cost, and what you're actually invested in.",
     f"Hi {BUSINESS['name']}! I'd like to talk to someone about Mutual Funds.", "mutual-funds"),
    ("retirement-tax-planning", f"Retirement &amp; Tax Planning - {BUSINESS['name']}",
     "Build the income you'll need later, and keep more of what you earn now.",
     f"Hi {BUSINESS['name']}! I'd like to talk to someone about Retirement & Tax Planning.", "retirement-tax-planning"),
    ("insurance", f"Insurance - {BUSINESS['name']}",
     "Cover for your health, your life, your vehicle, your home, and your business - matched to what you actually need.",
     f"Hi {BUSINESS['name']}! I'd like to talk to someone about Insurance.", "insurance"),
    ("loans", f"Loans - {BUSINESS['name']}",
     "Personal, home, car, and business loans - we shop the rates so you don't take the first offer you're given.",
     f"Hi {BUSINESS['name']}! I'd like to talk to someone about Loans.", "loans"),
    ("real-estate", f"Real Estate - {BUSINESS['name']}",
     "Buy, sell, or invest - with someone who's also looking at your whole financial plan.",
     f"Hi {BUSINESS['name']}! I'd like to talk to someone about Real Estate.", "real-estate"),
    ("debt-collection-recovery", f"Debt Collection &amp; Recovery - {BUSINESS['name']}",
     "Structured, compliant recovery for secured and unsecured accounts - for businesses and lenders.",
     f"Hi {BUSINESS['name']}! I'd like to talk to someone about Debt Collection & Recovery.", "debt-collection-recovery"),
    ("market-insights", f"Market Insights - {BUSINESS['name']}",
     "Stocks and commodities - what's moving, in plain language.",
     f"Hi {BUSINESS['name']}! I'd like to talk to someone.", None),
    ("contact", f"Contact Us - {BUSINESS['name']}",
     "One free consultation. Tell us what you're trying to solve.",
     f"Hi {BUSINESS['name']}! I'd like to talk to someone.", None),
    ("privacy-policy", f"Privacy Policy - {BUSINESS['name']}",
     f"How {BUSINESS['name']} collects, uses, and protects your information.",
     f"Hi {BUSINESS['name']}! I'd like to talk to someone.", None),
    ("terms-and-conditions", f"Terms &amp; Conditions - {BUSINESS['name']}",
     f"The terms governing your use of the {BUSINESS['name']} website.",
     f"Hi {BUSINESS['name']}! I'd like to talk to someone.", None),
]


def write_business_config():
    """Generates js/business-config.js from business.json so client-side
    scripts can read business details without a runtime fetch - a plain
    <script> tag works identically on file://, a local server, and any
    static host."""
    out_path = os.path.join(SITE_DIR, "js", "business-config.js")
    data = dict(BUSINESS)
    data["googleLink"] = GOOGLE_LINK
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("// Auto-generated from business.json by build.py - do not edit directly.\n")
        f.write("window.FFS_BUSINESS = " + json.dumps(data, indent=2, ensure_ascii=False) + ";\n")
    print("built js/business-config.js")


def main():
    write_business_config()
    for key, title, description, wa_message, active_service in PAGES:
        frag_path = os.path.join(PAGES_DIR, f"{key}.html")
        with open(frag_path, encoding="utf-8") as f:
            body = resolve_tokens(f.read())
            body = fix_internal_paths(body, key)
        html = render_shell(key, title, description, body, wa_message, active_service=active_service)
        out_path = os.path.join(SITE_DIR, OUTPUT_PATHS[key])
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print("built", OUTPUT_PATHS[key])


if __name__ == "__main__":
    main()
