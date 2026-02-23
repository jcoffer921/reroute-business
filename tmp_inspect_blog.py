from reroute_business.blog.models import BlogPost
qs = BlogPost.objects.filter(visibility='public', published=True).order_by('-created_at')
print('count', qs.count())
for p in qs[:30]:
    print(p.id, p.title, p.category, p.slug, p.featured)
