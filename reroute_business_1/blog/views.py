from django.shortcuts import render
from django.shortcuts import render, get_object_or_404
from .models import BlogPost

def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, published=True)
    return render(request, 'blog/detail.html', {'post': post})

def blog_category(request, category):
    posts = BlogPost.objects.filter(
        published=True,
        category__iexact=category  # You may need to add category as a model field
    ).order_by('-created_at')

    return render(request, 'blog/category.html', {
        'posts': posts,
        'category': category.capitalize(),
    })

def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, published=True)
    return render(request, 'blog/detail.html', {'post': post})

def blog_list(request):
    query = request.GET.get("q", "")
    category_filter = request.GET.get("category", "")

    posts = BlogPost.objects.filter(published=True)

    if query:
        posts = posts.filter(title__icontains=query)

    if category_filter:
        posts = posts.filter(category__iexact=category_filter)

    categories = BlogPost.objects.values_list('category', flat=True).distinct()

    return render(request, 'blog/blog_list.html', {
        'posts': posts.order_by('-created_at'),
        'query': query,
        'category_filter': category_filter,
        'categories': categories
    })
