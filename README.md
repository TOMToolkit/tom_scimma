[![pypi](https://img.shields.io/pypi/v/tom-scimma.svg)](https://pypi.python.org/pypi/tom-scimma)
[![run-tests](https://github.com/TOMToolkit/tom_scimma/actions/workflows/run-tests.yml/badge.svg)](https://github.com/TOMToolkit/tom_scimma/actions/workflows/run-tests.yml)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/2fb72a4120d8493bac9c25347ccf721d)](https://www.codacy.com/gh/TOMToolkit/tom_scimma/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=TOMToolkit/tom_scimma&amp;utm_campaign=Badge_Grade)
[![Coverage Status](https://coveralls.io/repos/github/TOMToolkit/tom_scimma/badge.svg?branch=main)](https://coveralls.io/github/TOMToolkit/tom_scimma?branch=main)

# tom_scimma
This module adds [Hopskotch](https://scimma.org/projects.html) and [Skip](http://skip.dev.hop.scimma.org/api/)
support to the TOM Toolkit. Using this module, TOMs can query alerts submitted to the Hopskotch stream, and publish alerts to Hopskotch.

## Installation

Install the module into your TOM environment:

    pip install tom-scimma

Add `tom_scimma.scimma.SCIMMABroker` to the `TOM_ALERT_CLASSES` in your TOM's `settings.py`:

    TOM_ALERT_CLASSES = [
        'tom_alerts.brokers.mars.MARSBroker',
        ...
        'tom_scimma.scimma.SCIMMABroker'
    ]

Though Skip alerts are public (for now), you'll need Hopskotch credentials to submit alerts. You can register for an
account [here](https://admin.dev.hop.scimma.org/hopauth/login?next=/hopauth/). Add the appropriate Skip and Hopskotch
credentials to your project's `settings.py`:

```python
    BROKERS = {
        'SCIMMA': {
            'url': 'http://skip.dev.hop.scimma.org',
            'api_key': os.getenv('SKIP_API_KEY', ''),
            'hopskotch_url': 'dev.hop.scimma.org',
            'hopskotch_username': os.getenv('HOPSKOTCH_USERNAME', ''),
            'hopskotch_password': os.getenv('HOPSKOTCH_PASSWORD', ''),
            'default_hopskotch_topic': ''
        }
    }
```

## Configurable settings

``url``: The URL for Skip requests, i.e. for retrieving alerts.

``api_key``: The API key used to authenticate/authorize with Skip. Currently unused.

``hopskotch_url``: The URL for Hopskotch broker submissions, i.e. submitting alerts.

``hopskotch_username``: The username used to authenticate with Hopskotch.

``hopskotch_password``: The password used to authenticate with Hopskotch.

``default_hopskotch_topic``: The Hopskotch topic to submit alerts to when none is provided.

## Available templatetags

Though the TOM Toolkit provides a broker submission templatetag, `tom_scimma` provides an additional templatetag that
includes a keyword argument for topic. To use it, 

Add `tom_scimma` to your `settings.INSTALLED_APPS`:

```python
    INSTALLED_APPS = [
        'django.contrib.admin',
        'django.contrib.auth',
        ...
        'tom_scimma'
    ]
```

Then, add `scimma_extras` to the `{% load ... %}` statement of your desired template:

```
    {% load bootstrap4 targets_extras ... scimma_extras %}
```

Finally, add your desired templatetag where you would like it in your template:

```
    {% submit_upstream_scimma_form target observation_record redirect_url topic_name %}
```

The signature and docstring of the `submit_upstream_to_scimma` button are as follows:

    ```
    def submit_upstream_scimma_form(target=None, observation_record=None, redirect_url=None, topic=None):
        """
        Renders a button to submit an alert upstream to a broker. At least one of target/obs record should be given.

        :param broker: The name of the broker to which the button will lead, as in the name field of the broker module.
        :type broker: str

        :param target: The target to be submitted as an alert, if any.
        :type target: ``Target``

        :param observation_record: The observation record to be submitted as an alert, if any.
        :type observation_record: ``ObservationRecord``

        :param topic: The topic to submit the alerts to.
        :type topic: str

        :param redirect_url:
        :type redirect_url: str
        """
    ```

## Running the tests

In order to run the tests, run the following in your virtualenv:

`python tom_scimma/tests/run_tests.py`
