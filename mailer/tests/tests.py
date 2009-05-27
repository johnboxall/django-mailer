import os
 
from django.conf import settings
from django.core import mail
from django.test import TestCase

from mailer import send_html_mail
from mailer.models import Message

class MailerTest(TestCase):
#     urls = "ab.tests.test_urls"
#     fixtures = ["test_data"]
#     template_dirs = [
#         os.path.join(os.path.dirname(__file__), 'templates'),
#     ]
    
    def setUp(self):
        self.old_debug = settings.DEBUG
        settings.DEBUG = True
        
    def tearDown(self):
        settings.DEBUG = self.old_debug
        
    def test_send_html_mail(self):
        "mailer.send_html_mail: Test the HTML mail sender."
        
        # Test sending in DEBUG mode - should go into OUTBOX.
        send_html_mail("subject", "plain", "html", "from@example.org", ["to@example.org"])
        self.assertEquals(len(mail.outbox), 1)

        # Test sending without DEBUG - should create a mail instance.
        settings.DEBUG = False
        send_html_mail("subject", "plain", "html", "from@example.org", ["to@example.org"])
        Message.objects.get(from_address="from@example.org")
