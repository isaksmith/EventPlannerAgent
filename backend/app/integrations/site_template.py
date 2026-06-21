from __future__ import annotations

import re
import shutil
from pathlib import Path
from urllib.parse import quote_plus

from app.memory.schema import EventProfile, EventType

_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "event_site" / "index.html"

# Neutral fallback primary used only when the event has no usable color at all.
_DEFAULT_PRIMARY = "#2563EB"

# Named brand colors → hex, so profiles that store "blue"/"yellow" still theme the site.
_NAMED_COLORS: dict[str, str] = {
    "red": "#DC2626",
    "crimson": "#DC143C",
    "maroon": "#7F1D1D",
    "rose": "#E11D48",
    "pink": "#DB2777",
    "magenta": "#C026D3",
    "fuchsia": "#C026D3",
    "coral": "#FB7185",
    "orange": "#EA580C",
    "amber": "#F59E0B",
    "gold": "#D4AF37",
    "yellow": "#EAB308",
    "lime": "#65A30D",
    "green": "#16A34A",
    "emerald": "#059669",
    "mint": "#10B981",
    "teal": "#0D9488",
    "turquoise": "#14B8A6",
    "cyan": "#0891B2",
    "sky": "#0EA5E9",
    "blue": "#2563EB",
    "navy": "#1E3A8A",
    "indigo": "#4F46E5",
    "violet": "#7C3AED",
    "purple": "#9333EA",
    "lavender": "#A78BFA",
    "brown": "#92400E",
    "tan": "#B45309",
    "black": "#0F172A",
    "charcoal": "#1E293B",
    "slate": "#475569",
    "gray": "#64748B",
    "grey": "#64748B",
    "silver": "#94A3B8",
    "white": "#E2E8F0",
}

_REGISTER_CTA: dict[EventType, str] = {
    EventType.HACKATHON: "Register your team",
    EventType.CONFERENCE: "Get your ticket",
    EventType.SUMMIT: "Reserve your seat",
    EventType.PARTY: "RSVP",
    EventType.MEETUP: "RSVP",
    EventType.WORKSHOP: "Sign up",
    EventType.FESTIVAL: "Get tickets",
    EventType.GALA: "RSVP",
    EventType.RETREAT: "Apply now",
    EventType.OTHER: "Register",
}

_FIELD_INPUT_TYPES: dict[str, str] = {
    "email": "email",
    "phone": "tel",
    "team": "text",
    "name": "text",
    "company": "text",
}


def template_path() -> Path:
    return _TEMPLATE_PATH


def _enum_label(value: object) -> str:
    raw = value.value if hasattr(value, "value") else str(value)
    return raw.replace("_", " ").title()


def _resolve_color(raw: str | None, fallback: str | None) -> str | None:
    """Resolve a hex (#rrggbb) or named color (e.g. 'blue') to hex."""
    if not raw:
        return fallback
    token = raw.strip().lower()
    if token.startswith("#") and len(token) in (4, 7):
        return raw.strip()
    return _NAMED_COLORS.get(token, fallback)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _mix(base: str, target: str, ratio: float) -> str:
    """Blend ``base`` toward ``target`` by ``ratio`` (0..1) and return hex."""
    br, bg, bb = _hex_to_rgb(base)
    tr, tg, tb = _hex_to_rgb(target)
    r = round(br + (tr - br) * ratio)
    g = round(bg + (tg - bg) * ratio)
    b = round(bb + (tb - bb) * ratio)
    return f"#{r:02X}{g:02X}{b:02X}"


_WHITE = "#FFFFFF"
_INK = "#0B1220"


def _palette(profile: EventProfile) -> dict[str, str]:
    """Derive a cohesive palette from the event's brand colors.

    Works for named colors ("blue") and hex; the full set (background,
    foreground, muted, border, accent) is generated from the primary so the
    site always reflects the specific event theme instead of a fixed default.
    """
    colors = profile.aesthetic.colors or []
    primary = _resolve_color(colors[0] if colors else None, _DEFAULT_PRIMARY) or _DEFAULT_PRIMARY
    secondary = _resolve_color(colors[1] if len(colors) > 1 else None, None)
    if not secondary:
        secondary = _mix(primary, _WHITE, 0.30)
    accent = _resolve_color(colors[2] if len(colors) > 2 else None, None) or secondary
    return {
        "primary": primary,
        "secondary": secondary,
        "accent": accent,
        "background": _mix(primary, _WHITE, 0.94),
        "foreground": _mix(primary, _INK, 0.82),
        "muted": _mix(primary, _INK, 0.45),
        "border": _mix(primary, _WHITE, 0.80),
    }


def _registration_fields_html(profile: EventProfile) -> str:
    fields = profile.ops.registration_fields or ["name", "email", "team"]
    lines = []
    for field in fields:
        label = _enum_label(field)
        input_type = _FIELD_INPUT_TYPES.get(field.lower(), "text")
        autocomplete = {
            "email": "email",
            "name": "name",
            "phone": "tel",
        }.get(field.lower(), "off")
        lines.append(
            f"""      <div class="field-group">
        <label for="reg-{field}" class="field-label">{label} <span class="required" aria-hidden="true">*</span></label>
        <input id="reg-{field}" class="field" type="{input_type}" name="{field}"
          autocomplete="{autocomplete}" required />
      </div>"""
        )
    return "\n".join(lines)


def _sponsor_section_html(profile: EventProfile) -> str:
    if not profile.outreach.sponsor_targets:
        return ""
    items = "".join(f'<li class="sponsor-card">{s}</li>' for s in profile.outreach.sponsor_targets)
    return f"""
  <section class="section sponsors" id="partners" aria-labelledby="partners-heading">
    <div class="section-head">
      <p class="eyebrow">Partners</p>
      <h2 id="partners-heading" class="display-heading">With thanks to</h2>
    </div>
    <ul class="sponsor-grid">{items}</ul>
  </section>"""


def _platform_links_html(profile: EventProfile) -> str:
    links: list[str] = []
    if profile.artifacts.slack_url:
        links.append(
            f'<a href="{profile.artifacts.slack_url}" class="platform-chip">'
            f'<svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
            f'<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>'
            f'<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>'
            f"Join Slack</a>"
        )
    if profile.artifacts.devpost_url:
        links.append(
            f'<a href="{profile.artifacts.devpost_url}" class="platform-chip">'
            f'<svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
            f'<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
            f'<polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>'
            f"Devpost</a>"
        )
    if not links:
        return ""
    return f'<div class="platform-links">{"".join(links)}</div>'


def _event_vibe(profile: EventProfile) -> str:
    theme = getattr(profile.aesthetic, "theme", "") or ""
    if theme and profile.aesthetic.vibe:
        return f"{theme} · {profile.aesthetic.vibe}"
    return theme or profile.aesthetic.vibe or "Join us for an unforgettable experience."


def _event_description(profile: EventProfile) -> str:
    name = profile.event.name or "This event"
    event_type = _enum_label(profile.event.type).lower()
    audience = profile.audience.description or "guests"
    parts = [f"{name} brings together {audience} for a {event_type} like no other."]
    if profile.aesthetic.vibe or profile.aesthetic.theme:
        parts.append(_event_vibe(profile).rstrip("."))
    if profile.event.location and profile.event.location not in {"", "Location TBD"}:
        parts.append(f"Join us in {profile.event.location}.")
    return " ".join(parts)


def _meta_description(profile: EventProfile) -> str:
    name = profile.event.name or "Event"
    dates = profile.event.dates or "Dates TBD"
    location = profile.event.location or "Location TBD"
    return f"{name} — {_enum_label(profile.event.type)} on {dates} in {location}. {_event_vibe(profile)}"[:160]


def _register_cta(profile: EventProfile) -> str:
    return _REGISTER_CTA.get(profile.event.type, "Register")


def _register_heading(profile: EventProfile) -> str:
    cta = _register_cta(profile)
    if cta == "RSVP":
        return "Save your spot"
    if "team" in cta.lower():
        return "Register your team"
    return "Secure your place"


def _register_blurb(profile: EventProfile) -> str:
    attendees = profile.event.expected_attendees
    if attendees:
        return f"We're expecting {attendees}+ guests. Complete the form and we'll confirm by email."
    return "Complete the form below and we'll confirm your registration by email."


def _audience_block_html(profile: EventProfile) -> str:
    if not profile.audience.description:
        return ""
    return f"""
      <div class="info-block">
        <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
          <path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
        </svg>
        <div>
          <p class="info-label">Who's coming</p>
          <p class="info-value">{profile.audience.description}</p>
        </div>
      </div>"""


# Location qualifiers that are not mappable physical places.
_NON_MAPPABLE_TOKENS = {
    "",
    "tbd",
    "location tbd",
    "in person",
    "in-person",
    "virtual",
    "online",
    "remote",
    "hybrid",
}


def _clean_location_query(location: str) -> str:
    """Strip format qualifiers (e.g. 'in person') so the map query is a real place."""
    parts = re.split(r"[·•|]+", location)
    kept = [p.strip() for p in parts if p.strip() and p.strip().lower() not in _NON_MAPPABLE_TOKENS]
    return ", ".join(kept).strip()


def _is_mappable(location: str | None) -> bool:
    if not location:
        return False
    return bool(_clean_location_query(location))


def _map_section_html(profile: EventProfile) -> str:
    location = profile.event.location
    if not _is_mappable(location):
        return ""
    query = _clean_location_query(location or "")
    embed_url = f"https://www.google.com/maps?q={quote_plus(query)}&output=embed&z=17"
    directions_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"
    return f"""
  <section class="section map-section" id="location" aria-labelledby="location-heading">
    <div class="section-head">
      <p class="eyebrow">Getting there</p>
      <h2 id="location-heading" class="display-heading">Find the venue</h2>
    </div>
    <div class="map-layout">
      <div class="map-info">
        <div class="info-block" style="margin-top:0">
          <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
          </svg>
          <div>
            <p class="info-label">Venue</p>
            <p class="info-value">{location}</p>
          </div>
        </div>
        <a class="btn btn-primary" href="{directions_url}" target="_blank" rel="noopener noreferrer">
          <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="3 11 22 2 13 21 11 13 3 11"/>
          </svg>
          Get directions
        </a>
      </div>
      <div class="map-frame">
        <iframe title="Map showing {query}" src="{embed_url}" loading="lazy"
          referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe>
      </div>
    </div>
  </section>"""


def _gallery_section_html(profile: EventProfile) -> str:
    del profile
    items = [
        ("invite_hero", "Event atmosphere", "block-hero"),
        ("invite_cover", "Invite cover", "block-tall"),
        ("invite_motif", "Brand motif", "block-square"),
        ("invite_social", "Social share", "block-square"),
        ("logo", "Brand mark", "block-square"),
    ]
    figures = []
    for stem, label, block_class in items:
        figures.append(
            f"""      <figure class="bento-item {block_class}">
        <img src="assets/{stem}.png" alt="{label}" loading="lazy" width="800" height="600"
          onerror="this.closest('figure').style.display='none'" />
        <figcaption>{label}</figcaption>
      </figure>"""
        )
    return f"""
  <section class="section gallery-section" id="gallery" aria-labelledby="gallery-heading">
    <div class="section-head">
      <p class="eyebrow">Visual identity</p>
      <h2 id="gallery-heading" class="display-heading">The look &amp; feel</h2>
    </div>
    <div class="bento-grid">
{chr(10).join(figures)}
    </div>
  </section>"""


def render_event_site(profile: EventProfile) -> str:
    """Fill the shared Marquee event site template with profile data."""
    if not _TEMPLATE_PATH.is_file():
        raise FileNotFoundError(f"Event site template missing: {_TEMPLATE_PATH}")

    e = profile.event
    palette = _palette(profile)
    replacements = {
        "{{EVENT_TITLE}}": e.name or "Event Registration",
        "{{EVENT_NAME}}": e.name or "Your Event",
        "{{EVENT_TYPE}}": _enum_label(e.type),
        "{{EVENT_FORMAT}}": _enum_label(e.format),
        "{{EVENT_DATES}}": e.dates or "Dates TBD",
        "{{EVENT_LOCATION}}": e.location or "Location TBD",
        "{{EVENT_VIBE}}": _event_vibe(profile),
        "{{EVENT_DESCRIPTION}}": _event_description(profile),
        "{{META_DESCRIPTION}}": _meta_description(profile),
        "{{EXPECTED_ATTENDEES}}": str(e.expected_attendees or "—"),
        "{{COLOR_PRIMARY}}": palette["primary"],
        "{{COLOR_SECONDARY}}": palette["secondary"],
        "{{COLOR_ACCENT}}": palette["accent"],
        "{{COLOR_BACKGROUND}}": palette["background"],
        "{{COLOR_FOREGROUND}}": palette["foreground"],
        "{{COLOR_MUTED}}": palette["muted"],
        "{{COLOR_BORDER}}": palette["border"],
        "{{REGISTER_CTA}}": _register_cta(profile),
        "{{REGISTER_HEADING}}": _register_heading(profile),
        "{{REGISTER_BLURB}}": _register_blurb(profile),
        "{{REGISTRATION_FIELDS}}": _registration_fields_html(profile),
        "{{AUDIENCE_BLOCK}}": _audience_block_html(profile),
        "{{GALLERY_SECTION}}": _gallery_section_html(profile),
        "{{MAP_SECTION}}": _map_section_html(profile),
        "{{SPONSOR_SECTION}}": _sponsor_section_html(profile),
        "{{PLATFORM_LINKS}}": _platform_links_html(profile),
    }

    html = _TEMPLATE_PATH.read_text(encoding="utf-8")
    for key, value in replacements.items():
        html = html.replace(key, value)
    return html


def seed_event_site(build_dir: Path, profile: EventProfile) -> Path:
    """
    Write rendered index.html from the shared template into the build directory.
    Also copies the raw template file for coding agents to reference.
    """
    build_dir.mkdir(parents=True, exist_ok=True)
    index_path = build_dir / "index.html"
    index_path.write_text(render_event_site(profile), encoding="utf-8")

    template_ref = build_dir / "site_template.html"
    shutil.copy2(_TEMPLATE_PATH, template_ref)
    return index_path
