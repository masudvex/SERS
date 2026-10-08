from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return ["core:home", "core:about", "core:mission_vision", "core:programs",
                "core:gallery", "core:contact", "core:donate", "accounts:register", "accounts:login"]

    def location(self, item):
        return reverse(item)
