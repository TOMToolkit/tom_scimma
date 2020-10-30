import requests

from confluent_kafka import KafkaException
from crispy_forms.layout import Column, Div, Fieldset, HTML, Layout, Row
from django import forms
from django.conf import settings
from hop import Stream
from hop.auth import Auth

from tom_alerts.alerts import GenericAlert, GenericBroker, GenericQueryForm, GenericUpstreamSubmissionForm
from tom_alerts.exceptions import AlertSubmissionException
from tom_targets.models import Target

SCIMMA_URL = 'http://skip.dev.hop.scimma.org'
SCIMMA_API_URL = f'{SCIMMA_URL}/api'


def get_topic_choices():
    response = requests.get(f'{SCIMMA_API_URL}/topics')
    response.raise_for_status()
    return [(result['id'], result['name']) for result in response.json()['results']]


class SCIMMABrokerForm(GenericQueryForm):
    keyword = forms.CharField(required=False, label='Keyword search')
    topic = forms.MultipleChoiceField(choices=get_topic_choices, required=False, label='Topic')
    cone_search = forms.CharField(required=False, label='Cone Search', help_text='RA, Dec, radius in degrees')
    polygon_search = forms.CharField(required=False, label='Polygon Search',
                                     help_text='Comma-separated pairs of space-delimited coordinates (degrees)')
    alert_timestamp_after = forms.DateTimeField(required=False, label='Datetime lower')
    alert_timestamp_before = forms.DateTimeField(required=False, label='Datetime upper')
    event_trigger_number = forms.CharField(required=False, label='LVC Trigger Number')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            self.common_layout,
            Fieldset(
                '',
                Div('topic'),
                Div('keyword')
            ),
            Fieldset(
                'Time Filters',
                Row(
                    Column('alert_timestamp_after'),
                    Column('alert_timestamp_before')
                )
            ),
            Fieldset(
                'Spatial Filters',
                Div('cone_search'),
                Div('polygon_search')
            ),
            HTML('<hr>'),
            Fieldset(
                'LVC Trigger Number',
                HTML('''
                    <p>
                    The LVC Trigger Number filter will only search the LVC topic. Please be aware that any topic
                    selections will be ignored.
                    </p>
                '''),
                'event_trigger_number'
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('event_trigger_number') and cleaned_data.get('topic'):
            raise forms.ValidationError('Topic filter cannot be used with LVC Trigger Number filter.')
        return cleaned_data


class SCIMMAUpstreamSubmissionForm(GenericUpstreamSubmissionForm):
    topic = forms.CharField(required=False, max_length=100, widget=forms.HiddenInput())


class SCIMMABroker(GenericBroker):
    """
    This is a prototype interface to the skip db built by SCIMMA
    """

    name = 'SCIMMA'
    form = SCIMMABrokerForm
    alert_submission_form = SCIMMAUpstreamSubmissionForm

    def fetch_alerts(self, parameters):
        parameters['page_size'] = 20
        response = requests.get(f'{SCIMMA_API_URL}/alerts/',
                                params={**parameters},
                                headers=settings.BROKERS['SCIMMA'])
        response.raise_for_status()
        result = response.json()
        return iter(result['results'])

    def fetch_alert(self, alert_id):
        url = f'{SCIMMA_API_URL}/alerts/{alert_id}'
        response = requests.get(url, headers=settings.BROKERS['SCIMMA'])
        response.raise_for_status()
        parsed = response.json()
        return parsed

    def to_generic_alert(self, alert):
        score = alert['message'].get('rank', 0) if alert['topic'] == 'lvc-counterpart' else ''
        return GenericAlert(
            url=f'{SCIMMA_API_URL}/alerts/{alert["id"]}',
            id=alert['id'],
            # This should be the object name if it is in the comments
            name=alert['alert_identifier'],
            ra=alert['right_ascension'],
            dec=alert['declination'],
            timestamp=alert['alert_timestamp'],
            # Well mag is not well defined for XRT sources...
            mag=0.0,
            score=score  # Not exactly what score means, but ish
        )

    def to_target(self, alert):
        # Galactic Coordinates come in the format:
        # "gal_coords": "76.19,  5.74 [deg] galactic lon,lat of the counterpart",
        gal_coords = [None, None]
        if alert['topic'] == 'lvc-counterpart':
            gal_coords = alert['message'].get('gal_coords', '').split('[')[0].split(',')
            gal_coords = [float(coord.strip()) for coord in gal_coords]
        return Target.objects.create(
            name=alert['alert_identifier'],
            type='SIDEREAL',
            ra=alert['right_ascension'],
            dec=alert['right_ascension'],
            galactic_lng=gal_coords[0],
            galactic_lat=gal_coords[1],
        )

    def submit_upstream_alert(self, target=None, observation_record=None, **kwargs):
        """
        Submits target and observation record as Hopskotch alerts.

        :param target: ``Target`` object to be converted to an alert and submitted upstream
        :type target: ``Target``

        :param observation_record: ``ObservationRecord`` object to be converted to an alert and submitted upstream
        :type observation_record: ``ObservationRecord``

        :param \\**kwargs:
            See below

        :Keyword Arguments:
            * *topic* (``str``): Hopskotch topic to submit the alert to.

        :returns: True or False depending on success of message submission
        :rtype: bool

        :raises:
            AlertSubmissionException: If topic is not provided to the function and a default is not provided in
                                      settings
        # TODO: write tests for this
        """
        creds = settings.BROKERS['SCIMMA']
        stream = Stream(auth=Auth(creds['hopskotch_username'], creds['hopskotch_password']))
        stream_url = creds['hopskotch_url']
        topic = kwargs.get('topic') if not kwargs.get('topic') else creds['default_hopskotch_topic']
        print(topic)

        if not topic:
            raise AlertSubmissionException(f'Topic must be provided to submit alert to {self.name}')

        try:
            with stream.open(f'kafka://{stream_url}:9092/{topic}', 'w') as s:
                if target:
                    message = {'type': 'target', 'target_name': target.name, 'ra': target.ra, 'dec': target.dec}
                    s.write(message)
                if observation_record:
                    message = {'type': 'observation', 'status': observation_record.status,
                               'parameters': observation_record.parameters_as_dict,
                               'target_name': observation_record.target.name,
                               'ra': observation_record.target.ra, 'dec': observation_record.target.dec,
                               'facility': observation_record.facility}
                    s.write(message)
        except KafkaException as e:
            raise AlertSubmissionException(f'Submission to Hopskotch failed: {e}')

        return True
