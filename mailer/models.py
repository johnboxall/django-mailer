from datetime import datetime
from django.conf import settings
from django.core.urlresolvers import get_mod_func
from django.db import models
from django.forms.models import fields_for_model


PRIORITIES = (
    ('1', 'high'),
    ('2', 'medium'),
    ('3', 'low'),
    ('4', 'deferred'),
)


class MessageManager(models.Manager):
    def high_priority(self):
        """the high priority messages in the queue"""
        return self.filter(priority='1')
    
    def medium_priority(self):
        """the medium priority messages in the queue"""
        return self.filter(priority='2')
    
    def low_priority(self):
        """the low priority messages in the queue"""
        return self.filter(priority='3')
    
    def non_deferred(self):
        """the messages in the queue not deferred"""        
        return self.filter(priority__lt='4')
    
    def deferred(self):
        """the deferred messages in the queue"""
        return self.filter(priority='4')
    
    def retry_deferred(self, new_priority=2):
        count = 0
        for message in self.deferred():
            if message.retry(new_priority):
                count += 1
        return count


class MessageBase(models.Model):
    objects = MessageManager()
    to_address = models.CharField(max_length=255)
    from_address = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    message_body = models.TextField()
    when_added = models.DateTimeField(default=datetime.now)
    priority = models.CharField(max_length=1, choices=PRIORITIES, default='2')

    class Meta:
        abstract = True

    def send(self):
        raise NotImplementedError
    
    def defer(self):
        self.priority = '4'
        self.save()
    
    def retry(self, new_priority=2):
        if self.priority == '4':
            self.priority = new_priority
            self.save()
            return True
        else:
            return False


class DontSendEntryManager(models.Manager):
    def has_address(self, address):
        """is the given address on the don't send list?"""
        return self.filter(to_address=address).count() > 0


class DontSendEntry(models.Model):
    objects = DontSendEntryManager()
    to_address = models.CharField(max_length=255)
    when_added = models.DateTimeField()
    
    class Meta:
        verbose_name = 'don\'t send entry'
        verbose_name_plural = 'don\'t send entries'
    


"""
Look at MAILER_MESSAGE_CLASS and import it as Message :\
Pretty sure there is a less magic way to do this.
"""
class MailerMessageModuleNotAvailable(Exception):
    pass

MESSAGE_CLASS = getattr(settings, "MAILER_MESSAGE_CLASS", "mailer.message.Message")
try:
    mod_name, model_name = get_mod_func(MESSAGE_CLASS)
    Message = getattr(__import__(mod_name, {}, {}, ['']), model_name)
except ImportError:
    raise MailerMessageModuleNotAvailable("Check your MAILER_MESSAGE_MODULE setting.")


# Now we'll dynamically create the messagelog class bassed on the Message cls.

RESULT_CODES = (
    ('1', 'success'),
    ('2', 'don\'t send'),
    ('3', 'failure'),
)


class MessageLogManager(models.Manager):    
    def log(self, message, result_code, log_message = ''):
        """
        create a log entry for an attempt to send the given message and
        record the given result and (optionally) a log message
        """
        params = {}
        fields = fields_for_model(message_model_cls).keys()
        for field in fields:
            params[field] = getattr(message, field)
        params.update({"result": result_code, "log_message": log_message})
        message_log = self.create(**params)


class MessageLog(Message):
    """Provides additional logging fields for the message_model_cls."""
    objects = MessageLogManager()
    when_attempted = models.DateTimeField(default=datetime.now)
    result = models.CharField(max_length=1, choices=RESULT_CODES)
    log_message = models.TextField()