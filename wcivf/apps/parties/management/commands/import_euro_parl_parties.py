from django.core.management.base import BaseCommand
from django.db import transaction

import csv

from parties.models import Party, LocalParty, Manifesto
from elections.models import PostElection, Election


csv_data = """election id,party name,party id,EP2019 manifesto PDF,EP2019 manifesto/info webpage,Party homepage,twitter,facebook
europarl.2019-05-23,English Democrats,17,,https://www.englishdemocrats.party/the_eu_election_call_to_arms,https://www.englishdemocrats.party/,https://twitter.com/EnglishDemocrat,
europarl.2019-05-23,Conservative and Unionist Party (GB),52,,,https://conservatives.com,https://twitter.com/Conservatives,https://www.facebook.com/conservatives
europarl.2019-05-23,Labour,53,http://labour.org.uk/wp-content/uploads/2019/05/Transforming-Britain-and-Europe-for-the-many-not-the-few.pdf,https://labour.org.uk/manifesto/transforming-britain-and-europe/,https://labour.org.uk/,https://twitter.com/UKLabour,https://www.facebook.com/labourparty
europarl.2019-05-23,Green Party of England and Wales,63,https://www.greenparty.org.uk/assets/images/national-site/eu-2019/eu-manifesto-online-19-05-07.pdf,,https://www.greenparty.org.uk,https://twitter.com/TheGreenParty,https://www.facebook.com/thegreenparty
europarl.2019-05-23,Plaid Cymru,77,https://d3n8a8pro7vhmx.cloudfront.net/plaid2016/pages/7962/attachments/original/1557734498/Plaid_Cymru_-_European_Manifesto_2019.pdf,https://www.partyof.wales/plaid_europe,https://www.partyof.wales/,https://twitter.com/plaid_cymru,https://www.facebook.com/PlaidCymruWales/
europarl.2019-05-23,UK Independence Party (UKIP) (GB),85,https://www.ukip.org/pdf/EUManifesto2019-3.pdf,,https://www.ukip.org/,https://twitter.com/UKIP,https://www.facebook.com/UKIP/
europarl.2019-05-23,Liberal Democrats,90,https://view.pagetiger.com/brexit/2019-eu-manifesto/PDF.pdf,https://www.libdems.org.uk/manifesto,https://www.libdems.org.uk,https://twitter.com/libdems,https://www.facebook.com/libdems
europarl.2019-05-23,Scottish National Party,102,,https://www.snp.org/campaigns/eu-election-2019/,https://www.snp.org/,https://twitter.com/theSNP,https://www.facebook.com/theSNP/
europarl.2019-05-23,Socialist Party of Great Britain,110,,http://socialismoryourmoneyback.blogspot.com/2019/05/brexit-statement.html,https://www.worldsocialism.org/spgb/,https://twitter.com/officialSPGB,https://www.facebook.com/socialistpartyofgreatbritain/
europarl.2019-05-23,Scottish Green Party,130,https://greens.scot/sites/default/files/Scottish%20Greens%20EU%20Manifesto%202019%20WebV.pdf,,https://greens.scot/,https://twitter.com/scotgp,https://www.facebook.com/ScottishGreens
europarl.2019-05-23,Animal Welfare Party,616,https://www.animalwelfareparty.org/wordpress/wp-content/uploads/2019/04/Manifesto-Animal-Politics-EU-2019.pdf,https://www.animalwelfareparty.org/current-elections/2019-eu-parliament-elections/,https://www.animalwelfareparty.org/,https://twitter.com/AnimalsCount,https://www.facebook.com/Animal.Welfare.Party/
europarl.2019-05-23,Independent Network,1951,,http://www.lincolnshireindependents.org.uk/independent-network-east-midlands,http://www.lincolnshireindependents.org.uk/,https://twitter.com/LincIndependent,https://www.facebook.com/LincolnshireIndependents/
europarl.2019-05-23,Yorkshire Party,2055,,https://www.yorkshireparty.org.uk/european-elections-2019/,https://www.yorkshireparty.org.uk/,https://twitter.com/Yorkshire_Party,https://www.facebook.com/voteyorkshire
europarl.2019-05-23,Women's Equality Party,2755,https://d3n8a8pro7vhmx.cloudfront.net/womensequality/pages/6597/attachments/original/1557333509/EU_Manifesto_compressed.pdf,https://www.womensequality.org.uk/manifesto_eu,https://www.womensequality.org.uk,https://twitter.com/WEP_UK,
europarl.2019-05-23,The Brexit Party,7931,,,https://thebrexitparty.org/,https://twitter.com/brexitparty_uk,https://www.facebook.com/brexitpartyuk/
europarl.2019-05-23,UK European Union Party (UKEUP),9060,https://static1.squarespace.com/static/5c8d132bda50d376a62715e4/t/5ccc9c92fa0d605d2527330f/1556913310609/UKEUP_Manifesto_2019_fin.pdf,,https://theukeuparty.org/,https://twitter.com/theukeuparty,
europarl.2019-05-23,Change UK,9077,https://voteforchange.uk/wp-content/uploads/2019/05/Change-UK-Charter-for-Remain.pdf,,https://voteforchange.uk/,https://twitter.com/ForChange_Now,https://www.facebook.com/ForChangeNow/
europarl.2019-05-23,UK Independence Party (UKIP) (NI),84,,,https://ukipnorthernireland.uk/,https://twitter.com/ukip_ni,https://www.facebook.com/UkipNorthernIreland/
europarl.2019-05-23,Ulster Unionist Party,83,,https://uup.org/news/6070/No-second-Brexit-referendum-Kennedy#.XN6ZP8hKhPY,http://www.uup.org,https://twitter.com/uuponline,
europarl.2019-05-23,Alliance - Alliance Party of Northern Ireland,103,https://d3n8a8pro7vhmx.cloudfront.net/allianceparty/pages/3559/attachments/original/1557772505/ManifestoEPNIonline.pdf,https://www.allianceparty.org/brexit,http://www.allianceparty.org,https://twitter.com/allianceparty,https://www.facebook.com/alliancepartyni/
europarl.2019-05-23,Democratic Unionist Party - D.U.P.,70,,http://www.mydup.com/news/article/dodds-to-defend-the-union-and-deliver-brexit-vote-dodds-1,http://www.mydup.com,https://twitter.com/duponline,https://www.facebook.com/democraticunionistparty
europarl.2019-05-23,SDLP (Social Democratic & Labour Party),55,,http://www.sdlp.ie/news/2019/eastwood-launches-bid-to-take-back-john-humes-european-seat/,http://www.sdlp.ie,https://twitter.com/SDLPlive,https://www.facebook.com/SocialDemocraticLabourParty/
europarl.2019-05-23,Sinn Féin,39,https://www.sinnfein.ie/files/2019/EU_Manifesto2.pdf,https://www.sinnfein.ie/brexit,https://www.sinnfein.ie,https://twitter.com/sinnfeinireland,https://www.facebook.com/sinnfein
europarl.2019-05-23,Conservative and Unionist Party (NI),51,,,https://www.niconservatives.com/,https://twitter.com/niconservative,https://www.facebook.com/niconservatives/
europarl.2019-05-23,Green Party (NI),305,,http://www.greenpartyni.org/peoples-vote-the-only-possible-escape-from-brexit-blind-alley/,http://www.greenpartyni.org/,https://twitter.com/GreenPartyNI,https://www.facebook.com/GreenParty
europarl.2019-05-23,Traditional Unionist Voice - TUV,680,,http://tuv.org.uk/euro-election-confirmation-tell-them-to-get-on-with-getting-out/,http://tuv.org.uk/,,
"""


class Command(BaseCommand):
    def get_party_list_from_party_id(self, party_id):
        party_id = "party:{}".format(party_id)

        PARTIES = [["party:53", "party:84", "joint-party:53-119"]]

        for party_list in PARTIES:
            if party_id in party_list:
                return party_list
        return [party_id]

    @transaction.atomic
    def handle(self, **options):
        # Delete all data for the eu elections
        # as rows in the source might have been deleted
        self.euro_parl_election = Election.objects.get(
            slug="europarl.2019-05-23"
        )

        LocalParty.objects.filter(
            post_election__election=self.euro_parl_election
        ).delete()

        reader = csv.DictReader(csv_data.splitlines())
        for row in reader:
            party_id = row["party id"].strip()
            # Try to get a post election
            try:
                party_list = self.get_party_list_from_party_id(party_id)
                parties = Party.objects.filter(party_id__in=party_list)
            except Party.DoesNotExist:
                print("Parent party not found with ID %s" % party_id)
                continue

            post_elections = PostElection.objects.filter(
                election__slug=row["election id"]
            ).exclude(localparty__parent__in=parties)
            for party in parties:
                self.add_local_party(row, party, post_elections)
                self.add_manifesto(row, party)

    def add_local_party(self, row, party, post_elections):
        twitter = row["twitter"].replace("https://twitter.com/", "")
        twitter = twitter.split("/")[0]
        twitter = twitter.split("?")[0]
        for post_election in post_elections:
            LocalParty.objects.update_or_create(
                parent=party,
                post_election=post_election,
                defaults={
                    "name": row["party name"],
                    "twitter": twitter,
                    "facebook_page": row["facebook"],
                    "homepage": row["Party homepage"],
                },
            )

    def add_manifesto(self, row, party):

        manifesto_web = row["EP2019 manifesto/info webpage"].strip()
        manifesto_pdf = row["EP2019 manifesto PDF"].strip()
        if any([manifesto_web, manifesto_pdf]):
            manifesto_obj, created = Manifesto.objects.update_or_create(
                election=self.euro_parl_election,
                party=party,
                defaults={
                    "web_url": manifesto_web,
                    "pdf_url": manifesto_pdf,
                    "country": "EU",
                    "language": "English",
                },
            )
            manifesto_obj.save()
