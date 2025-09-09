import os
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.twiml.messaging_response import MessagingResponse
import json
from twilio.rest import Client
from helper import normalize_place_name, parse_origin_destination_gemini_ai, get_directions_ors, build_voice_text_ors, geocode_place, strip_html


# -------------- Twilio endpoints ----------------

@csrf_exempt
def twilio_voice_entry(request):
    """
    Receives initial inbound call. Use <Gather input='speech'> so Twilio transcribes into SpeechResult
    See Twilio docs: https://www.twilio.com/docs/voice/twiml/gather
    """
    resp = VoiceResponse()
    # Ask user in Hindi (use language hi-IN) - change text as needed
    gather = Gather(
        input="speech",
        action="/twilio/voice/result",
        method="POST",
        timeout=5,
        language="hi-IN"  # prefer Hindi; Twilio supports language codes
    )
    gather.say("Namaste. Kripya boliye — aap kahaan se kahaan jaana chahte hain.", language="hi-IN")
    resp.append(gather)
    resp.say("Agar aapne bolna band kar diya hai, toh main call ko band kar dunga.")
    return HttpResponse(str(resp), content_type="text/xml")

@csrf_exempt
def twilio_voice_result(request):
    """
    Twilio will POST SpeechResult here (if using Gather input=speech).
    We parse the transcription, extract origin/destination using an LLM, call Google Directions,
    and reply via TwiML <Say>.
    """
    speech_text = request.POST.get("SpeechResult","")
    from_number = request.POST.get("From")  # Caller’s number
    to_number = request.POST.get("To")      # Your Twilio number

    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    client = Client(account_sid, auth_token)
    resp = VoiceResponse()
    if not speech_text:
        resp.say("Mujhe aapki baat samajh nahi aayi. Kripya dobara call karen.", language="hi-IN")
        return HttpResponse(str(resp), content_type="text/xml")

    # parse origin & destination via LLM
    parsed = parse_origin_destination_gemini_ai(speech_text)
    origin = parsed.get("origin","")
    destination = parsed.get("destination","")


    if not origin or not destination:
        # clarify: ask once more
        gather = Gather(input="speech", action="/twilio/voice/result", method="POST", timeout=6, language="hi-IN")
        gather.say("Mujhe poori jankari nahi mili. Kripya dubara kahe.", language="hi-IN")
        resp.append(gather)
        return HttpResponse(str(resp), content_type="text/xml")
    

    nor_origin=normalize_place_name(origin)
    nor_destination=normalize_place_name(destination)
    
    #extracting geocode for searching
    origin = geocode_place(nor_origin)
    destination = geocode_place(nor_destination)

    if not origin and destination:
        gather = Gather(input="speech", action="/twilio/voice/result", method="POST", timeout=6, language="hi-IN")
        gather.say("Mujhe jagha ka pata nahi laga kripya acche se kahe.", language="hi-IN")
        resp.append(gather)
        return HttpResponse(str(resp), content_type="text/xml")


    # get route
    directions = get_directions_ors(origin, destination, profile="driving-car")
    if directions.get("error"):
        resp.say(f"Maaf kijiye. Route prapt karne mein error: {directions.get('error')}", language="hi-IN")
        return HttpResponse(str(resp), content_type="text/xml")

  
    voice_text = build_voice_text_ors(directions, max_steps=6)
    try:
        client.messages.create(
            body=voice_text,
            from_=to_number,
            to=from_number
        )
    except Exception as e:
        print("SMS sending error:", e)


    parts = voice_text.split("Kadam")
    for i, part in enumerate(parts):
        if not part.strip():
            continue
        # Say the line
        resp.say(("Kadam" + part).strip(), language="hi-IN")
        # Add 1 sec pause after each line except last
        if i < len(parts) - 1:
            resp.pause(length=1)

    return HttpResponse(str(resp), content_type="text/xml")


@csrf_exempt
def twilio_sms(request):
    """
    Handle inbound SMS. Extract origin/destination from the SMS body, call Google Directions,
    and reply via SMS with a compact step-by-step text (use Twilio MessagingResponse).
    """
    body = request.POST.get("Body", "")
    resp = MessagingResponse()

    if not body:
        resp.message("Kya aap dobara bhej sakte hain? Samajhne mein dikkat hui.")
        return HttpResponse(str(resp), content_type="text/xml")

    parsed = parse_origin_destination_gemini_ai(body)
    origin = parsed.get("origin","")
    destination = parsed.get("destination","")
    if not origin or not destination:
        resp.message("Kripya format : 'FROM <place> TO <place>' ya 'X se Y tak' bhejein.")
        return HttpResponse(str(resp), content_type="text/xml")

    directions = get_directions_ors(origin, destination, mode="walking")
    if directions.get("error"):
        resp.message(f"Route Error: {directions.get('error')}")
        return HttpResponse(str(resp), content_type="text/xml")

    # build SMS text (compact)
    sms_lines = [f"Rasta: {origin} → {destination}. Distance: {directions['total_distance']}, Time: {directions['total_duration']}."]
    for i, step in enumerate(directions.get("steps",[])[:6], start=1):
        sms_lines.append(f"{i}. {step['instruction']} ({step['distance']})")
    if len(directions.get("steps",[])) > 6:
        sms_lines.append("Aur details ke liye call karein ya visit karein map link.")  # optionally supply a google maps link
    resp.message("\n".join(sms_lines))
    return HttpResponse(str(resp), content_type="text/xml")
