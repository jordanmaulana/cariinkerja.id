from django.db import migrations

from jobs.url_builders import build_crawl_urls


def advance_waiting_admin(apps, schema_editor):
    """Free crawl on registration is disabled, so the transient waiting_admin
    ("ngumpulin loker") state no longer resolves on its own. Unstick any
    preference already sitting there: fill crawl_urls if empty and make it
    payable (waiting_payment)."""
    Preference = apps.get_model("profiles", "Preference")
    stuck = Preference.objects.filter(status="waiting_admin").exclude(title="")
    for pref in stuck.iterator():
        if not pref.crawl_urls:
            pref.crawl_urls = build_crawl_urls(
                pref.title, pref.job_type, pref.remote_option
            )
        pref.status = "waiting_payment"
        pref.save(update_fields=["crawl_urls", "status", "updated_on"])


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0017_remove_glints_crawl_urls"),
    ]

    operations = [
        migrations.RunPython(advance_waiting_admin, migrations.RunPython.noop),
    ]
