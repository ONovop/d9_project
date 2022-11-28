from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from .models import Post, Category
from .filters import PostFilter
from .forms import PostForm
from django.urls import reverse_lazy
from django.http import Http404
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib.auth.models import Group
from django.core.mail import send_mail, EmailMultiAlternatives
from django.contrib.auth.models import User

class PostList(ListView):
    model = Post
    ordering = '-time_creating'
    template_name = 'news.html'
    context_object_name = 'posts'
    paginate_by = 10

class PostListFiltered(ListView):
    model = Post
    ordering = '-time_creating'
    template_name = 'search.html'
    context_object_name = 'posts'
    paginate_by = 2

    # Переопределяем функцию получения списка товаров
    def get_queryset(self):
        # Получаем обычный запрос
        queryset = super().get_queryset()
        # Используем наш класс фильтрации.
        # self.request.GET содержит объект QueryDict, который мы рассматривали
        # в этом юните ранее.
        # Сохраняем нашу фильтрацию в объекте класса,
        # чтобы потом добавить в контекст и использовать в шаблоне.
        self.filterset = PostFilter(self.request.GET, queryset)
        # Возвращаем из функции отфильтрованный список товаров
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Добавляем в контекст объект фильтрации.
        context['filterset'] = self.filterset
        return context


class PostDetail(DetailView):
    model = Post
    template_name = 'news_d.html'
    context_object_name = 'post'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['subscribes'] = Category.objects.filter(subscribers=self.request.user)
        return context

class NewsCreate(PermissionRequiredMixin, CreateView):
    permission_required = ('news.add_post')
    # Указываем нашу разработанную форму
    form_class = PostForm
    # модель товаров
    model = Post
    # и новый шаблон, в котором используется форма.
    template_name = 'posts_edit.html'

    def form_valid(self, form):
        result = super().form_valid(form)
        self.object.type = Post.news

        html_content = render_to_string('post_created_mail.html', {'post': self.object})

        if Post.objects.filter(id=self.object.id).values('category__subscribers').exists():
            subs = Post.objects.filter(id=self.object.id).values('category__subscribers')
        else:
            subs = []
        emails = []
        if subs != []:
            for i in User.objects.all():
                if i in subs:
                    emails.append(i.email)
        msg = EmailMultiAlternatives(
            subject=f'Новый материал{self.object.title}',
            body=self.object.text,
            from_email='da3c709e-298c-4bc6-98b5-30bfc7892069@debugmail.io',
            to=emails,
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        return result

class ArticleCreate(PermissionRequiredMixin, CreateView):
    permission_required = ('news.add_post')
    # Указываем нашу разработанную форму
    form_class = PostForm
    # модель товаров
    model = Post
    # и новый шаблон, в котором используется форма.
    template_name = 'posts_edit.html'

    def form_valid(self, form):
        post = form.save(commit=False)
        post.type = Post.article
        return super().form_valid(form)

class NewsUpdate(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = ('news.change_post')
    form_class = PostForm
    model = Post
    def get_object(self, queryset=None):
        initial = super(NewsUpdate, self).get_object(queryset)
        if initial.type != Post.news:
            raise Http404('Нет такой новости!')
        return initial
    template_name = 'posts_edit.html'


# Добавляем представление для изменения
class ArticleUpdate(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = ('news.change_post')
    form_class = PostForm
    model = Post
    def get_object(self, queryset=None):
        initial = super(ArticleUpdate, self).get_object(queryset)
        if initial.type != Post.article:
            raise Http404('Нет такой новости!')
        return initial
    template_name = 'posts_edit.html'


class NewsDelete(DeleteView):
    model = Post
    def get_object(self, queryset=None):
        initial = super(NewsDelete, self).get_object(queryset)
        if initial.type != Post.news:
            raise Http404('Нет такой новости!')
        return initial
    template_name = 'posts_delete.html'
    success_url = reverse_lazy('List')

class ArticleDelete(DeleteView):
    model = Post
    def get_object(self, queryset=None):
        initial = super(ArticleDelete, self).get_object(queryset)
        if initial.type != Post.article:
            raise Http404('Нет такой новости!')
        return initial
    template_name = 'posts_delete.html'
    success_url = reverse_lazy('List')

class IndexView(LoginRequiredMixin, TemplateView):
    template_name = 'protect/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_not_author'] = not self.request.user.groups.filter(name='authors').exists()
        return context

@login_required
def upgrade_me(request):
    user = request.user
    authors_group = Group.objects.get(name='authors')
    if not request.user.groups.filter(name='authors').exists():
        authors_group.user_set.add(user)
    return redirect('/user')

def subscribe_me(request, **kwargs):
    user = request.user
    key = kwargs.get('pk')
    cat = Category.objects.get(id=key)
    if not Category.objects.filter(id=key, subscribers=user).exists():
        cat.subscribers.add(user)
    return redirect('List')
