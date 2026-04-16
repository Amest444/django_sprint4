from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from .models import Post, Category, Comment
from .forms import PostForm, CommentForm
from django import forms
from django.db.models import Count
from django.http import Http404


def index(request):
    template_name = "blog/index.html"
    post_list = (
        Post.objects.select_related("category", "location", "author")
        .filter(
            is_published=True, pub_date__lte=timezone.now(), category__is_published=True
        )
        .annotate(comment_count=Count("comments"))
        .order_by("-pub_date")
    )

    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
    }
    return render(request, template_name, context)


def post_detail(request, id):
    post = get_object_or_404(
        Post.objects.select_related("category", "location", "author"), id=id
    )
    if not (
        post.is_published
        and post.pub_date <= timezone.now()
        and post.category.is_published
    ):
        if request.user != post.author:
            raise Http404
    comments = post.comments.order_by("created_at")
    form = CommentForm()
    return render(
        request, "blog/detail.html", {"post": post,
                                      "comments": comments, "form": form}
    )


def category_posts(request, category_slug):
    template_name = "blog/category.html"
    category = get_object_or_404(
        Category, slug=category_slug, is_published=True)
    post_list = (
        Post.objects.select_related("category", "location", "author")
        .filter(category=category, is_published=True, pub_date__lte=timezone.now())
        .annotate(comment_count=Count("comments"))
        .order_by("-pub_date")
    )

    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "category": category,
        "page_obj": page_obj,
    }
    return render(request, template_name, context)


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = "blog/create.html"

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "blog:profile", kwargs={"username": self.request.user.username}
        )


class PostUpdateView(UpdateView):
    model = Post
    form_class = PostForm
    template_name = "blog/create.html"
    pk_url_kwarg = "post_id"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not request.user.is_authenticated or request.user != self.object.author:
            return redirect("blog:post_detail", id=self.object.id)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("blog:post_detail", kwargs={"id": self.object.id})


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    template_name = "blog/delete.html"
    pk_url_kwarg = "post_id"
    success_url = reverse_lazy("blog:index")

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
    return redirect("blog:post_detail", id=post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, post_id=post_id)
    if comment.author != request.user:
        return redirect("blog:post_detail", id=post_id)
    if request.method == "POST":
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect("blog:post_detail", id=post_id)
    else:
        form = CommentForm(instance=comment)
    return render(request, "blog/comment.html", {"form": form, "comment": comment})


class CommentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Comment
    template_name = "blog/delete.html"
    pk_url_kwarg = "comment_id"

    def test_func(self):
        comment = self.get_object()
        return self.request.user == comment.author

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        return redirect("blog:post_detail", id=self.get_object().post.id)

    def get_success_url(self):
        return reverse_lazy("blog:post_detail", kwargs={"id": self.object.post.id})


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]


@login_required
def edit_profile(request):
    user = request.user
    if request.method == "POST":
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect("blog:profile", username=user.username)
    else:
        form = UserEditForm(instance=user)
    return render(request, "blog/user.html", {"form": form, "profile_user": user})
