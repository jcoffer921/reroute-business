from reroute_business.job_list.models import ZipCentroid
from reroute_business.resources.models import ResourceOrganization

print('zip19115', ZipCentroid.objects.filter(zip_code='19115').exists())
print('zip19104', ZipCentroid.objects.filter(zip_code='19104').exists())
print('resources_total', ResourceOrganization.objects.count())
print('resources_with_geo', ResourceOrganization.objects.filter(geo_point__isnull=False).count())
