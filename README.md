[![CircleCI](https://circleci.com/gh/DemocracyClub/WhoCanIVoteFor.svg?style=svg)](https://circleci.com/gh/DemocracyClub/WhoCanIVoteFor) [![Coverage Status](https://coveralls.io/repos/github/DemocracyClub/WhoCanIVoteFor/badge.svg?branch=master)](https://coveralls.io/github/DemocracyClub/WhoCanIVoteFor?branch=master) ![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)

# WhoCanIVoteFor

This project is brand new!

It is designed for people who don't know loads about the ins and outs of elections to use to find out everything about upcoming elections, including candidates, polling stations, electon dates, etc.

It will have the following features:

* "Given a postcode, when is my next election?"
* "Who are the candidates per election?"
* "Where is my polling staion?"
* Enter email address and postcode to get alerted about future elections in yous area
* Option to show interest in standing for future elections
* Option to donate to DC in order to keep the site running
* Option to record results of elections (power users only, maybe in a different interface to the normal one)
* …and other things like that.

It might be good to look at [this issue](https://github.com/mysociety/yournextrepresentative/issues/584) for a little more info.

The reason for building this site:

1. We have some other tools that are designed for gathering data, for example [Democracy Club Candidates](https://candidates.democracyclub.org.uk/) and [UK Polling Statons](https://wheredoivote.co.uk/).  There is value in keeping these sites on their own, as the candidates one in particular has a very different audiance to this site.
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

## Getting started

See [INSTALL.md](INSTALL.md) for setup instructions.
