from scrapy.utils.project import get_project_settings
s = get_project_settings()
print("DOWNLOAD_HANDLERS:", s.get("DOWNLOAD_HANDLERS"))
print("TWISTED_REACTOR:", s.get("TWISTED_REACTOR"))
print("Settings module:", s.get("SETTINGS_MODULE"))
