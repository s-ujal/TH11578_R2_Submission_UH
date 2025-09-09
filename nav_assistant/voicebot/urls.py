# voicebot/urls.py
# from . import Exotelviews
from django.urls import path
from . import views

urlpatterns = [

    path('voice', views.twilio_voice_entry),            # initial call welcome + Gather
    path('voice/result', views.twilio_voice_result),    # Twilio posts back SpeechResult here
    path('sms', views.twilio_sms),                      # Incoming SMS handler
]
