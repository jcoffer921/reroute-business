from reroute_business.blog.models import BlogPost

post = BlogPost.objects.filter(title__iexact='Why We Built ReRoute', visibility=BlogPost.VISIBILITY_PUBLIC).first()
if post is None:
    post = BlogPost(
        title='Why We Built ReRoute',
        content=(
            'ReRoute was built to expand access to fair-chance employment and remove barriers that keep qualified people out of the workforce. '
            'We saw employers who wanted to hire differently and talented candidates who needed a pathway that respected their growth, not just their history.\n\n'
            'Our mission is to connect employers, job seekers, and support organizations through practical tools, transparent guidance, and real outcomes. '
            'This platform exists to help opportunity move faster, with dignity and accountability for everyone involved.'
        ),
        visibility=BlogPost.VISIBILITY_PUBLIC,
        category=BlogPost.CATEGORY_STORY,
        published=True,
        featured=True,
    )
    post.save()
    print('created', post.id, post.slug)
else:
    post.featured = True
    post.published = True
    post.visibility = BlogPost.VISIBILITY_PUBLIC
    post.category = BlogPost.CATEGORY_STORY
    if not post.content.strip():
        post.content = 'Why we built ReRoute.'
    post.save()
    print('updated', post.id, post.slug)
