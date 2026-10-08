from django.urls import reverse

from .models import MenuItem, SiteSettings, SocialLink


def site(request):
    items = list(MenuItem.objects.filter(is_active=True))
    authed = request.user.is_authenticated
    menus = {m.value: [] for m in MenuItem.Menu}
    for it in items:
        if it.visibility == MenuItem.Visibility.ANON and authed:
            continue
        if it.visibility == MenuItem.Visibility.AUTH and not authed:
            continue
        it.is_current = it.menu == MenuItem.Menu.MAIN and it.url.rstrip("/") == request.path.rstrip("/")
        menus[it.menu].append(it)
    cfg = SiteSettings.load()
    return {
        "site": cfg,
        "map_config": {
            "mapUrl": reverse("core:map_data"),
            "key": cfg.google_maps_api_key.strip(),
            "mapId": cfg.google_map_id.strip() or "DEMO_MAP_ID",
            "lat": cfg.map_center_lat, "lng": cfg.map_center_lng, "zoom": cfg.map_zoom,
            "query": cfg.map_fallback_query,
        },
        "menus": menus,
        "social_links": SocialLink.objects.filter(is_active=True),
    }
