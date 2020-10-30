from datetime import datetime
from faker import Faker

fake = Faker()


def create_test_alert(topic=None):
    alert = {
        'id': fake.pyint(min_value=2458000, max_value=2463000),
        'alert_identifier': fake.pystr(),
        'alert_timestamp': datetime.strftime(fake.date_time_this_month(), '%Y-%m-%d %H:%M:%S'),
        'topic': fake.pyfloat(min_value=15, max_value=23),
        'right_ascension': fake.pyfloat(min_value=0, max_value=360),
        'declination': fake.pyfloat(min_value=0, max_value=360),
        'extracted_fields': {},  # fake.pydict(nb_elements=0),
        'message': {},  # fake.pydict(nb_elements=0)
    }

    if topic:
        alert['topic'] = topic

    return alert
