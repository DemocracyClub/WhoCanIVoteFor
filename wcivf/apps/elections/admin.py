from django.contrib import admin

from .models import Election, Post, PostElection, VotingSystem


class ElectionAdmin(admin.ModelAdmin):
    list_filter = ("election_type", "voting_system")
    list_display = ("name", "slug", "election_date")
    search_fields = ("slug", "name")
    date_hierarchy = "election_date"


class PostAdmin(admin.ModelAdmin):
    list_display = ("area_name", "role")
    list_filter = ("organization", "role")


class PostElectionAdmin(admin.ModelAdmin):
    search_fields = ("ballot_paper_id",)


admin.site.register(Election, ElectionAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(VotingSystem)
admin.site.register(PostElection, PostElectionAdmin)
