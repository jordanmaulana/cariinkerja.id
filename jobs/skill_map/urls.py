from django.urls import path

from jobs.skill_map_views import skill_map_detail, skill_map_index, skill_map_sitemap

urlpatterns = [
    path("", skill_map_index, name="skill_map_index"),
    path("sitemap.xml", skill_map_sitemap, name="skill_map_sitemap"),
    path("<slug:slug>/", skill_map_detail, name="skill_map_detail"),
]
