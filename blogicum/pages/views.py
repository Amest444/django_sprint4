from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from blog.models import Post
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Count

def profile(request, username):
    user = get_object_or_404(User, username=username)
    if request.user == user:
        posts = Post.objects.filter(author=user).annotate(comment_count=Count('comments')).order_by('-pub_date')
    else:
        posts = Post.objects.filter(
            author=user,
            is_published=True,
            pub_date__lte=timezone.now()
        ).annotate(
            comment_count=Count('comments')
        ).order_by('-pub_date')
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'blog/profile.html', {'profile': user, 'page_obj': page_obj})

def about(request):
    return render(request, 'pages/about.html')

def rules(request):
    return render(request, 'pages/rules.html')

def page_not_found(request, exception):
    return render(request, 'pages/404.html', status=404)

def csrf_failure(request, reason=''):
    return render(request, 'pages/403csrf.html', status=403)

def server_error(request, reason=''):
    return render(request, 'pages/500.html', status=500)


