from django.test import tag, TestCase

from tom_scimma.scimma import SCIMMABroker
from tom_targets.models import Target


@tag('canary')
class TestSCIMMAModuleCanary(TestCase):
    """NOTE: To run these tests in your venv: python ./tom_scimma/tests/run_tests.py"""

    def setUp(self):
        self.broker = SCIMMABroker()
        self.expected_keys = ['id', 'identifier', 'timestamp', 'topic', 'right_ascension', 'declination',
                              'right_ascension_sexagesimal', 'declination_sexagesimal', 'parsed_message',
                              'raw_message', 'created', 'modified']

    def test_boilerplate(self):
        self.assertTrue(True)

    def test_fetch_alerts(self):
        """Test fetch_alerts"""
        response = self.broker.fetch_alerts({'topic': 1})
        alerts = []
        for alert in response:
            alerts.append(alert)
            for key in self.expected_keys:
                self.assertTrue(key in alert.keys())
        self.assertEqual(len(alerts), 20)

    def test_fetch_alert(self):
        """Test fetch_alert"""
        alert = self.broker.fetch_alert(1000)
        self.assertAlmostEqual(alert['right_ascension'], 55.25, 2)
        for key in self.expected_keys:
            self.assertTrue(key in alert.keys())

    def test_submit_upstream_alert(self):
        """Test submit_upstream_alert"""
        t = Target.objects.create(name='canary test target', ra=1, dec=2)
        response = self.broker.submit_upstream_alert(target=t, observation_record=None, topic='TOMToolkit.test')

        self.assertTrue(response)
