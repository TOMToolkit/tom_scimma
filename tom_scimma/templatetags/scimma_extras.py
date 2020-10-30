from django import template

from tom_scimma.scimma import SCIMMAUpstreamSubmissionForm


register = template.Library()


@register.inclusion_tag('tom_scimma/partials/submit_upstream_scimma_form.html')
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

    form = SCIMMAUpstreamSubmissionForm(broker='SCIMMA', initial={
        'target': target,
        'observation_record': observation_record,
        'redirect_url': redirect_url,
        'topic': topic
    })

    return {
        'submit_upstream_form': form
    }
