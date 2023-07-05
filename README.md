[![CircleCI](https://circleci.com/gh/DemocracyClub/WhoCanIVoteFor.svg?style=svg)](https://circleci.com/gh/DemocracyClub/WhoCanIVoteFor) [![Coverage Status](https://coveralls.io/repos/github/DemocracyClub/WhoCanIVoteFor/badge.svg?branch=master)](https://coveralls.io/github/DemocracyClub/WhoCanIVoteFor?branch=master) ![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)

# WhoCanIVoteFor

This project is designed for people who don't know loads about the ins and outs of elections to use to find out everything about upcoming elections, including candidates, polling stations, electon dates, etc.

It has the following features:

* "Given a postcode, when is my next election?"
* "Who are the candidates per election?"
* "Where is my polling staion?"
* Enter email address and postcode to get alerted about future elections in your area

It might be good to look at [this issue](https://github.com/mysociety/yournextrepresentative/issues/584) for a little more info.

The reason for building this site:

1. We have some other tools that are designed for gathering data, for example [Democracy Club Candidates](https://candidates.democracyclub.org.uk/) and [UK Polling Statons](https://wheredoivote.co.uk/).  There is value in keeping these sites on their own, as the candidates one in particular has a very different audience to this site.
2. We want to allow 3rd parties to write sites that we can include in this one via data dumps.  3rd parties shouldn't have to use our codebase in order to make interesting things.  We saw this a low during the UK General Election.
3. This site is very read heavy, so we can think about optimizing for that, rather than both read and write heavy operations.  In 2015 this site was [a Jekyll install](https://github.com/DemocracyClub/YourNextMP-Read).
4. We want to be able to spin up new ideas quickly in this codebase, and not pollute the [YourNextRepresentative](https://github.com/DemocracyClub/YourNextRepresentative) code too much (it has an international focus)


![photo 04-03-2016 17 18 46](https://cloud.githubusercontent.com/assets/739624/13565711/bc9bf7ea-e449-11e5-822b-8322c6a63872.jpg)


## Results Recorder App

This app will be used by people both at counts and after the count to record results from each election.

There are two types of 'result' that we want to capture:

1. 'Control' of councils.  This is the dominant party or 'No Overall Control' if no party has more than 50% of the council seats.  This is a fairly simple data model (`AuthorityControlSet`), looking something like `controlling_party(NULL=True)`, `authority`.  Stretch goal would be to pre-load the control model with the previous year's control (data to be provided), to allow 'swing' to be calculated ("HOLD", "LAB GAIN", etc).
2. Votes Cast per person.  This is slightly more complex than the above, with roughly the following model:

![Results App](results_app.png)

In addition to this, we will ask them to record the number of spoilt votes, and the turn out if it's reported.

For both of the above, a non-authenticated user can navigate to an election and area.  There they can enter 'control' and 'votes cast' on two different forms.

Both workflow should consoder the following:

* We want to record more than one result of it's class ('control' and 'votes cast') per election.  There are a number of reasons for this:

  1. The result may have been recorded incorrectly, either because of a mistake or out of malice.
  2. The result announced at the count might not be the actual final result – apparently this happens alarmingly often.
  3. More than one person might report the results.
  4. Someone might want to double check the results as published on the council's web site at a later date (see #2).

  There should be a nice way to see `ResultsSet` and `AuthorityControlSet` objects that have differing results recorded, and we should provide some shortcuts, for example to `ResultsSet` objects where the sum of the `CandidateResult` `votes_cast` field isn't the same.

* Sourcing and timing is important for us, so each model should extend from an abstract base class that has `created` (datetime), `modified` (datetime) and `source` (TextField).  Forms should ask for a source (we need to decide if this is required) when recording either type of result.

* There are different voting systems – for example [Single Transferable Vote](https://en.m.wikipedia.org/wiki/Single_transferable_vote), as used in Northern Ireland.  This could be out of scope for this initial phase of work – more research time is needed to see how complex this will be to model.

## Dummy ballots and profiles

There is a dummy ballot with dummy candidate profiles, that was produced for
[The Children's Commissioner for Wales](https://www.childcomwales.org.uk).
These are defined in the [elections URL file](wcivf/apps/elections/urls.py)
(at time of writing this is "TE1 1ST").

From the resulting dummy ballot page, you can click the candidates to see their
dummy profiles. All links on the page are intended to be "dead" links.

## Getting started

See [INSTALL.md](INSTALL.md) for setup instructions.

# Translations

This application can be translated in to different languages.

This is done using [Django's standard translation system](https://docs.djangoproject.com/en/3.2/topics/i18n/translation/).

## TranslatedTemplateView

There are some templates in the system that are mainly text and that rarely
change. For example, the election explainers.

Rather than wrapping this complex document in `trans` tags, we can translate
the entire template as a single file.

To do this, we can use `TranslatedTemplateView`. This extends Django's
`TemplateView` but attempts to load a template relating to the current
language, falling back to the one specified in `template_name`.

For example if the curent language is `cy` (Welsh):

```python
TranslatedTemplateView.as_view(template_name="foo.html")
```

Will try to render `foo_cy.html` first and if that doesn't exist it will
render `foo.html`

## Pre-Election Tasks

Update slack feedback schedule to post more frequently during election 
season (perhaps daily)and less frequently during non-election season 
(perhaps weekly). Both the hours and the cron schedule in needs to be 
edited in `sam-template.yaml` for this change to take effect.

# New WCIVF Google Sheets imports (Hustings, local parties)

Peter will have set up some Google sheets in a known format. The CSV version of these sheets are imported in to WCIVF from time to time.

Each election, we create a new set of sheets. These need to be added to the import jobs.

Get the Sheet CSV URL (file -> share -> public to the web -> select sheet / csv > publish > copy URL)
For local parties, edit https://github.com/DemocracyClub/WhoCanIVoteFor/blob/master/wcivf/apps/parties/management/commands/import_local_parties.py#L23-L34
For hustings edit https://github.com/DemocracyClub/WhoCanIVoteFor/blob/master/wcivf/apps/hustings/management/commands/import_hustings.py#L60

Commit, PR, merge, deploy.

If you want to show the GB voter ID messaging, set `SHOW_GB_ID_MESSAGING = True` in `settings/base.py`

## Post-Election Tasks

When we've got some results to show, you'll want to update `SHOW_RESULTS_CHART = True` in `settings/base.py`.
You'll also need to grab the Flourish chart info and replace it in `/templates/home.html`. It should live inside the `{% if show_results_chart %}` block.

## Deployments

Deployments are triggered by Circle CI. Take a look at `.circleci/config.yml` to see details of the deployment workflow.

To increase the number of EC2 instances for an environment (e.g. during busy times around elections) increase the `min-size`, `max-size` and `desired-capacity` variables found in the `code_deploy` jobs in the `config.yml` file. For further details, see notes about scaling [scaling](/docs/troubleshooting.md#scaling).
