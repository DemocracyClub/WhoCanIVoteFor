import contextlib
import csv

import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from elections.models import PostElection
from news_mentions.models import BallotNewsArticle
from newspaper import Article, ArticleException, Config


class Command(BaseCommand):
    help = "My shiny new management command."

    @transaction.atomic
    def handle(self, *args, **options):
        BallotNewsArticle.objects.all().delete()
        self.ballot_cache = {}
        self.urls = [
            "https://docs.google.com/spreadsheets/d/e/2PACX-1vTGhmOojqQ5eUr0EIwhs577kZrBJOgHB02rivqcdjst7qoNTCuLigtLb4m1JZ8KSbzGYOZfIj1-Tea-/pub?gid=1312231964&single=true&output=csv",
            "https://docs.google.com/spreadsheets/d/e/2PACX-1vTGhmOojqQ5eUr0EIwhs577kZrBJOgHB02rivqcdjst7qoNTCuLigtLb4m1JZ8KSbzGYOZfIj1-Tea-/pub?gid=730408843&single=true&output=csv",
        ]
        for url in self.urls:
            req = requests.get(url)
            csv_data = csv.DictReader(req.text.splitlines())
            for line in csv_data:
                with contextlib.suppress(ArticleException):
                    self.add_article(line)

    def get_ballot(self, ballot_paper_id):
        if ballot_paper_id not in self.ballot_cache:
            self.ballot_cache[ballot_paper_id] = PostElection.objects.get(
                ballot_paper_id=ballot_paper_id
            )
        return self.ballot_cache[ballot_paper_id]

    def add_article(self, line):
        if not line["Link"]:
            return

        if not line["Link"].startswith("http"):
            return

        config = Config()
        config.request_timeout = 3
        print(line["Link"])
        article = Article(line["Link"], config=config)
        article.download()
        article.parse()
        BallotNewsArticle.objects.create(
            ballot=self.get_ballot(line["Ballot Paper ID"]),
            url=article.canonical_link,
            title=article.title,
            publisher=line["Newspaper (not essential)"],
        )
