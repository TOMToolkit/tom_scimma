import json
from requests import Response
from unittest.mock import mock_open, patch

from confluent_kafka import KafkaException
from django.core.exceptions import NON_FIELD_ERRORS
from django.test import override_settings, TestCase

from tom_alerts.exceptions import AlertSubmissionException
from tom_scimma.scimma import SCIMMAQueryForm, SCIMMABroker
from tom_scimma.tests.utils import create_test_alert
from tom_targets.models import Target


class TestSCIMMAQueryForm(TestCase):
    """
    NOTE: to run these tests in your venv: python ./tom_scimma/tests/run_tests.py
    """
    def setUp(self):
        mock_topic_choices = {
            'count': 1,
            'results': [
                {'id': 1, 'name': 'gcn'},
                {'id': 2, 'name': 'lvc.lvc-counterpart'}
            ]
        }
        self.mock_response = Response()
        self.mock_response._content = str.encode(json.dumps(mock_topic_choices))
        self.mock_response.status_code = 200

    def test_boilerplate(self):
        """Make sure the testing infrastructure is working."""
        self.assertTrue(True)

    @patch('tom_scimma.scimma.requests.get')
    def test_clean_topic_and_trigger_number(self, mock_requests_get):
        """Test that an error is thrown when both Topic and LVC Trigger Number are included in form submission."""
        mock_requests_get.return_value = self.mock_response

        form = SCIMMAQueryForm({'query_name': 'Test SCIMMA Query',
                                'broker': 'SCIMMA',
                                'topic': [1],
                                'event_trigger_number': 'S190426'})
        form.is_valid()
        self.assertTrue(form.has_error(NON_FIELD_ERRORS))
        self.assertIn('Topic filter cannot be used with LVC Trigger Number filter.', form.non_field_errors())


@override_settings(BROKERS={'SCIMMA': {'api_key': '', 'hopskotch_username': '', 'hopskotch_password': '',
                                       'hopskotch_url': 'test_url', 'default_hopskotch_topic': 'default'}
                            })
class TestSCIMMABrokerClass(TestCase):
    """NOTE: To run these tests in your venv: python ./tom_scimma/tests/run_tests.py"""

    def setUp(self):
        # Create 20 alerts
        self.alerts = [create_test_alert() for i in range(0, 20)]

    @patch('tom_scimma.scimma.requests.get')
    def test_fetch_alerts(self, mock_requests_get):
        """Test the SCIMMA-specific fetch_alerts logic."""
        mock_response = Response()
        mock_response._content = str.encode(json.dumps({'results': self.alerts}))
        mock_response.status_code = 200
        mock_requests_get.return_value = mock_response

        alerts_response = SCIMMABroker().fetch_alerts({})

        alerts = [alert for alert in alerts_response]
        self.assertEqual(len(alerts), 20)
        self.assertEqual(alerts[0], self.alerts[0])

    def test_to_generic_alert_any_topic(self):
        """Test the SCIMMA-specific to_generic_alert logic."""
        test_alert = self.alerts[0]
        test_alert['topic'] = 'gcn'
        test_alert['message'] = {'rank': '3'}
        generic_alert = SCIMMABroker().to_generic_alert(test_alert)

        # NOTE: The string is hardcoded as a sanity check to ensure that the string is reviewed if it changes
        self.assertEqual(generic_alert.url, f'http://skip.dev.hop.scimma.org/api/v2/alerts/{test_alert["id"]}')
        self.assertEqual(generic_alert.score, '')

    def test_to_generic_alert_lvc_topic(self):
        """Test the to_generic_alert logic for lvc-counterpart alerts. Should result in the inclusion of score."""
        test_alert = self.alerts[0]
        test_alert['topic'] = 'lvc.lvc-counterpart'
        test_alert['message'] = {'rank': '3'}
        generic_alert = SCIMMABroker().to_generic_alert(test_alert)

        # NOTE: The string is hardcoded as a sanity check to ensure that the string is reviewed if it changes
        self.assertEqual(generic_alert.url, f'http://skip.dev.hop.scimma.org/api/v2/alerts/{test_alert["id"]}')
        self.assertEqual(generic_alert.score, '3')

    def test_to_target_any_topic(self):
        """Test the SCIMMA-specific to_target logic."""
        test_alert = self.alerts[0]
        test_alert['topic'] = 'gcn'
        SCIMMABroker().to_target(test_alert)

        target = Target.objects.filter(name=test_alert['alert_identifier']).first()

        self.assertIsInstance(target, Target)
        self.assertEqual(target.galactic_lat, None)
        self.assertEqual(target.ra, self.alerts[0]['right_ascension'])
        self.assertEqual(target.dec, self.alerts[0]['declination'])

    def test_to_target_lvc_topic(self):
        """
        Test the to_target logic for lvc-counterpart alerts. Should result in the inclusion of galactic coordinates.
        """
        test_alert = self.alerts[0]
        test_alert['topic'] = 'lvc-counterpart'
        test_alert['message']['gal_coords'] = '336.99,-45.74 [deg] galactic lon,lat of the counterpart'
        SCIMMABroker().to_target(test_alert)

        target = Target.objects.filter(name=test_alert['alert_identifier']).first()

        self.assertIsInstance(target, Target)
        self.assertEqual(target.galactic_lat, -45.74)
        self.assertEqual(target.ra, self.alerts[0]['right_ascension'])
        self.assertEqual(target.dec, self.alerts[0]['declination'])

    def test_submit_upstream_alert_with_topic(self):
        """Test that successful submission uses the provided topic."""
        t = Target.objects.create(name='test name', ra=1, dec=2)
        with patch('tom_scimma.scimma.Stream.open', mock_open(read_data='data')) as mock_stream:
            SCIMMABroker().submit_upstream_alert(target=t, observation_record=None, topic='test')
            mock_stream.assert_called_once_with('kafka://test_url:9092/test', 'w')
            mock_stream().write.assert_called_with({'type': 'target', 'target_name': t.name, 'ra': t.ra, 'dec': t.dec})

    def test_submit_upstream_alert_no_topic(self):
        """Test that submission with no topic succeeds, using the default topic."""
        t = Target.objects.create(name='test name', ra=1, dec=2)
        with patch('tom_scimma.scimma.Stream.open', mock_open(read_data='data')) as mock_stream:
            SCIMMABroker().submit_upstream_alert(target=t, observation_record=None, topic=None)
            mock_stream.assert_called_once_with('kafka://test_url:9092/default', 'w')
            mock_stream().write.assert_called_with({'type': 'target', 'target_name': t.name, 'ra': t.ra, 'dec': t.dec})

    @override_settings(BROKERS={'SCIMMA': {'api_key': '', 'hopskotch_username': '', 'hopskotch_password': '',
                                           'hopskotch_url': 'test_url', 'default_hopskotch_topic': ''}
                                })
    @patch('tom_scimma.scimma.Stream')
    def test_submit_upstream_alert_no_default_topic(self, mock_stream):
        """Test that submission with no topic and no default topic fails."""
        with self.assertRaises(AlertSubmissionException):
            SCIMMABroker().submit_upstream_alert(target=None, observation_record=None)

    def test_submit_upstream_alert_failure(self):
        """Test that a KafkaException results in an AlertSubmissionException."""
        t = Target.objects.create(name='test name', ra=1, dec=2)
        with patch('tom_scimma.scimma.Stream.open', mock_open(read_data='data')) as mock_stream:
            mock_stream().write.side_effect = KafkaException()
            with self.assertRaises(AlertSubmissionException):
                SCIMMABroker().submit_upstream_alert(target=t, observation_record=None)
