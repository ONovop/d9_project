import logging

from django.conf import settings

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.core.management.base import BaseCommand
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from ...models import Post, Category
from datetime import timedelta, datetime

logger = logging.getLogger(__name__)


# наша задача по выводу текста на экран
def my_job():
    i = 1
    while True:
        #print('id category', i)
        if not Category.objects.filter(id=i).exists():
            #print(f"Category {i} doesn't exist, sended!")
            break
        subs = Category.objects.filter(id=i).values('subscribers')
        #print('subscribers', subs)
        if subs[0]['subscribers']:
            limit = datetime.now() - timedelta(days=7)
            emails = []
            for sub in subs:
                #print(sub)
                #print(sub['subscribers'])
                reciever = User.objects.get(id=sub['subscribers'])
                emails.append(reciever.email)
            if Post.objects.filter(category__id=i, time_creating__gt=limit).exists():
                news = Post.objects.filter(category__id=i, time_creating__gt=limit)
                html_content = render_to_string('weekly_mail.html', {'posts': news})
                msg = EmailMultiAlternatives(
                    subject=f'Новый материал за неделю в подписке',
                    body='Материалы',
                    from_email='da3c709e-298c-4bc6-98b5-30bfc7892069@debugmail.io',
                    to=emails,
                    )
                msg.attach_alternative(html_content, "text/html")
                msg.send()
        #else:
            #print('skip, no subscribers')
        i += 1


# функция, которая будет удалять неактуальные задачи
def delete_old_job_executions(max_age=604800):
    """This job deletes all apscheduler job executions older than `max_age` from the database."""
    DjangoJobExecution.objects.delete_old_job_executions(max_age)


class Command(BaseCommand):
    help = "Runs apscheduler."

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        # добавляем работу нашему задачнику
        scheduler.add_job(
            my_job,
            trigger=CronTrigger(
                day_of_week="mon", hour="00", minute="00"
            ),
            # То же, что и интервал, но задача тригера таким образом более понятна django
            id="my_job",  # уникальный айди
            max_instances=1,
            replace_existing=True,
        )
        logger.info("Added job 'my_job'.")

        scheduler.add_job(
            delete_old_job_executions,
            trigger=CronTrigger(
                day_of_week="mon", hour="00", minute="00"
            ),
            # Каждую неделю будут удаляться старые задачи, которые либо не удалось выполнить, либо уже выполнять не надо.
            id="delete_old_job_executions",
            max_instances=1,
            replace_existing=True,
        )
        logger.info(
            "Added weekly job: 'delete_old_job_executions'."
        )

        try:
            logger.info("Starting scheduler...")
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            scheduler.shutdown()
            logger.info("Scheduler shut down successfully!")