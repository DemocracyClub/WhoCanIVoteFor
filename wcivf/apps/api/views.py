import abc

from rest_framework import viewsets
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from api import serializers
from core.helpers import clean_postcode

from people.models import Person
from elections.views import mixins
from elections.models import PostElection, InvalidPostcodeError


class PostcodeNotProvided(APIException):
    status_code = 400
    default_detail = "postcode is a required GET parameter"
    default_code = "postcode_required"


class InvalidPostcode(APIException):
    status_code = 400
    default_detail = "Could not find postcode"
    default_code = "postcode_invalid"


class BallotIdsNotProvided(APIException):
    status_code = 400
    default_detail = "ballot_ids is a required GET parameter"
    default_code = "ballot_ids_required"


class PersonViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "head"]
    queryset = Person.objects.all()
    serializer_class = serializers.PersonSerializer


class BaseCandidatesAndElectionsViewSet(
    viewsets.ViewSet, mixins.PostelectionsToPeopleMixin, metaclass=abc.ABCMeta
):
    http_method_names = ["get", "head"]

    @abc.abstractmethod
    def get_ballots(self, request):
        pass

    def list(self, request, *args, **kwargs):
        results = []

        postelections = self.get_ballots(request)
        for postelection in postelections:
            candidates = []
            personposts = self.people_for_ballot(postelection)
            for personpost in personposts:
                candidates.append(
                    serializers.PersonPostSerializer(
                        personpost, context={"request": request}
                    ).data
                )

            election = {
                "ballot_paper_id": postelection.ballot_paper_id,
                "absolute_url": self.request.build_absolute_uri(
                    postelection.get_absolute_url()
                ),
                "election_date": postelection.election.election_date,
                "election_name": postelection.election.nice_election_name,
                "election_id": postelection.election.slug,
                "post": {
                    "post_name": postelection.post.label,
                    "post_slug": postelection.post.ynr_id,
                },
                "cancelled": postelection.cancelled,
                "ballot_locked": postelection.locked,
                "replaced_by": postelection.replaced_by,
                "candidates": candidates,
            }
            if postelection.replaced_by:
                election[
                    "replaced_by"
                ] = postelection.replaced_by.ballot_paper_id
            else:
                election["replaced_by"] = None

            results.append(election)
        return Response(results)


class CandidatesAndElectionsForPostcodeViewSet(
    BaseCandidatesAndElectionsViewSet, mixins.PostcodeToPostsMixin
):
    def get_ballots(self, request):
        postcode = request.GET.get("postcode", None)
        if not postcode:
            raise PostcodeNotProvided()
        postcode = clean_postcode(postcode)
        try:
            return self.postcode_to_ballots(postcode, compact=True)
        except InvalidPostcodeError:
            raise InvalidPostcode()


class CandidatesAndElectionsForBallots(BaseCandidatesAndElectionsViewSet):
    def get_ballots(self, request):
        ballot_ids_str = request.GET.get("ballot_ids", None)
        if not ballot_ids_str:
            raise BallotIdsNotProvided
        if "," in ballot_ids_str:
            ballot_ids_lst = ballot_ids_str.split(",")
            ballot_ids_lst = [b.strip() for b in ballot_ids_lst]
        else:
            ballot_ids_lst = [ballot_ids_str]

        pes = PostElection.objects.filter(ballot_paper_id__in=ballot_ids_lst)
        pes = pes.select_related("post", "election", "election__voting_system")
        pes = pes.order_by(
            "election__election_date", "election__election_weight"
        )
        return pes
