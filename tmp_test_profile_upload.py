from django.contrib.auth.models import User
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from reroute_business.profiles.models import UserProfile

u, created = User.objects.get_or_create(username='tmp_profile_upload_user')
if created:
    u.set_password('Pass12345!')
    u.email='tmp@example.com'
    u.save()
else:
    u.set_password('Pass12345!')
    u.save()

client = Client()
print('login', client.login(username='tmp_profile_upload_user', password='Pass12345!'))

# 1x1 gif
img_bytes = (
    b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,'
    b'\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
)
file = SimpleUploadedFile('avatar.gif', img_bytes, content_type='image/gif')

payload = {
    'profile_form': '1',
    'headline': 'Test Headline',
    'location': 'Test City',
    'status': '',
    'about': 'About me',
    'core_skills_json': '[]',
    'soft_skills_json': '[]',
    'experiences_json': '[]',
    'certifications_json': '[]',
    'save_profile': '1',
}
resp = client.post('/settings/?panel=profile', data={**payload, 'profile_photo': file})
print('status', resp.status_code, 'redirect', getattr(resp, 'url', None))

p = UserProfile.objects.get(user=u)
print('picture?', bool(p.profile_picture), 'name', p.profile_picture.name)
