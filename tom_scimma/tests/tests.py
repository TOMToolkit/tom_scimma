from datetime import datetime, timezone

from django.test import TestCase, override_settings
from unittest import mock

from tom_antares.antares import ANTARESBroker
from tom_antares.tests.factories import LocusFactory
from tom_targets.models import Target, TargetName


@override_settings(BROKER_CREDENTIALS={'antares': {'api_key': '', 'api_secret': ''}})
class TestANTARESBrokerClass(TestCase):
    """
    NOTE: to run these tests in your venv: python ./tom_antares/tests/run_tests.py
    """

    def setUp(self):
        self.test_target = Target.objects.create(name='ZTF20achooum')
        self.loci = [LocusFactory.create() for i in range(0, 5)]
        self.locus = self.loci[0]  # Get an individual locus for testing
        self.topic = 'in_m31_staging'

    def test_boilerplate(self):
        """make sure the testing infrastructure is working"""
        self.assertTrue(True)

    @mock.patch('tom_antares.antares.StreamingClient')
    def test_fetch_alerts(self, mock_streaming_client):
        """
        Test the ANTARES-specific fetch_alerts logic.
        """
        mock_client = mock_streaming_client.return_value
        # NOTE: if .side_effect is going to return a list, it needs a function that returns a list
        mock_client.iter.side_effect = lambda loci: iter([(self.topic, locus) for locus in self.loci])

        expected_alert = ANTARESBroker.alert_to_dict(self.locus)
        alerts = ANTARESBroker().fetch_alerts({'stream': [self.topic]})

        # TODO: compare iterator length with len(self.loci)
        self.assertEqual(next(alerts), (self.topic, expected_alert))

    def test_to_target_with_horizons_targetname(self):
        """
        Test that the expected names are created.

        The to_target logic in ANTARESBroker only has one branch, which occurs
        when the alert from ANTARES contains a horizons_targetname property

        This test should create two TargetName objects: one for the ANTARES name,
        and one for the horizons_targetname.
        """
        self.locus.properties['horizons_targetname'] = 'test targetname'
        alert = (self.topic, ANTARESBroker.alert_to_dict(self.locus))
        _ = ANTARESBroker().to_target(alert)

        self.assertEqual(TargetName.objects.all().count(), 2)

    def test_to_generic_alert(self):
        self.locus.properties['newest_alert_observation_time'] = 59134  # 10/12/2020
        generic_alert = ANTARESBroker().to_generic_alert((self.topic, ANTARESBroker.alert_to_dict(self.locus)))

        # NOTE: The string is hardcoded as a sanity check to ensure that the string is reviewed if it changes
        self.assertEqual(generic_alert.url, f'https://antares.noirlab.edu/loci/{self.locus.locus_id}')
        self.assertEqual(generic_alert.timestamp, datetime(2020, 10, 12, tzinfo=timezone.utc))
