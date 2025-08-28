import csv
import datetime

from django.contrib import admin
from django.http import HttpResponse, HttpResponseForbidden
from django.urls import re_path

from .models import Feedback, NoElectionFeedback


class FeedbackAdmin(admin.ModelAdmin):
    change_list_template = "feedback/admin/change_list.html"

    list_filter = ("found_useful", "vote")
    list_display = (
        "id",
        "found_useful",
        "vote",
        "comments",
        "flagged_as_spam",
        "created",
    )
    readonly_fields = [f.name for f in Feedback._meta.get_fields()]
    ordering = ("-created", "id")

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            re_path(
                "export_all/",
                self.export_all_feedback,
                name="feedback_export_all",
            ),
            re_path(
                "export_comments/",
                self.export_feedback_with_comments,
                name="feedback_export_comments",
            ),
        ]
        return my_urls + urls

    def export_all_feedback(self, request):
        if not request.user.is_superuser:
            return HttpResponseForbidden("Access Denied")
        return self.export(Feedback.objects.all().order_by("-created", "id"))

    def export_feedback_with_comments(self, request):
        if not request.user.is_superuser:
            return HttpResponseForbidden("Access Denied")
        return self.export(
            Feedback.objects.all()
            .exclude(comments="")
            .order_by(
                "found_useful",
                "vote",
                "sources",
                "flagged_as_spam",
                "-created",
                "id",
            )
        )

    def export(self, qs):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            'attachment; filename="feedback-%s.csv"'
            % (datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S"))
        )
        fields = [
            "id",
            "created",
            "flagged_as_spam",
            "comments",
            "found_useful",
            "vote",
            "sources",
            "source_url",
        ]
        writer = csv.writer(response)
        writer.writerow(fields)
        for row in qs:
            writer.writerow([getattr(row, field) for field in fields])
        return response


class NoElectionFeedbackAdmin(admin.ModelAdmin):
    change_list_template = "feedback/admin/change_list.html"

    list_display = (
        "id",
        "no_election_feedback_text",
        "flagged_as_spam",
        "created",
    )
    readonly_fields = [f.name for f in NoElectionFeedback._meta.get_fields()]
    ordering = ("-created", "id")

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            re_path(
                "no_election_feedback_export_all/",
                self.export_all_feedback,
                name="no_election_feedback_export_all",
            ),
        ]
        return my_urls + urls

    def export_all_feedback(self, request):
        if not request.user.is_superuser:
            return HttpResponseForbidden("Access Denied")
        return self.export(
            NoElectionFeedback.objects.all().order_by("-created", "id")
        )

    def export(self, qs):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            'attachment; filename="feedback-%s.csv"'
            % (datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S"))
        )
        fields = [
            "id",
            "created",
            "flagged_as_spam",
            "no_election_feedback_text",
            "source_url",
        ]
        writer = csv.writer(response)
        writer.writerow(fields)
        for row in qs:
            writer.writerow([getattr(row, field) for field in fields])
        return response


admin.site.register(Feedback, FeedbackAdmin)
admin.site.register(NoElectionFeedback, NoElectionFeedbackAdmin)
