from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import JournalEntryForm
from .models import BlogPost

PUBLIC_STORY_CATEGORIES = {
    BlogPost.CATEGORY_STORY,
    BlogPost.CATEGORY_FAIR_CHANCE,
    BlogPost.CATEGORY_TIPS,
    BlogPost.CATEGORY_UPDATES,
    BlogPost.CATEGORY_REENTRY,
}


@login_required
def journal_home(request):
    entries = BlogPost.objects.filter(
        owner=request.user,
        visibility=BlogPost.VISIBILITY_PRIVATE,
        category=BlogPost.CATEGORY_JOURNAL,
    ).order_by("-created_at")

    selected_entry = None
    editor_mode = None
    selected_pk = request.GET.get("entry")
    new_mode = request.GET.get("mode") == "new"
    if selected_pk:
        selected_entry = entries.filter(pk=selected_pk).first()
        if selected_entry:
            editor_mode = "edit"
    elif new_mode:
        editor_mode = "new"

    if request.method == "POST":
        posted_entry_pk = request.POST.get("entry_id")
        editing_entry = entries.filter(pk=posted_entry_pk).first() if posted_entry_pk else None
        form = JournalEntryForm(request.POST, instance=editing_entry)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.owner = request.user
            entry.visibility = BlogPost.VISIBILITY_PRIVATE
            entry.category = BlogPost.CATEGORY_JOURNAL
            entry.slug = None
            entry.save()
            return redirect(f"{reverse('journal_home')}?entry={entry.pk}")

        selected_entry = editing_entry
        editor_mode = "edit" if editing_entry else "new"
    else:
        form = JournalEntryForm(instance=selected_entry) if selected_entry else JournalEntryForm()

    return render(
        request,
        "blog/journal_home.html",
        {
            "entries": entries,
            "selected_entry": selected_entry,
            "form": form,
            "editor_mode": editor_mode,
        },
    )


@login_required
def journal_create(request):
    return redirect(f"{reverse('journal_home')}?mode=new")


@login_required
def journal_detail(request, pk):
    entry = get_object_or_404(
        BlogPost,
        pk=pk,
        owner=request.user,
        visibility=BlogPost.VISIBILITY_PRIVATE,
        category=BlogPost.CATEGORY_JOURNAL,
    )
    return render(request, "blog/journal_detail.html", {"entry": entry})


@login_required
def journal_edit(request, pk):
    get_object_or_404(
        BlogPost,
        pk=pk,
        owner=request.user,
        visibility=BlogPost.VISIBILITY_PRIVATE,
        category=BlogPost.CATEGORY_JOURNAL,
    )
    return redirect(f"{reverse('journal_home')}?entry={pk}")


@login_required
def journal_delete(request, pk):
    entry = get_object_or_404(
        BlogPost,
        pk=pk,
        owner=request.user,
        visibility=BlogPost.VISIBILITY_PRIVATE,
        category=BlogPost.CATEGORY_JOURNAL,
    )

    if request.method == "POST":
        entry.delete()
        return redirect("journal_home")

    return render(request, "blog/journal_confirm_delete.html", {"entry": entry})


def stories_list(request):
    topic_filter = (request.GET.get("topic") or "").strip()
    sort = (request.GET.get("sort") or "newest").strip()
    query = (request.GET.get("q") or "").strip()

    posts = BlogPost.objects.filter(
        visibility=BlogPost.VISIBILITY_PUBLIC,
        published=True,
        slug__isnull=False,
        category__in=PUBLIC_STORY_CATEGORIES,
    ).exclude(slug="")

    topic_map = {
        "stories": BlogPost.CATEGORY_STORY,
        "fair_chance_hiring": BlogPost.CATEGORY_FAIR_CHANCE,
        "employer_guides": BlogPost.CATEGORY_FAIR_CHANCE,
        "job_seeker_tips": BlogPost.CATEGORY_TIPS,
        "platform_updates": BlogPost.CATEGORY_UPDATES,
        "reentry_organizations": BlogPost.CATEGORY_REENTRY,
    }

    if topic_filter in topic_map:
        posts = posts.filter(category=topic_map[topic_filter])

    if query:
        posts = posts.filter(Q(title__icontains=query) | Q(content__icontains=query))

    if sort == "most_relevant":
        ordered_posts = list(posts.order_by("-featured", "-updated_at", "-created_at"))
    else:
        sort = "newest"
        ordered_posts = list(posts.order_by("-created_at"))

    for post in ordered_posts:
        # Rough read-time estimate at 220 wpm to support public article metadata.
        word_count = len((post.content or "").split())
        post.read_minutes = max(1, (word_count + 219) // 220)

    featured_post = next(
        (
            post
            for post in ordered_posts
            if "why we built reroute" in (post.title or "").strip().lower()
        ),
        None,
    )
    if featured_post is None:
        featured_post = next((post for post in ordered_posts if post.featured), None)
    if featured_post is None and ordered_posts:
        featured_post = ordered_posts[0]

    featured_id = featured_post.pk if featured_post else None
    grid_posts = [post for post in ordered_posts if post.pk != featured_id]

    return render(
        request,
        "blog/stories_list.html",
        {
            "posts": ordered_posts,
            "featured_post": featured_post,
            "grid_posts": grid_posts,
            "stories_count": len(ordered_posts),
            "query": query,
            "topic_filter": topic_filter,
            "sort": sort,
            "topic_options": [
                ("", "All Stories"),
                ("fair_chance_hiring", "Overcoming Barriers"),
                ("stories", "First Job"),
                ("job_seeker_tips", "Interview Win"),
                ("platform_updates", "Mindset Shift"),
                ("reentry_organizations", "Community Support"),
                ("employer_guides", "Career Change"),
            ],
        },
    )


def stories_detail(request, slug):
    post = get_object_or_404(
        BlogPost,
        slug=slug,
        visibility=BlogPost.VISIBILITY_PUBLIC,
        published=True,
    )
    return render(request, "blog/stories_detail.html", {"post": post})


# Legacy endpoints kept for existing links.
def blog_list(request):
    return redirect("journal_home")


def blog_detail(request, slug):
    return redirect("stories_detail", slug=slug)


def blog_category(request, category):
    legacy_map = {
        "legal": BlogPost.CATEGORY_REENTRY,
        "tips": BlogPost.CATEGORY_TIPS,
        "news": BlogPost.CATEGORY_UPDATES,
        "motivation": BlogPost.CATEGORY_STORY,
        "success": BlogPost.CATEGORY_STORY,
        "tech": BlogPost.CATEGORY_STORY,
        "other": BlogPost.CATEGORY_STORY,
    }
    mapped = legacy_map.get(category.lower(), BlogPost.CATEGORY_STORY)
    url = reverse("stories_list")
    return redirect(f"{url}?{urlencode({'category': mapped})}")
